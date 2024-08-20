import os

# Configuración de la base de datos
db_config = {
    'user': 'root',
    'password': 'MiguelWorkbench009',
    'host': 'localhost',
    'database': 'bd',
    'port': 3306
}

#Clave secreta
secret_key = os.urandom(24)

#Ruta de subida de rutas de los archivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}