import os
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Image
from app.utils.email_utils import send_email


from flask import request
from sqlalchemy import and_

from app.models.user import Utilisateur, RoleEnum
from app.models.contrat_location import ContratLocation
from app.models.vehicule import Vehicule
from app.extensions import db

contrats_bp = Blueprint("contrats", __name__)

# 📌 GET /api/contrats : Fleet Admin voit tous, Fournisseur voit les siens
@contrats_bp.route("/", methods=["GET"])
@jwt_required()
def get_contrats():
    """
    Permet au FLEET_ADMIN ou au FOURNISSEUR de voir les contrats qu’il a générés ou reçus.
    """
    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user is None:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if user.role == RoleEnum.FLEET_ADMIN:
        contrats = ContratLocation.query.all()
    elif user.role == RoleEnum.FOURNISSEUR:
        contrats = (
            ContratLocation.query
            .join(Vehicule)
            .filter(Vehicule.fournisseur_id == user.id)
            .all()
        )
    else:
        return jsonify({"error": "Accès refusé"}), 403

    result = []
    for c in contrats:
        result.append({
            "id": c.id,
            "vehicule_id": c.vehicule_id,
            "utilisateur_id": c.utilisateur_id,
            "date_debut": c.date_debut.strftime("%Y-%m-%d"),
            "date_fin": c.date_fin.strftime("%Y-%m-%d"),
            "statut": c.statut,
            "date_signature": c.date_signature.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(result), 200

# 📌 PUT /api/contrats/<id>/assigner : Assignation par Fleet Admin
@contrats_bp.route("/<int:contrat_id>/assigner", methods=["PUT"])
@jwt_required()
def assigner_vehicule(contrat_id):
    """
    Le Fleet Admin assigne un véhicule à l’utilisateur et met à jour le statut.
    """
    user_id = get_jwt_identity()
    admin = Utilisateur.query.get(user_id)

    if admin is None or admin.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    contrat = ContratLocation.query.get(contrat_id)
    if not contrat:
        return jsonify({"error": "Contrat introuvable"}), 404

    if contrat.statut != "EN_COURS":
        return jsonify({"error": "Le contrat a déjà été traité"}), 400

    vehicule = Vehicule.query.get(contrat.vehicule_id)
    if not vehicule:
        return jsonify({"error": "Véhicule introuvable"}), 404

    vehicule.is_assigned = True
    contrat.statut = "TERMINE"

    db.session.commit()

    return jsonify({"message": "Véhicule assigné et contrat terminé avec succès"}), 200

# 📌 GET /api/contrats/mes : Voir ses propres contrats (Utilisateur simple uniquement)
@contrats_bp.route("/mes", methods=["GET"])
@jwt_required()
def get_mes_contrats():
    """
    Permet à un utilisateur simple de consulter ses propres contrats.
    """
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)

    if user is None:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if user.role != RoleEnum.USER:
        return jsonify({"error": "Accès réservé aux utilisateurs simples"}), 403

    contrats = ContratLocation.query.filter_by(utilisateur_id=user.id).all()

    result = []
    for c in contrats:
        result.append({
            "id": c.id,
            "vehicule_id": c.vehicule_id,
            "date_debut": c.date_debut.strftime("%Y-%m-%d"),
            "date_fin": c.date_fin.strftime("%Y-%m-%d"),
            "statut": c.statut,
            "date_signature": c.date_signature.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(result), 200

# 📌 GET /api/contrats/<id> : Détails d’un contrat (Fleet Admin uniquement)
@contrats_bp.route("/<int:contrat_id>", methods=["GET"])
@jwt_required()
def get_contrat_details(contrat_id):
    """
    Permet au Fleet Admin de consulter les détails d’un contrat spécifique.
    """
    user_id = get_jwt_identity()
    user = Utilisateur.query.get(user_id)

    if user is None or user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    contrat = ContratLocation.query.get(contrat_id)
    if not contrat:
        return jsonify({"error": "Contrat introuvable"}), 404

    vehicule = contrat.vehicule
    utilisateur = contrat.utilisateur

    return jsonify({
        "contrat": {
            "id": contrat.id,
            "statut": contrat.statut,
            "date_signature": contrat.date_signature.strftime("%Y-%m-%d %H:%M:%S"),
            "date_debut": contrat.date_debut.strftime("%Y-%m-%d"),
            "date_fin": contrat.date_fin.strftime("%Y-%m-%d"),
        },
        "vehicule": {
            "id": vehicule.id,
            "marque": vehicule.marque,
            "modele": vehicule.modele,
            "carburant": vehicule.carburant,
            "kilometrage": vehicule.kilometrage,
            "prix_jour": vehicule.prix_jour,
        },
        "utilisateur": {
            "id": utilisateur.id,
            "nom": utilisateur.nom,
            "email": utilisateur.email
        }
    }), 200

@contrats_bp.route("/<int:contrat_id>/pdf", methods=["GET"])
@jwt_required()
def telecharger_contrat_pdf(contrat_id):
    from reportlab.lib.utils import ImageReader
    user = Utilisateur.query.get(get_jwt_identity())
    if user is None:
        return jsonify({"error": "Utilisateur non trouvé"}), 403

    contrat = ContratLocation.query.get(contrat_id)
    if not contrat:
        return jsonify({"error": "Contrat introuvable"}), 404

    # ✅ Autoriser si FLEET_ADMIN ou utilisateur concerné
    if user.role != RoleEnum.FLEET_ADMIN and contrat.utilisateur_id != user.id:
        return jsonify({"error": "Vous n'avez pas accès à ce contrat"}), 403

    vehicule = contrat.vehicule
    fournisseur = vehicule.fournisseur if vehicule else None

    pdf_dir = os.path.join(os.getcwd(), 'contracts')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"contrat_{contrat.id}.pdf")

    p = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 50

    def ligne(text, y, bold=False):
        if bold:
            p.setFont("Helvetica-Bold", 12)
        else:
            p.setFont("Helvetica", 12)
        p.drawString(50, y, text)
        return y - 20

    # 🖼 Logo
    logo_path = os.path.join("static", "logo.png")
    if os.path.exists(logo_path):
        logo = ImageReader(logo_path)
        p.drawImage(logo, 50, y - 80, width=100, preserveAspectRatio=True, mask='auto')
        y -= 90

    # 🖋 Titre
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, y, "CONTRAT DE LOCATION DE VÉHICULE")
    y -= 40

    # 📝 Infos contrat
    y = ligne(f"Contrat ID : {contrat.id}", y)
    y = ligne(f"Date de signature : {contrat.date_signature.strftime('%Y-%m-%d %H:%M:%S')}", y)
    y = ligne(f"Statut : {contrat.statut}", y)
    y = ligne(f"Période : du {contrat.date_debut.strftime('%Y-%m-%d')} au {contrat.date_fin.strftime('%Y-%m-%d')}", y)

    # 👤 Utilisateur
    y = ligne("Informations de l'utilisateur :", y, bold=True)
    y = ligne(f"Nom : {contrat.utilisateur.nom}", y)
    y = ligne(f"Email : {contrat.utilisateur.email}", y)

    # 🚘 Véhicule
    y = ligne("Informations du véhicule :", y, bold=True)
    y = ligne(f"Marque : {vehicule.marque}", y)
    y = ligne(f"Modèle : {vehicule.modele}", y)
    y = ligne(f"Carburant : {vehicule.carburant}", y)
    y = ligne(f"Kilométrage : {vehicule.kilometrage} km", y)
    y = ligne(f"Prix par jour : {vehicule.prix_jour} MAD", y)

    # 🤝 Fournisseur
    if fournisseur:
        y = ligne("Informations du fournisseur :", y, bold=True)
        y = ligne(f"Nom : {fournisseur.nom}", y)
        y = ligne(f"Email : {fournisseur.email}", y)

    p.showPage()
    p.save()

    # ✉️ Envoi d'un email à l'utilisateur
    email_body = f"""Bonjour {contrat.utilisateur.nom},

    Votre contrat de location a été généré avec succès pour le véhicule {vehicule.marque} {vehicule.modele}.

    Période de location : du {contrat.date_debut.strftime('%Y-%m-%d')} au {contrat.date_fin.strftime('%Y-%m-%d')}
    Statut : {contrat.statut}

    Merci de vérifier votre tableau de bord pour plus de détails.
    """

    send_email(
        subject="Contrat de location généré",
        recipient=contrat.utilisateur.email,  # ✅ correct
        body=email_body
    )

    return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path), mimetype='application/pdf')


@contrats_bp.route("/<int:contrat_id>/pdf-fournisseur", methods=["GET"])
@jwt_required()
def telecharger_pdf_fournisseur(contrat_id):
    """
    Permet à un fournisseur de télécharger le contrat PDF si le véhicule lui appartient.
    """
    user = Utilisateur.query.get(get_jwt_identity())
    if user is None or user.role != RoleEnum.FOURNISSEUR:
        return jsonify({"error": "Accès réservé aux fournisseurs"}), 403

    contrat = ContratLocation.query.get(contrat_id)
    if not contrat:
        return jsonify({"error": "Contrat introuvable"}), 404

    vehicule = contrat.vehicule
    if vehicule.fournisseur_id != user.id:
        return jsonify({"error": "Ce contrat n'est pas lié à vos véhicules"}), 403

    # 🔍 Recherche du fichier PDF
    pdf_path = os.path.join("contracts", f"contrat_{contrat.id}.pdf")
    if not os.path.exists(pdf_path):
        # ✅ On régénère le PDF si nécessaire
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader

        pdf_dir = os.path.join(os.getcwd(), 'contracts')
        os.makedirs(pdf_dir, exist_ok=True)

        p = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        y = height - 50

        def ligne(text, y, bold=False):
            p.setFont("Helvetica-Bold" if bold else "Helvetica", 12)
            p.drawString(50, y, text)
            return y - 20

        logo_path = os.path.join("static", "logo.png")
        if os.path.exists(logo_path):
            logo = ImageReader(logo_path)
            p.drawImage(logo, 50, y - 80, width=100, preserveAspectRatio=True, mask='auto')
            y -= 90

        p.setFont("Helvetica-Bold", 16)
        p.drawCentredString(width / 2, y, "CONTRAT DE LOCATION DE VÉHICULE")
        y -= 40

        y = ligne(f"Contrat ID : {contrat.id}", y)
        y = ligne(f"Date de signature : {contrat.date_signature.strftime('%Y-%m-%d %H:%M:%S')}", y)
        y = ligne(f"Statut : {contrat.statut}", y)
        y = ligne(f"Période : du {contrat.date_debut.strftime('%Y-%m-%d')} au {contrat.date_fin.strftime('%Y-%m-%d')}",
                  y)

        y = ligne("Informations de l'utilisateur :", y, bold=True)
        y = ligne(f"Nom : {contrat.utilisateur.nom}", y)
        y = ligne(f"Email : {contrat.utilisateur.email}", y)

        y = ligne("Informations du véhicule :", y, bold=True)
        y = ligne(f"Marque : {vehicule.marque}", y)
        y = ligne(f"Modèle : {vehicule.modele}", y)
        y = ligne(f"Carburant : {vehicule.carburant}", y)
        y = ligne(f"Kilométrage : {vehicule.kilometrage} km", y)
        y = ligne(f"Prix par jour : {vehicule.prix_jour} MAD", y)

        y = ligne("Informations du fournisseur :", y, bold=True)
        y = ligne(f"Nom : {user.nom}", y)
        y = ligne(f"Email : {user.email}", y)

        p.showPage()
        p.save()

    return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path), mimetype='application/pdf')

@contrats_bp.route("/recherche", methods=["GET"])
@jwt_required()
def rechercher_contrats():
    """
    Filtrer les contrats selon statut, utilisateur, fournisseur, ou date.
    Accessible uniquement au Fleet Admin.
    """
    user = Utilisateur.query.get(get_jwt_identity())
    if user is None or user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    statut = request.args.get("statut")
    utilisateur_id = request.args.get("utilisateur_id")
    fournisseur_id = request.args.get("fournisseur_id")
    date_debut = request.args.get("date_debut")
    date_fin = request.args.get("date_fin")

    query = ContratLocation.query.join(Vehicule)

    if statut:
        query = query.filter(ContratLocation.statut == statut)
    if utilisateur_id:
        query = query.filter(ContratLocation.utilisateur_id == utilisateur_id)
    if fournisseur_id:
        query = query.filter(Vehicule.fournisseur_id == fournisseur_id)
    if date_debut and date_fin:
        query = query.filter(and_(
            ContratLocation.date_debut >= date_debut,
            ContratLocation.date_fin <= date_fin
        ))

    contrats = query.all()

    result = []
    for c in contrats:
        result.append({
            "id": c.id,
            "vehicule_id": c.vehicule_id,
            "utilisateur_id": c.utilisateur_id,
            "date_debut": c.date_debut.strftime("%Y-%m-%d"),
            "date_fin": c.date_fin.strftime("%Y-%m-%d"),
            "statut": c.statut,
            "date_signature": c.date_signature.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(result), 200

from app.models.demande_mission import DemandeMission  # à importer en haut si pas encore fait

@contrats_bp.route("/", methods=["POST"])
@jwt_required()
def create_contrat():
    """
    Le Fleet Admin génère un contrat pour une mission approuvée.
    """
    user = Utilisateur.query.get(get_jwt_identity())
    if user is None or user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    data = request.get_json()
    mission_id = data.get("mission_id")
    vehicule_id = data.get("vehicule_id")

    mission = DemandeMission.query.get(mission_id)
    vehicule = Vehicule.query.get(vehicule_id)

    if not mission or mission.statut != "APPROUVEE":
        return jsonify({"error": "Mission invalide ou non approuvée"}), 400

    if not vehicule or vehicule.is_assigned:
        return jsonify({"error": "Véhicule non disponible"}), 400

    # Génération du contrat
    contrat = ContratLocation(
        location_id=mission.id,
        utilisateur_id=mission.user_id,
        vehicule_id=vehicule.id,
        date_debut=mission.date_debut,
        date_fin=mission.date_fin,
    )

    vehicule.is_assigned = True

    db.session.add(contrat)
    db.session.commit()

    return jsonify({"message": "Contrat généré avec succès", "contrat_id": contrat.id}), 201

