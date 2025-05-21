import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.vehicule import Vehicule
from app.models.user import Utilisateur, RoleEnum
from app.extensions import db

vehicules_bp = Blueprint("vehicules", __name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads', 'vehicules')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 🚘 Ajouter un véhicule (Fournisseur uniquement)
@vehicules_bp.route("/", methods=["POST"])
@jwt_required()
def create_vehicule():
    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user.role != RoleEnum.FOURNISSEUR:
        return jsonify({"error": "Seuls les fournisseurs peuvent ajouter des véhicules"}), 403

    marque = request.form.get("marque")
    modele = request.form.get("modele")
    carburant = request.form.get("carburant")
    kilometrage = request.form.get("kilometrage")
    prix_jour = request.form.get("prix_jour")
    image_file = request.files.get("image")

    if not all([marque, modele, carburant, kilometrage, prix_jour, image_file]):
        return jsonify({"error": "Tous les champs sont requis"}), 400

    filename = secure_filename(image_file.filename)
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    image_file.save(image_path)

    vehicule = Vehicule(
        marque=marque,
        modele=modele,
        carburant=carburant,
        kilometrage=int(kilometrage),
        prix_jour=float(prix_jour),
        image_path=image_path,
        fournisseur_id=user.id,
        is_assigned=False
    )

    db.session.add(vehicule)
    db.session.commit()

    return jsonify({"message": "Véhicule ajouté avec succès"}), 201

# 🚗 Modifier un véhicule
@vehicules_bp.route("/<int:vehicule_id>", methods=["PUT"])
@jwt_required()
def update_vehicule(vehicule_id):
    user = Utilisateur.query.get(get_jwt_identity())
    vehicule = Vehicule.query.get(vehicule_id)

    if vehicule is None or vehicule.fournisseur_id != user.id:
        return jsonify({"error": "Véhicule introuvable ou accès interdit"}), 404

    vehicule.marque = request.form.get("marque", vehicule.marque)
    vehicule.modele = request.form.get("modele", vehicule.modele)
    vehicule.carburant = request.form.get("carburant", vehicule.carburant)
    vehicule.kilometrage = int(request.form.get("kilometrage", vehicule.kilometrage))
    vehicule.prix_jour = float(request.form.get("prix_jour", vehicule.prix_jour))

    image_file = request.files.get("image")
    if image_file:
        filename = secure_filename(image_file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(image_path)
        vehicule.image_path = image_path

    db.session.commit()
    return jsonify({"message": "Véhicule mis à jour avec succès"}), 200

# ❌ Supprimer un véhicule
@vehicules_bp.route("/<int:vehicule_id>", methods=["DELETE"])
@jwt_required()
def delete_vehicule(vehicule_id):
    user = Utilisateur.query.get(get_jwt_identity())
    vehicule = Vehicule.query.get(vehicule_id)

    if vehicule is None or vehicule.fournisseur_id != user.id:
        return jsonify({"error": "Véhicule introuvable ou accès interdit"}), 404

    if vehicule.image_path and os.path.exists(vehicule.image_path):
        os.remove(vehicule.image_path)

    db.session.delete(vehicule)
    db.session.commit()
    return jsonify({"message": "Véhicule supprimé avec succès"}), 200

# 🔍 Récupérer tous les véhicules selon rôle
@vehicules_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_vehicules():
    user = Utilisateur.query.get(get_jwt_identity())

    if user.role == RoleEnum.FOURNISSEUR:
        vehicules = Vehicule.query.filter_by(fournisseur_id=user.id).all()
    else:
        vehicules = Vehicule.query.all()

    result = [{
        "id": v.id,
        "marque": v.marque,
        "modele": v.modele,
        "carburant": v.carburant,
        "kilometrage": v.kilometrage,
        "prix_jour": v.prix_jour,
        "image_path": v.image_path,
        "is_assigned": v.is_assigned,
        "fournisseur": {
            "id": v.fournisseur.id,
            "nom": v.fournisseur.nom,
            "email": v.fournisseur.email
        }
    } for v in vehicules]

    return jsonify(result), 200

# ✅ Récupérer véhicules disponibles avec filtres
@vehicules_bp.route("/disponibles", methods=["GET"])
@jwt_required()
def get_vehicules_disponibles():
    user = Utilisateur.query.get(get_jwt_identity())

    if user.role not in [RoleEnum.USER, RoleEnum.FLEET_ADMIN]:
        return jsonify({"error": "Accès refusé"}), 403

    query = Vehicule.query.filter_by(is_assigned=False)

    fournisseur_id = request.args.get("fournisseur_id")
    prix_max = request.args.get("prix_jour")
    carburant = request.args.get("carburant")
    marque = request.args.get("marque")

    if fournisseur_id:
        query = query.filter_by(fournisseur_id=fournisseur_id)
    if prix_max:
        query = query.filter(Vehicule.prix_jour <= float(prix_max))
    if carburant:
        query = query.filter_by(carburant=carburant)
    if marque:
        query = query.filter(Vehicule.marque.ilike(f"%{marque}%"))

    vehicules = query.all()

    return jsonify([
        {
            "id": v.id,
            "marque": v.marque,
            "modele": v.modele,
            "carburant": v.carburant,
            "kilometrage": v.kilometrage,
            "prix_jour": v.prix_jour,
            "image_path": v.image_path,
            "fournisseur": {
                "id": v.fournisseur.id,
                "nom": v.fournisseur.nom,
                "email": v.fournisseur.email
            }
        }
        for v in vehicules
    ]), 200

# 🔍 Obtenir les détails d’un véhicule spécifique
@vehicules_bp.route("/<int:vehicule_id>", methods=["GET"])
@jwt_required()
def get_vehicule_by_id(vehicule_id):
    user = Utilisateur.query.get(get_jwt_identity())
    vehicule = Vehicule.query.get(vehicule_id)

    if not vehicule:
        return jsonify({"error": "Véhicule introuvable"}), 404

    # Fournisseur ne peut voir que ses propres véhicules
    if user.role == RoleEnum.FOURNISSEUR and vehicule.fournisseur_id != user.id:
        return jsonify({"error": "Accès interdit"}), 403

    # Tous les autres (USER, FLEET_ADMIN) peuvent voir
    return jsonify({
        "id": vehicule.id,
        "marque": vehicule.marque,
        "modele": vehicule.modele,
        "carburant": vehicule.carburant,
        "kilometrage": vehicule.kilometrage,
        "prix_jour": vehicule.prix_jour,
        "image_path": vehicule.image_path,
        "is_assigned": vehicule.is_assigned,
        "fournisseur": {
            "id": vehicule.fournisseur.id,
            "nom": vehicule.fournisseur.nom,
            "email": vehicule.fournisseur.email
        }
    }), 200
