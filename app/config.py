import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = 'clave-secreta-por-defecto'

    db_config = {
        'dbname': 'cpm_pert_db',
        'user': 'postgres',
        'password': 'admin',
        'host': 'localhost',
        'port': '5432'
    }

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
