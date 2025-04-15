from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    transacties = db.relationship('Transactie', backref='user', lazy=True)
    categorieen = db.relationship('Categorie', backref='user', lazy=True)
    budgetten = db.relationship('Budget', backref='user', lazy=True)
    spaarpotjes = db.relationship('Spaarpotje', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transactie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # inkomst of uitgave
    omschrijving = db.Column(db.String(200), nullable=False)
    bedrag = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie.id'), nullable=True)
    spaarpotje_id = db.Column(db.Integer, db.ForeignKey('spaarpotje.id'), nullable=True)
    spaarpotje = db.relationship('Spaarpotje', backref='transacties')

    def __repr__(self):
        return f'<Transactie {self.type} {self.bedrag}>'

class Categorie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    naam = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transacties = db.relationship('Transactie', backref='categorie', lazy=True)  # Relatie toegevoegd

    def __repr__(self):
        return f'<Categorie {self.naam}>'

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bedrag = db.Column(db.Float, nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie.id'), nullable=False)
    categorie = db.relationship('Categorie', backref='budgetten')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Budget {self.bedrag} voor {self.categorie.naam}>'

class Spaarpotje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    naam = db.Column(db.String(100), nullable=False)
    doelbedrag = db.Column(db.Float, nullable=False)
    huidig_bedrag = db.Column(db.Float, default=0.0)
    deadline = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Spaarpotje {self.naam}>'

    @property
    def voortgang(self):
        return (self.huidig_bedrag / self.doelbedrag) * 100 if self.doelbedrag > 0 else 0