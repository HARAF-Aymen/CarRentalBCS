from app.extensions import db
from datetime import datetime

class ContratLocation(db.Model):
    __tablename__ = "contrats_location"

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey("demandes_location.id"), nullable=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey("utilisateurs.id"), nullable=False)
    vehicule_id = db.Column(db.Integer, db.ForeignKey("vehicule.id"), nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    date_signature = db.Column(db.DateTime, default=datetime.utcnow)
    statut = db.Column(db.String(20), default="EN_COURS")  # EN_COURS, TERMINE

    # Relations
    location = db.relationship("DemandeLocation", backref="contrat")
    utilisateur = db.relationship("Utilisateur")
    vehicule = db.relationship("Vehicule")
