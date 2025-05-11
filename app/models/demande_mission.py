# app/models/demande_mission.py
from app.extensions import db
from datetime import datetime

class DemandeMission(db.Model):
    __tablename__ = 'demandes_mission'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicule.id'), nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    statut = db.Column(db.String(20), default="EN_ATTENTE")  # EN_ATTENTE, APPROUVEE, REFUSEE
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    utilisateur = db.relationship("Utilisateur", backref="missions")
    vehicule = db.relationship("Vehicule", backref="missions")
