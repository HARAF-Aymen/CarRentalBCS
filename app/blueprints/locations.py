from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.demande_location import DemandeLocation
from app.models.demande_mission import DemandeMission
from app.models.user import Utilisateur, RoleEnum
from app.extensions import db
from datetime import datetime
from app.models.contrat_location import ContratLocation
from app.models.vehicule import Vehicule

locations_bp = Blueprint("locations", __name__)

# 🟢 Route 1: Créer une demande de location (Fleet Admin)
@locations_bp.route("/", methods=["POST"])
@jwt_required()
def creer_demande_location():
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)

    if user is None or user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Seuls les Fleet Admin peuvent créer une demande de location"}), 403

    data = request.get_json()
    mission_id = data.get("mission_id")

    if not mission_id:
        return jsonify({"error": "L'identifiant de la mission est requis"}), 400

    mission = DemandeMission.query.get(mission_id)
    if not mission or mission.statut != "APPROUVEE":
        return jsonify({"error": "Mission introuvable ou non approuvée"}), 404

    existing_location = DemandeLocation.query.filter_by(mission_id=mission.id).first()
    if existing_location:
        return jsonify({"error": "Une demande de location existe déjà pour cette mission"}), 400

    vehicule = Vehicule.query.get(mission.vehicule_id)
    if not vehicule:
        return jsonify({"error": "Véhicule introuvable"}), 404

    demande_location = DemandeLocation(
        mission_id=mission.id,
        vehicule_id=vehicule.id,
        fournisseur_id=vehicule.fournisseur_id,
        statut="EN_ATTENTE",
        created_at=datetime.utcnow()
    )

    db.session.add(demande_location)
    db.session.commit()

    return jsonify({"message": "Demande de location créée avec succès"}), 201

# 🟢 Route 2: Voir les demandes reçues (Fournisseur)
@locations_bp.route("/recues", methods=["GET"])
@jwt_required()
def get_demandes_recues():
    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user is None or user.role != RoleEnum.FOURNISSEUR:
        return jsonify({"error": "Accès réservé aux fournisseurs"}), 403

    demandes = DemandeLocation.query.filter_by(fournisseur_id=user.id).all()
    result = [{
        "id": d.id,
        "mission_id": d.mission_id,
        "vehicule_id": d.vehicule_id,
        "statut": d.statut,
        "date_reception": d.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for d in demandes]

    return jsonify(result), 200

# 🟢 Route 3: Fournisseur accepte ou refuse une demande
@locations_bp.route("/<int:location_id>/decision", methods=["PUT"])
@jwt_required()
def decision_location(location_id):
    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user is None or user.role != RoleEnum.FOURNISSEUR:
        return jsonify({"error": "Accès refusé"}), 403

    location = DemandeLocation.query.get(location_id)
    if location is None or location.fournisseur_id != user.id:
        return jsonify({"error": "Demande introuvable ou non autorisée"}), 404

    data = request.get_json()
    decision = data.get("decision")

    if decision not in ["ACCEPTEE", "REFUSEE"]:
        return jsonify({"error": "Décision invalide (ACCEPTEE ou REFUSEE)"}), 400

    location.statut = decision
    db.session.commit()

    return jsonify({"message": f"Demande de location {decision.lower()} avec succès"}), 200

# 🟢 Route 4: Fleet Admin génère un contrat si la demande est acceptée
@locations_bp.route("/<int:location_id>/generer-contrat", methods=["POST"])
@jwt_required()
def generer_contrat(location_id):
    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user is None or user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    location = DemandeLocation.query.get(location_id)
    if not location or location.statut != "ACCEPTEE":
        return jsonify({"error": "Location introuvable ou non acceptée"}), 404

    mission = location.mission
    date_debut = mission.date_debut
    date_fin = mission.date_fin

    conflits = ContratLocation.query.filter(
        ContratLocation.vehicule_id == mission.vehicule_id,
        ContratLocation.statut == "EN_COURS",
        db.or_(
            db.and_(ContratLocation.date_debut <= date_debut, ContratLocation.date_fin >= date_debut),
            db.and_(ContratLocation.date_debut <= date_fin, ContratLocation.date_fin >= date_fin),
            db.and_(ContratLocation.date_debut >= date_debut, ContratLocation.date_fin <= date_fin)
        )
    ).first()

    if conflits:
        return jsonify({"error": "Le véhicule est déjà assigné durant cette période"}), 400

    contrat = ContratLocation(
        location_id=location.id,
        utilisateur_id=mission.user_id,
        vehicule_id=mission.vehicule_id,
        date_debut=date_debut,
        date_fin=date_fin,
        statut="EN_COURS"
    )

    # Assigner le véhicule
    vehicule = Vehicule.query.get(mission.vehicule_id)
    if not vehicule:
        return jsonify({"error": "Véhicule introuvable"}), 404

    vehicule.is_assigned = True

    db.session.add(contrat)
    db.session.commit()

    return jsonify({
        "message": "Contrat généré avec succès",
        "contrat": {
            "id": contrat.id,
            "vehicule_id": contrat.vehicule_id,
            "utilisateur_id": contrat.utilisateur_id,
            "date_debut": contrat.date_debut.strftime("%Y-%m-%d"),
            "date_fin": contrat.date_fin.strftime("%Y-%m-%d"),
            "statut": contrat.statut
        }
    }), 201
