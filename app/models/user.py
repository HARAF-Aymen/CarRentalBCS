from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class RoleEnum(Enum):
    FLEET_ADMIN = "FLEET_ADMIN"
    FOURNISSEUR = "FOURNISSEUR"
    USER = "USER"

class Utilisateur(db.Model):
    __tablename__ = 'utilisateurs'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(RoleEnum), default=RoleEnum.USER, nullable=False)

    def set_password(self, raw_password: str):
        self.mot_de_passe = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.mot_de_passe, raw_password)
