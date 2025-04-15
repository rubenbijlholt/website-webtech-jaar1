import sys
sys.dont_write_bytecode = True  # voorkomt het maken van cache bestanden

from flask import Flask
from extensions import db

def create_app():
    # initialiseer flask app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'jouw-geheime-sleutel-hier'  # nodig voor het beheren van gebruikerssessies

    # initialiseer database
    db.init_app(app)

    # Import en registreer routes
    from routes import init_routes
    init_routes(app)

    return app

def init_db(app):
    with app.app_context():
        # maakt alleen nieuwe tabellen aan als ze nog niet bestaan
        db.create_all()
        print("database is geïnitialiseerd!")

if __name__ == '__main__':
    app = create_app()
    init_db(app)  # start de database
    app.run(debug=True) 