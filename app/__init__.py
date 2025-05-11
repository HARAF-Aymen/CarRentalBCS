from flask import Flask
from app.services.config import Config

from app.extensions import db, jwt, migrate, mail

# Blueprints
from app.blueprints.auth import auth_bp
from app.blueprints.vehicules import vehicules_bp
from app.blueprints.missions import missions_bp
from app.blueprints.locations import locations_bp
from app.blueprints.contrats import contrats_bp
from app.blueprints.dashboard import dashboard_bp

# Models (pour les migrations automatiques)
from app.models import demande_location
from app.models.demande_mission import DemandeMission
from app.models.contrat_location import ContratLocation

# Commandes CLI & Scheduler
from app.commands.unassign import unassign_vehicules
from app.services.scheduler import start_scheduler

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialisation des extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # Enregistrement des blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(vehicules_bp, url_prefix="/api/vehicules")
    app.register_blueprint(missions_bp, url_prefix="/api/missions")
    app.register_blueprint(locations_bp, url_prefix="/api/locations")
    app.register_blueprint(contrats_bp, url_prefix="/api/contrats")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")

    # Commande CLI personnalisée
    app.cli.add_command(unassign_vehicules)

    # Lancement du scheduler dans le contexte Flask
    with app.app_context():
        start_scheduler()

    return app
