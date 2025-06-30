from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from app.models.user import Utilisateur, RoleEnum
from app.extensions import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(force=True)
    nom      = data.get("nom")
    email    = data.get("email")
    password = data.get("password")
    role_str = data.get("role")

    if not nom or not email or not password:
        return jsonify({"message": "Champs manquants"}), 400

    if Utilisateur.query.filter_by(email=email).first():
        return jsonify({"message": "Email déjà utilisé"}), 409

    try:
        role_enum = RoleEnum(role_str) if role_str else RoleEnum.USER
    except ValueError:
        role_enum = RoleEnum.USER

    user = Utilisateur(nom=nom, email=email, role=role_enum)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Utilisateur créé", "user_id": user.id}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Champs requis"}), 400

    user = Utilisateur.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Email ou mot de passe incorrect"}), 401

    if user.archiver:
        return jsonify({"message": "Ce compte a été archivé. Veuillez contacter l'administrateur."}), 403

    claims = {"role": user.role.value}
    access_token = create_access_token(identity=user.id, additional_claims=claims)
    refresh_token = create_refresh_token(identity=user.id)

    info_user = {
        "nom": user.nom,
        "email": user.email,
        "role": user.role.value,
        "id": user.id,
    }

    return jsonify(access_token=access_token, refresh_token=refresh_token, info_user=info_user), 200


@auth_bp.route('/login/mobile', methods=['POST'])
def mobile_login():
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Champs requis"}), 400

    user = Utilisateur.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Email ou mot de passe incorrect"}), 401

    if user.archiver:
        return jsonify({"message": "Ce compte a été archivé. Veuillez contacter l'administrateur."}), 403

    if user.role == RoleEnum.FLEET_ADMIN:
        return jsonify({"message": "Connexion interdite pour les administrateurs via l'application mobile"}), 403

    claims = {"role": user.role.value}
    access_token = create_access_token(identity=user.id, additional_claims=claims)
    refresh_token = create_refresh_token(identity=user.id)

    return jsonify({
        "access_token": access_token,
        "id": user.id,
        "email": user.email,
        "role": user.role.value.lower()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    claims  = get_jwt()

    user = Utilisateur.query.get(user_id)
    if not user:
        return jsonify({"message": "Utilisateur non trouvé"}), 404

    return jsonify({
        "id": user.id,
        "nom": user.nom,
        "email": user.email,
        "role": claims.get("role")
    }), 200


@auth_bp.route('/admin-only', methods=['GET'])
@jwt_required()
def admin_only():
    claims = get_jwt()
    if claims.get("role") != "FLEET_ADMIN":
        return jsonify({"message": "Accès réservé au Fleet Admin"}), 403
    return jsonify({"message": "Bienvenue, Fleet Admin"}), 200


@auth_bp.route("/utilisateurs", methods=["GET"])
@jwt_required()
def get_all_users():
    current_user_id = get_jwt_identity()
    user = Utilisateur.query.get(current_user_id)

    if user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    role_param = request.args.get("role")
    query = Utilisateur.query

    if role_param:
        role_map = {
            "user": RoleEnum.USER,
            "fournisseur": RoleEnum.FOURNISSEUR,
            "fleet_admin": RoleEnum.FLEET_ADMIN
        }
        role_enum = role_map.get(role_param.lower())
        if not role_enum:
            return jsonify({"error": f"Rôle invalide : {role_param}. Choisissez parmi: user, fournisseur, fleet_admin"}), 400

        query = query.filter_by(role=role_enum)

    utilisateurs = query.all()

    return jsonify([
        {
            "id": u.id,
            "nom": u.nom,
            "email": u.email,
            "role": u.role.value,
            "archiver": u.archiver,

        }
        for u in utilisateurs
    ])


@auth_bp.route("/utilisateurs/<int:user_id>/archiver", methods=["PUT"])
@jwt_required()
def archiver_utilisateur(user_id):
    current_user = Utilisateur.query.get(get_jwt_identity())

    if current_user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    user = Utilisateur.query.get(user_id)
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if user.archiver:
        return jsonify({"message": "Utilisateur déjà archivé"}), 400

    user.archiver = True
    db.session.commit()

    return jsonify({"message": f"Utilisateur {user.nom} archivé avec succès."}), 200

@auth_bp.route("/utilisateurs/<int:user_id>/desarchiver", methods=["PUT"])
@jwt_required()
def desarchiver_utilisateur(user_id):
    current_user = Utilisateur.query.get(get_jwt_identity())

    if current_user.role != RoleEnum.FLEET_ADMIN:
        return jsonify({"error": "Accès refusé"}), 403

    user = Utilisateur.query.get(user_id)
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    if not user.archiver:
        return jsonify({"message": "Utilisateur déjà actif"}), 400

    user.archiver = False
    db.session.commit()

    return jsonify({"message": f"Utilisateur {user.nom} désarchivé avec succès."}), 200
