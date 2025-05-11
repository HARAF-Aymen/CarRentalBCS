from app.extensions import db
from datetime import datetime

class DemandeLocation(db.Model):
    __tablename__ = 'demandes_location'

    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey('demandes_mission.id'), nullable=False)
    vehicule_id = db.Column(db.Integer, db.ForeignKey('vehicule.id'), nullable=False)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    statut = db.Column(db.String(20), default="EN_ATTENTE")  # EN_ATTENTE, ACCEPTEE, REFUSEE
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    mission = db.relationship("DemandeMission", backref="locations")
    vehicule = db.relationship("Vehicule", backref="locations")
    fournisseur = db.relationship("Utilisateur", backref="locations_envoyees")
