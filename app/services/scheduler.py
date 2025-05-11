from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date
from app.extensions import db
from app.models.contrat_location import ContratLocation

def unassign_expired_vehicules():
    from app.models.vehicule import Vehicule  # import local pour éviter les conflits circulaires
    today = date.today()
    contrats = ContratLocation.query.filter(
        ContratLocation.date_fin < today,
        ContratLocation.statut == "EN_COURS"
    ).all()

    for contrat in contrats:
        contrat.statut = "TERMINE"
        contrat.vehicule.is_assigned = False

    db.session.commit()
    print("[Scheduler] Désassignation des véhicules terminée.")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(unassign_expired_vehicules, "interval", hours=24)
    scheduler.start()
