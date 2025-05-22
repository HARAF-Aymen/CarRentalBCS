from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.demande_mission import DemandeMission
from app.models.user import Utilisateur, RoleEnum
from app.models.vehicule import Vehicule
from app.extensions import db
from datetime import datetime
from app.utils.email_utils import send_email
from app.models.contrat_location import ContratLocation




missions_bp = Blueprint("missions", __name__)

#  Route : Créer une demande de mission (UTILISATEUR)
@missions_bp.route("/", methods=["POST"])
@jwt_required()
def create_mission():
    """
    Un utilisateur simple fait une demande de mission pour un véhicule.
    """
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)

    if user is None or user.role != RoleEnum.USER:
        return jsonify({"error": "Seuls les utilisateurs peuvent faire une demande"}), 403

    data = request.get_json()
    vehicule_id = data.get("vehicule_id")
    date_debut = data.get("date_debut")
    date_fin = data.get("date_fin")
    motif = data.get("motif")

    if not all([vehicule_id, date_debut, date_fin]):
        return jsonify({"error": "Champs manquants"}), 400

    try:
        date_debut = datetime.strptime(date_debut, "%Y-%m-%d")
        date_fin = datetime.strptime(date_fin, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Format de date invalide (attendu YYYY-MM-DD)"}), 400

    demande = DemandeMission(
        user_id=user.id,
        vehicule_id=vehicule_id,
        date_debut=date_debut,
        date_fin=date_fin,
        motif=motif
    )

    db.session.add(demande)
    db.session.commit()

    return jsonify({"message": "Demande de mission envoyée avec succès"}), 201


#  Route : Récupérer toutes les demandes de mission (FLEET_ADMIN)

@missions_bp.route("/", methods=["GET"])
@jwt_required()
def get_all_missions():
    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user is None or user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    missions = DemandeMission.query.all()

    result = []
    for m in missions:
        vehicule = Vehicule.query.get(m.vehicule_id)
        user = Utilisateur.query.get(m.user_id)

        result.append({
            "id": m.id,
            "vehicule": {
                "id": vehicule.id,
                "modele": vehicule.modele
            } if vehicule else None,
            "user": {
                "id": user.id,
                "nom": user.nom
            } if user else None,
            "date_debut": m.date_debut.strftime("%Y-%m-%d"),
            "date_fin": m.date_fin.strftime("%Y-%m-%d"),
            "status": m.statut,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(result), 200


#  Route : Prendre une décision sur une mission (FLEET_ADMIN)
@missions_bp.route("/<int:mission_id>/decision", methods=["PUT"])
@jwt_required()
def decision_mission(mission_id):

    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user is None or user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    data = request.get_json()
    decision = data.get("decision")

    if decision not in ["APPROUVEE", "REFUSEE"]:
        return jsonify({"error": "Décision invalide"}), 400

    mission = DemandeMission.query.get(mission_id)
    if mission is None:
        return jsonify({"error": "Demande non trouvée"}), 404

    mission.statut = decision
    db.session.commit()

    # Notification à l'utilisateur
    utilisateur = Utilisateur.query.get(mission.user_id)
    if utilisateur:
        send_email(
            subject="Mise à jour de votre demande de mission",
            recipient=utilisateur.email,
            body=f"Votre demande de mission du {mission.date_debut.strftime('%Y-%m-%d')} au {mission.date_fin.strftime('%Y-%m-%d')} a été {decision.lower()}."
        )

    return jsonify({
        "message": f"Demande {decision.lower()} avec succès",
        "vehicule_id": mission.vehicule_id if decision == "APPROUVEE" else None,
        "mission_id": mission.id
    }), 200


@missions_bp.route("/mes", methods=["GET"])
@jwt_required()
def get_mes_missions():

    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)

    if user is None or user.role != RoleEnum.USER:
        return jsonify({"error": "Accès réservé aux utilisateurs simples"}), 403

    missions = DemandeMission.query.filter_by(user_id=user.id).all()

    result = []
    for m in missions:
        vehicule = Vehicule.query.get(m.vehicule_id)  # Récupération du modèle
        result.append({
            "id": m.id,
            "vehicule_id": m.vehicule_id,
            "vehicule_modele": vehicule.modele if vehicule else "Inconnu",
            "date_debut": m.date_debut.strftime("%Y-%m-%d"),
            "date_fin": m.date_fin.strftime("%Y-%m-%d"),
            "status": m.statut,
            "motif": m.motif,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(result), 200

@missions_bp.route("/approved_without_contract", methods=["GET"])
@jwt_required()
def get_approved_without_contract():

    user = Utilisateur.query.get(get_jwt_identity())
    if user is None or user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    subquery = db.session.query(ContratLocation.location_id)
    missions = (
        DemandeMission.query
        .filter(DemandeMission.statut == "APPROUVEE")
        .filter(~DemandeMission.id.in_(subquery))
        .all()
    )

    result = []
    for m in missions:
        result.append({
            "id": m.id,
            "vehicule_id": m.vehicule_id,
            "user_id": m.user_id,
            "date_debut": m.date_debut.strftime("%Y-%m-%d"),
            "date_fin": m.date_fin.strftime("%Y-%m-%d"),
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(result), 200