from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, extract
from datetime import datetime, date

from app.extensions import db
from app.models.demande_location import DemandeLocation
from app.models.user import Utilisateur, RoleEnum
from app.models.vehicule import Vehicule
from app.models.contrat_location import ContratLocation
from app.models.demande_mission import DemandeMission  # ✅ AJOUT : pour compter les missions


dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
def fleet_dashboard():
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)

    if user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    # ✅ AJOUT : nombre total d’employés (role = USER)
    nombre_employes = db.session.query(func.count(Utilisateur.id)).filter_by(role=RoleEnum.USER).scalar()

    # ✅ Renommage pour cohérence
    nombre_vehicules = db.session.query(func.count(Vehicule.id)).scalar()
    assigned = db.session.query(func.count(Vehicule.id)).filter_by(is_assigned=True).scalar()
    unassigned = nombre_vehicules - assigned

    # ✅ AJOUT : nombre total de missions
    nombre_missions = db.session.query(func.count(DemandeMission.id)).scalar()

    # ✅ AJOUT : nombre total de contrats
    nombre_contrats = db.session.query(func.count(ContratLocation.id)).scalar()

    # Contrats créés ce mois-ci
    this_month = datetime.now().month
    this_year = datetime.now().year
    contrats_ce_mois = db.session.query(func.count(ContratLocation.id)).filter(
        extract('month', ContratLocation.date_signature) == this_month,
        extract('year', ContratLocation.date_signature) == this_year
    ).scalar()

    # Jours loués ce mois-ci
    jours_loues = db.session.query(func.sum(func.datediff(ContratLocation.date_fin, ContratLocation.date_debut))).filter(
        extract('month', ContratLocation.date_signature) == this_month,
        extract('year', ContratLocation.date_signature) == this_year
    ).scalar() or 0

    # Jours loués par mois (courbe annuelle)
    monthly_rentals = []
    for month in range(1, 13):
        total_days = db.session.query(
            func.sum(func.datediff(ContratLocation.date_fin, ContratLocation.date_debut))
        ).filter(
            extract('month', ContratLocation.date_signature) == month,
            extract('year', ContratLocation.date_signature) == this_year
        ).scalar() or 0

        month_label = datetime(2024, month, 1).strftime('%b')  # Jan, Feb...
        monthly_rentals.append({"month": month_label, "days": int(total_days)})

    # Marques les plus louées
    top_marques = db.session.query(
        Vehicule.marque, func.count(ContratLocation.id).label("nb")
    ).join(ContratLocation).group_by(Vehicule.marque).order_by(func.count().desc()).limit(5).all()

    return jsonify({
        "nombre_employes": nombre_employes,  # ✅
        "nombre_vehicules": nombre_vehicules,  # ✅
        "assigned": assigned,
        "unassigned": unassigned,
        "nombre_missions": nombre_missions,  # ✅
        "nombre_contrats": nombre_contrats,  # ✅
        "contrats_ce_mois": contrats_ce_mois,
        "jours_loues": jours_loues,
        "top_marques": [{"marque": m, "count": n} for m, n in top_marques],
        "monthly_rentals": monthly_rentals
    })

# ✅ ROUTE FOURNISSEUR
@dashboard_bp.route("/fournisseur", methods=["GET"])
@jwt_required()
def fournisseur_dashboard():
    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user.role != RoleEnum.FOURNISSEUR:
        return jsonify({"error": "Accès refusé"}), 403

    nombre_vehicules = db.session.query(func.count(Vehicule.id)).filter_by(fournisseur_id=user.id).scalar()

    today = date.today()
    contrats_en_cours = db.session.query(func.count(ContratLocation.id))\
        .join(Vehicule)\
        .filter(
            Vehicule.fournisseur_id == user.id,
            ContratLocation.date_fin >= today
        ).scalar()

    demandes_acceptees = db.session.query(func.count()).select_from(DemandeLocation)\
        .join(Vehicule)\
        .filter(
            Vehicule.fournisseur_id == user.id,
            DemandeLocation.statut == "acceptee"
        ).scalar()

    demandes_refusees = db.session.query(func.count()).select_from(DemandeLocation)\
        .join(Vehicule)\
        .filter(
            Vehicule.fournisseur_id == user.id,
            DemandeLocation.statut == "refusee"
        ).scalar()

    # Évolution mensuelle des jours loués (pour les véhicules de ce fournisseur) BAR CHART
    monthly_rentals = []
    for month in range(1, 13):
        total_days = db.session.query(
            func.sum(func.datediff(ContratLocation.date_fin, ContratLocation.date_debut))
        ).join(Vehicule).filter(
            Vehicule.fournisseur_id == user.id,
            extract('month', ContratLocation.date_signature) == month,
            extract('year', ContratLocation.date_signature) == datetime.now().year
        ).scalar() or 0

        month_label = datetime(2024, month, 1).strftime('%b')
        monthly_rentals.append({"month": month_label, "days": int(total_days)})


    # Top modèles ou marques du fournisseur (loués le plus souvent)  Camembert CHART
    top_marques = db.session.query(
        Vehicule.marque,
        func.count(ContratLocation.id).label("nb")
    ).join(ContratLocation).filter(
        Vehicule.fournisseur_id == user.id
    ).group_by(Vehicule.marque).order_by(func.count().desc()).limit(5).all()

    return jsonify({
        "nombre_vehicules": nombre_vehicules,
        "contrats_en_cours": contrats_en_cours,
        "demandes_acceptees": demandes_acceptees,
        "demandes_refusees": demandes_refusees,
        "monthly_rentals": monthly_rentals,  # 🔥 ajout pour le graphique en courbe
        "top_marques": [{"marque": m, "count": n} for m, n in top_marques]  # 🔥 ajout pour un camembert ou bar chart
    })

