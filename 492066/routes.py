from flask import render_template, request, redirect, url_for, session, flash
from functools import wraps
from extensions import db
from models import User, Transactie, Categorie, Budget, Spaarpotje
from forms import (
    TransactieForm, LoginForm, RegisterForm, CategorieForm,
    BudgetForm, SpaarpotjeForm, SpaarpotjeGeldForm
)
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, SelectField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, NumberRange, EqualTo

def init_routes(app):
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Je moet eerst inloggen om deze pagina te bekijken.', 'warning')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        
        form = RegisterForm()
        if request.method == 'POST':
            try:
                if form.validate_on_submit():
                    # controleer of gebruikersnaam al bestaat
                    if User.query.filter_by(username=form.username.data).first():
                        flash('Gebruikersnaam bestaat al', 'danger')
                        return redirect(url_for('register'))
                    
                    user = User(username=form.username.data)
                    user.set_password(form.password.data)
                    db.session.add(user)
                    db.session.commit()
                    
                    flash('Registratie succesvol! Je kunt nu inloggen.', 'success')
                    return redirect(url_for('login'))
                else:
                    # form validatie fouten
                    for field, errors in form.errors.items():
                        for error in errors:
                            flash(f'{error}', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Er is een fout opgetreden: {str(e)}', 'danger')
        
        return render_template('register.html', form=form)

    @app.route('/')
    def root():
        session.clear()
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            
            if user and user.check_password(form.password.data):
                session['user_id'] = user.id
                flash('Je bent succesvol ingelogd!', 'success')
                return redirect(url_for('dashboard'))
            
            flash('Ongeldige gebruikersnaam of wachtwoord', 'danger')
        
        return render_template('login.html', form=form)

    @app.route('/logout')
    def logout():
        session.clear()
        flash('Je bent uitgelogd', 'danger')
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user_id = session['user_id']
        user = User.query.get(user_id)
        transacties = Transactie.query.filter_by(user_id=user_id).all()
        categorieen = Categorie.query.filter_by(user_id=user_id).all()
        budgetten = Budget.query.filter_by(user_id=user_id).all()
        spaarpotjes = Spaarpotje.query.filter_by(user_id=user_id).all()
        
        spaarpotjes_voortgang = []
        for spaarpotje in spaarpotjes:
            voortgang = (spaarpotje.huidig_bedrag / spaarpotje.doelbedrag) * 100 if spaarpotje.doelbedrag > 0 else 0
            spaarpotjes_voortgang.append({
                'naam': spaarpotje.naam,
                'huidig_bedrag': spaarpotje.huidig_bedrag,
                'doelbedrag': spaarpotje.doelbedrag,
                'voortgang': voortgang
            })
        
        inkomsten = Transactie.query.filter_by(user_id=user_id, type='inkomst').all()
        uitgaven = Transactie.query.filter_by(user_id=user_id, type='uitgave').all()
        
        totaal_inkomsten = sum(t.bedrag for t in inkomsten)
        totaal_uitgaven = sum(t.bedrag for t in uitgaven)
        saldo = totaal_inkomsten - totaal_uitgaven
        
        # Bereken voortgang van budgetten
        budgetten_voortgang = []
        for budget in budgetten:
            uitgaven_categorie = sum(t.bedrag for t in budget.categorie.transacties if t.type == 'uitgave')
            voortgang = (uitgaven_categorie / budget.bedrag) * 100 if budget.bedrag > 0 else 0
            budgetten_voortgang.append({
                'categorie': budget.categorie.naam,
                'bedrag': budget.bedrag,
                'uitgaven': uitgaven_categorie,
                'voortgang': voortgang
            })
        
        form = TransactieForm()
        form.categorie_id.choices = [(0, 'Geen categorie')] + [(c.id, c.naam) for c in categorieen]
        form.spaarpotje_id.choices = [(0, 'Geen spaarpotje')] + [(s.id, s.naam) for s in spaarpotjes]
        
        return render_template('index.html', 
                             current_user=user,
                             transacties=transacties,
                             categorieen=categorieen,
                             budgetten=budgetten,
                             spaarpotjes=spaarpotjes,
                             spaarpotjes_voortgang=spaarpotjes_voortgang,
                             budgetten_voortgang=budgetten_voortgang,
                             totaal_inkomsten=totaal_inkomsten,
                             totaal_uitgaven=totaal_uitgaven,
                             saldo=saldo,
                             form=form)

    @app.route('/toevoegen', methods=['POST'])
    @login_required
    def toevoegen():
        form = TransactieForm()
        
        categorieen = Categorie.query.filter_by(user_id=session['user_id']).all()
        spaarpotjes = Spaarpotje.query.filter_by(user_id=session['user_id']).all()
        
        form.categorie_id.choices = [(c.id, c.naam) for c in categorieen]
        form.spaarpotje_id.choices = [(0, 'Geen spaarpotje')] + [(s.id, s.naam) for s in spaarpotjes]
        
        if request.method == 'POST':
            try:
                type = request.form.get('type')
                omschrijving = request.form.get('omschrijving')
                bedrag = float(request.form.get('bedrag', 0))
                categorie_id = int(request.form.get('categorie_id', 0))
                spaarpotje_id = int(request.form.get('spaarpotje_id', 0))
                
                if type == 'uitgave' and categorie_id:
                    categorie = Categorie.query.get(categorie_id)
                    if categorie and categorie.user_id == session['user_id']:
                        uitgaven = Transactie.query.filter(
                            Transactie.user_id == session['user_id'],
                            Transactie.categorie_id == categorie_id,
                            Transactie.type == 'uitgave'
                        ).all()
                        
                        totaal_uitgaven = sum(t.bedrag for t in uitgaven)
                        
                        budget = Budget.query.filter_by(
                            categorie_id=categorie_id,
                            user_id=session['user_id']
                        ).first()
                        
                        if budget and (totaal_uitgaven + bedrag) > budget.bedrag:
                            flash(f'Let op: Deze uitgave zou je budget van €{budget.bedrag:.2f} voor de categorie {categorie.naam} overschrijden!', 'danger')
                            return redirect(url_for('dashboard'))
                
                transactie = Transactie(
                    type=type,
                    omschrijving=omschrijving,
                    bedrag=bedrag,
                    user_id=session['user_id'],
                    categorie_id=categorie_id if categorie_id > 0 else None,
                    spaarpotje_id=spaarpotje_id if spaarpotje_id > 0 else None
                )
                
                db.session.add(transactie)
                
                if spaarpotje_id > 0:
                    spaarpotje = Spaarpotje.query.get(spaarpotje_id)
                    if spaarpotje and spaarpotje.user_id == session['user_id']:
                        if type == 'inkomst':
                            spaarpotje.huidig_bedrag += bedrag
                            flash(f'€{bedrag:.2f} succesvol toegevoegd aan {spaarpotje.naam}!', 'success')
                        else:
                            if spaarpotje.huidig_bedrag >= bedrag:
                                spaarpotje.huidig_bedrag -= bedrag
                                flash(f'€{bedrag:.2f} succesvol afgehaald van {spaarpotje.naam}!', 'success')
                            else:
                                flash('Er is niet genoeg geld in het spaarpotje!', 'danger')
                                db.session.rollback()
                                return redirect(url_for('dashboard'))
                
                db.session.commit()
                flash('Transactie succesvol toegevoegd!', 'success')
                
            except Exception as e:
                db.session.rollback()
                flash(f'Er is een fout opgetreden: {str(e)}', 'danger')
        
        return redirect(url_for('dashboard'))

    @app.route('/verwijderen/<int:id>')
    @login_required
    def verwijderen(id):
        transactie = Transactie.query.get_or_404(id)
        if transactie.user_id == session['user_id']:
            db.session.delete(transactie)
            db.session.commit()
            flash('Transactie succesvol verwijderd!', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/reset')
    @login_required
    def reset_database():
        user_id = session['user_id']
        Transactie.query.filter_by(user_id=user_id).delete()
        Categorie.query.filter_by(user_id=user_id).delete()
        Budget.query.filter_by(user_id=user_id).delete()
        Spaarpotje.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        flash('Alle gegevens zijn gereset!', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/categorieen')
    @login_required
    def categorieen():
        user_id = session['user_id']
        user = User.query.get(user_id)
        form = CategorieForm()
        categorieen = Categorie.query.filter_by(user_id=user_id).all()
        return render_template('categorieen.html', 
                             current_user=user,
                             form=form, 
                             categorieen=categorieen)

    @app.route('/categorie/toevoegen', methods=['POST'])
    @login_required
    def categorie_toevoegen():
        form = CategorieForm()
        if form.validate_on_submit():
            categorie = Categorie(
                naam=form.naam.data,
                user_id=session['user_id']
            )
            db.session.add(categorie)
            db.session.commit()
            flash('Categorie succesvol toegevoegd!', 'success')
        return redirect(url_for('categorieen'))

    @app.route('/categorie/verwijderen/<int:id>')
    @login_required
    def categorie_verwijderen(id):
        categorie = Categorie.query.get_or_404(id)
        if categorie.user_id == session['user_id']:
            db.session.delete(categorie)
            db.session.commit()
            flash('Categorie succesvol verwijderd!', 'success')
        return redirect(url_for('categorieen'))

    @app.route('/budgetten')
    @login_required
    def budgetten():
        user_id = session['user_id']
        user = User.query.get(user_id)
        form = BudgetForm()
        categorieen = Categorie.query.filter_by(user_id=user_id).all()
        form.categorie_id.choices = [(c.id, c.naam) for c in categorieen]
        budgetten = Budget.query.filter_by(user_id=user_id).all()
        
        budget_uitgaven = {}
        for budget in budgetten:
            uitgaven = sum(t.bedrag for t in budget.categorie.transacties 
                          if t.type == 'uitgave')
            budget_uitgaven[budget.id] = uitgaven
        
        return render_template('budgetten.html', 
                             current_user=user,
                             form=form, 
                             budgetten=budgetten,
                             budget_uitgaven=budget_uitgaven)

    @app.route('/budget/toevoegen', methods=['POST'])
    @login_required
    def budget_toevoegen():
        user_id = session['user_id']
        form = BudgetForm()
        categorieen = Categorie.query.filter_by(user_id=user_id).all()
        form.categorie_id.choices = [(c.id, c.naam) for c in categorieen]
        
        if request.method == 'POST':
            try:
                categorie_id = int(request.form.get('categorie_id'))
                bedrag = float(request.form.get('bedrag'))
                
                categorie = Categorie.query.get(categorie_id)
                if categorie and categorie.user_id == user_id:
                    budget = Budget(
                        bedrag=bedrag,
                        categorie_id=categorie_id,
                        user_id=user_id
                    )
                    db.session.add(budget)
                    db.session.commit()
                    flash('Budget succesvol toegevoegd!', 'success')
                else:
                    flash('Ongeldige categorie geselecteerd', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Er is een fout opgetreden: {str(e)}', 'danger')
        
        return redirect(url_for('budgetten'))

    @app.route('/budget/verwijderen/<int:id>')
    @login_required
    def budget_verwijderen(id):
        budget = Budget.query.get_or_404(id)
        if budget.user_id == session['user_id']:
            db.session.delete(budget)
            db.session.commit()
            flash('Budget succesvol verwijderd!', 'success')
        return redirect(url_for('budgetten'))

    @app.route('/transacties')
    @login_required
    def transacties():
        user_id = session['user_id']
        user = User.query.get(user_id)
        transacties = Transactie.query.filter_by(user_id=user_id).all()
        categorieen = Categorie.query.filter_by(user_id=user_id).all()
        
        # Maak een dictionary van categorieën voor snelle lookup
        categorie_dict = {c.id: c.naam for c in categorieen}
        
        return render_template('transacties.html', 
                             current_user=user,
                             transacties=transacties,
                             categorie_dict=categorie_dict)

    @app.route('/spaarpotjes')
    @login_required
    def spaarpotjes():
        user_id = session['user_id']
        user = User.query.get(user_id)
        form = SpaarpotjeForm()
        geld_form = SpaarpotjeGeldForm()
        spaarpotjes = Spaarpotje.query.filter_by(user_id=user_id).all()
        return render_template('spaarpotjes.html', 
                             current_user=user,
                             form=form,
                             geld_form=geld_form,
                             spaarpotjes=spaarpotjes)

    @app.route('/spaarpotje/toevoegen', methods=['POST'])
    @login_required
    def spaarpotje_toevoegen():
        user_id = session['user_id']
        if request.method == 'POST':
            try:
                naam = request.form.get('naam')
                doelbedrag = float(request.form.get('doelbedrag', 0))
                
                spaarpotje = Spaarpotje(
                    naam=naam,
                    doelbedrag=doelbedrag,
                    user_id=user_id
                )
                db.session.add(spaarpotje)
                db.session.commit()
                flash('Spaarpotje succesvol toegevoegd!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Er is een fout opgetreden: {str(e)}', 'danger')
        return redirect(url_for('spaarpotjes'))

    @app.route('/spaarpotje/verwijderen/<int:id>')
    @login_required
    def spaarpotje_verwijderen(id):
        user_id = session['user_id']
        spaarpotje = Spaarpotje.query.get_or_404(id)
        if spaarpotje.user_id == user_id:
            db.session.delete(spaarpotje)
            db.session.commit()
            flash('Spaarpotje succesvol verwijderd!', 'success')
        return redirect(url_for('spaarpotjes'))

    @app.route('/spaarpotje/verwijderen/<int:id>/bevestig')
    @login_required
    def spaarpotje_verwijderen_bevestig(id):
        user_id = session['user_id']
        user = User.query.get(user_id)
        spaarpotje = Spaarpotje.query.get_or_404(id)
        if spaarpotje.user_id == user_id:
            return render_template('spaarpotje_verwijderen.html', 
                                 current_user=user,
                                 spaarpotje=spaarpotje)
        return redirect(url_for('spaarpotjes'))

    @app.route('/spaarpotje/geld/<int:id>', methods=['POST'])
    @login_required
    def spaarpotje_geld(id):
        user_id = session['user_id']
        if request.method == 'POST':
            try:
                spaarpotje_id = int(request.form.get('spaarpotje_id', 0))
                spaarpotje = Spaarpotje.query.get_or_404(spaarpotje_id)
                if spaarpotje.user_id == user_id:
                    bedrag = float(request.form.get('bedrag', 0))
                    type = request.form.get('type')
                    
                    if type == 'toevoegen':
                        spaarpotje.huidig_bedrag += bedrag
                        flash(f'€{bedrag:.2f} succesvol toegevoegd aan {spaarpotje.naam}!', 'success')
                    elif type == 'afhalen':
                        if spaarpotje.huidig_bedrag >= bedrag:
                            spaarpotje.huidig_bedrag -= bedrag
                            flash(f'€{bedrag:.2f} succesvol afgehaald van {spaarpotje.naam}!', 'success')
                        else:
                            flash('Er is niet genoeg geld in het spaarpotje!', 'danger')
                            return redirect(url_for('spaarpotjes'))
                    else:
                        flash('Ongeldige actie geselecteerd', 'danger')
                        return redirect(url_for('spaarpotjes'))
                    
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f'Er is een fout opgetreden: {str(e)}', 'danger')
        return redirect(url_for('spaarpotjes'))

    @app.route('/transactie/bewerken/<int:id>', methods=['GET', 'POST'])
    @login_required
    def transactie_bewerken(id):
        user_id = session['user_id']
        user = User.query.get(user_id)
        transactie = Transactie.query.get_or_404(id)
        if transactie.user_id != user_id:
            return redirect(url_for('dashboard'))
        
        categorieen = Categorie.query.filter_by(user_id=user_id).all()
        form = TransactieForm()
        form.categorie_id.choices = [(0, '-- Geen categorie --')] + [(c.id, c.naam) for c in categorieen]
        
        if request.method == 'POST':
            try:
                type = request.form.get('type')
                omschrijving = request.form.get('omschrijving')
                bedrag = float(request.form.get('bedrag', 0))
                categorie_id = int(request.form.get('categorie_id', 0))
                
                transactie.type = type
                transactie.omschrijving = omschrijving
                transactie.bedrag = bedrag
                transactie.categorie_id = categorie_id if categorie_id > 0 else None
                
                db.session.commit()
                flash('Transactie is succesvol bijgewerkt!', 'success')
                return redirect(url_for('transacties'))
            except Exception as e:
                print("Error saving transaction:", str(e))
                db.session.rollback()
                flash(f'Er is een fout opgetreden: {str(e)}', 'danger')
        
        if request.method == 'GET':
            form.type.data = transactie.type
            form.omschrijving.data = transactie.omschrijving
            form.bedrag.data = transactie.bedrag
            form.categorie_id.data = transactie.categorie_id if transactie.categorie_id else 0
        
        return render_template('transactie_bewerken.html', 
                             current_user=user,
                             form=form, 
                             transactie=transactie)