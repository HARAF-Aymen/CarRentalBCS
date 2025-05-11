class Config:
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:1234@localhost/locvoiture_db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "aymen"
    JWT_ACCESS_TOKEN_EXPIRES = 3600
    JWT_REFRESH_TOKEN_EXPIRES = 86400
