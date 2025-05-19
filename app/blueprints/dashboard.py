from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, extract
from datetime import datetime


from app.extensions import db
from app.models.user import Utilisateur, RoleEnum
from app.models.vehicule import Vehicule
from app.models.contrat_location import ContratLocation

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
def fleet_dashboard():
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)

    if user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    total_vehicules = db.session.query(func.count(Vehicule.id)).scalar()
    assigned = db.session.query(func.count(Vehicule.id)).filter_by(is_assigned=True).scalar()
    unassigned = total_vehicules - assigned

    # Nombre de contrats créés ce mois-ci
    this_month = datetime.now().month
    this_year = datetime.now().year
    contrats_ce_mois = db.session.query(func.count(ContratLocation.id)).filter(
        extract('month', ContratLocation.date_signature) == this_month,
        extract('year', ContratLocation.date_signature) == this_year
    ).scalar()

    # Jours totaux loués ce mois
    jours_loues = db.session.query(func.sum(func.datediff(ContratLocation.date_fin, ContratLocation.date_debut))).filter(
        extract('month', ContratLocation.date_signature) == this_month,
        extract('year', ContratLocation.date_signature) == this_year
    ).scalar() or 0

    # 📊 Jours loués par mois pour l’année en cours (MySQL-compatible)
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
        "total_vehicules": total_vehicules,
        "assigned": assigned,
        "unassigned": unassigned,
        "contrats_ce_mois": contrats_ce_mois,
        "jours_loues": jours_loues,
        "top_marques": [{"marque": m, "count": n} for m, n in top_marques],
        "monthly_rentals": monthly_rentals  # ✅ NEW
    })

