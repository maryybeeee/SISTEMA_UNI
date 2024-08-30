import os
from datetime import timedelta

# Configuración de la base de datos
db_config = {
    'user': 'root',
    'password': 'MiguelWorkbench009',
    'host': 'localhost',
    'database': 'op',
    'port': 3306
}

class Config:
    SECRET_KEY = os.urandom(24)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'pdf'}