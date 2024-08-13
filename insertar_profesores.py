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

# Datos del alumno
A1_no_control = 19020241
A1_nombres = 'Sara Mayela'
A1_apellidoP = 'Ruvalcaba'
A1_apellidoM = 'Roque'
A1_contraseña = '123456'

A2_no_control = 19150003
A2_nombres = 'Jorge Humberto'
A2_apellidoP = 'Gobera'
A2_apellidoM = 'Ledezma'
A2_contraseña = '123456'

A3_no_control = 19150114
A3_nombres = 'Jessica'
A3_apellidoP = 'Avila'
A3_apellidoM = 'Navarro'
A3_contraseña = '123456'

# Hashing de la contraseña
hashed_clave1 = bcrypt.hashpw(A1_contraseña.encode('utf-8'), bcrypt.gensalt())
hashed_clave2 = bcrypt.hashpw(A2_contraseña.encode('utf-8'), bcrypt.gensalt())
hashed_clave3 = bcrypt.hashpw(A3_contraseña.encode('utf-8'), bcrypt.gensalt())

# Conexión y consulta
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO alumnos (Nombres, ApellidoP, ApellidoM, Contraseña, NoControl) VALUES (%s,%s,%s,%s,%s)", (A1_nombres, A1_apellidoP, A1_apellidoM, hashed_clave1.decode('utf-8'), A1_no_control))
    conn.commit()
    cursor.execute("INSERT INTO alumnos (Nombres, ApellidoP, ApellidoM, Contraseña, NoControl) VALUES (%s,%s,%s,%s,%s)", (A2_nombres, A2_apellidoP, A2_apellidoM, hashed_clave2.decode('utf-8'), A2_no_control))
    conn.commit()
    cursor.execute("INSERT INTO alumnos (Nombres, ApellidoP, ApellidoM, Contraseña, NoControl) VALUES (%s,%s,%s,%s,%s)", (A3_nombres, A3_apellidoP, A3_apellidoM, hashed_clave3.decode('utf-8'), A3_no_control))
    conn.commit()
    print("Alumnos insertados correctamente.")
except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    cursor.close()
    conn.close()
