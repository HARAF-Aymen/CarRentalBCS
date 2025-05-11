import os

class Config:
    """
    Configuration unique – lit tout depuis l’environnement ou utilise
    des valeurs par défaut si rien n’est fourni.
    """
    SECRET_KEY = os.getenv('SECRET_KEY', 'aymen')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+mysqlconnector://root:1234@localhost:3306/locvoiture_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Durées en secondes
    JWT_ACCESS_TOKEN_EXPIRES  = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 900))     # 15 min
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800)) # 7 jours

    # Système de notifs
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'harafaymen@gmail.com'
    MAIL_PASSWORD = 'Tuescon+123'
    MAIL_DEFAULT_SENDER = 'bckillsgroup@gmail.com'
