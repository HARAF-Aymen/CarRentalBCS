# app/commands/unassign.py
from flask.cli import with_appcontext
from app.models.contrat_location import ContratLocation
from app.extensions import db
from datetime import date

import click

@click.command("unassign_vehicules")
@with_appcontext
def unassign_vehicules():
    from app.models.vehicule import Vehicule
    today = date.today()
    contrats = ContratLocation.query.filter(ContratLocation.date_fin < today, ContratLocation.statut == "EN_COURS").all()
    for contrat in contrats:
        contrat.statut = "TERMINE"
        contrat.vehicule.is_assigned = False
    db.session.commit()
    print("Désassignation effectuée.")
