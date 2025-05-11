from app.extensions import db
from enum import Enum
from sqlalchemy.sql import func

class CarburantEnum(Enum):
    ESSENCE = "ESSENCE"
    DIESEL = "DIESEL"
    ELECTRIQUE = "ELECTRIQUE"

class Vehicule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    marque = db.Column(db.String(100), nullable=False)
    modele = db.Column(db.String(100), nullable=False)
    carburant = db.Column(db.String(50), nullable=False)
    kilometrage = db.Column(db.Integer, nullable=False)
    prix_jour = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(255))

    is_assigned = db.Column(db.Boolean, default=False, nullable=False)  # 🆕



    fournisseur_id = db.Column(db.Integer, db.ForeignKey('utilisateurs.id'), nullable=False)
    fournisseur = db.relationship("Utilisateur", backref="vehicules")
