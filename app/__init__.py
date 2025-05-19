import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.services.config import Config

from app.extensions import db, jwt, migrate, mail
from flask import send_from_directory

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

    # Serve uploaded vehicle images
    @app.route('/uploads/vehicules/<path:filename>')
    def uploaded_vehicule_file(filename):
        return send_from_directory(os.path.join(os.getcwd(), 'uploads', 'vehicules'), filename)

    # Initialisation des extensions
    db.init_app(app)
    jwt.init_app(app)

    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({"error": "Missing Authorization Header"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({"error": "Invalid token"}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token expired"}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token revoked"}), 401

    migrate.init_app(app, db)
    mail.init_app(app)
    # ✅ CORS FIX
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}, supports_credentials=True)


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
