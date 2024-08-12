import mysql.connector
import bcrypt

# Configuración de la base de datos
db_config = {
    'user': 'root',
    'host': 'localhost',
    'database': 'bd',
    'password': 'MiguelWorkbench009'
}

# Datos del profesor
no_trabajador = 12345678
nombres = 'Miguel Angel'
clave = '123456'

# Hashing de la contraseña
hashed_clave = bcrypt.hashpw(clave.encode('utf-8'), bcrypt.gensalt())

# Conexión y consulta
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO profesores (NoTrabajador, Nombres, Clave) VALUES (%s, %s, %s)",(no_trabajador, nombres, hashed_clave.decode('utf-8')))
    conn.commit()
    print("Profesor insertado correctamente.")
except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    cursor.close()
    conn.close()
