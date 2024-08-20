import mysql.connector
import bcrypt

db_config = {
    'user': 'root',
    'host': 'localhost',
    'database': 'bd',
    'password': 'MiguelWorkbench009'
}
def insert_data(cursor, query, data):
    try:
        cursor.execute(query, data)
    except mysql.connector.Error as err:
        print(f"Error al insertar datos: {err}")
        conn.rollback()
# Datos del profesor
profesor_data = {
    'NoTrabajador': 12345678,
    'Nombres': 'Miguel Angel',
    'Clave': bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
}
# Datos de los alumnos
alumnos_data = [
    (19020241, 'Sara Mayela', 'Ruvalcaba', 'Roque', '123456'),
    (19150003, 'Jorge Humberto', 'Gobera', 'Ledezma', '123456'),
    (19150114, 'Jessica', 'Avila', 'Navarro', '123456')
]
hashed_alumnos_data = [(no_control, nombres, apellidoP, apellidoM, bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')) for no_control, nombres, apellidoP, apellidoM, contrasena in alumnos_data]
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    insert_data(cursor, "INSERT INTO profesores (NoTrabajador, Nombres, Clave) VALUES (%s, %s, %s)", 
                (profesor_data['NoTrabajador'], profesor_data['Nombres'], profesor_data['Clave']))
    insert_data(cursor, "INSERT INTO alumnos (NoControl, Nombres, ApellidoP, ApellidoM, Contraseña) VALUES (%s, %s, %s, %s, %s)",
                hashed_alumnos_data[0])
    insert_data(cursor, "INSERT INTO alumnos (NoControl, Nombres, ApellidoP, ApellidoM, Contraseña) VALUES (%s, %s, %s, %s, %s)",
                hashed_alumnos_data[1])
    insert_data(cursor, "INSERT INTO alumnos (NoControl, Nombres, ApellidoP, ApellidoM, Contraseña) VALUES (%s, %s, %s, %s, %s)",
                hashed_alumnos_data[2])
    conn.commit()
    print("Profesor y alumnos insertados correctamente.")
except mysql.connector.Error as err:
    print(f"Error: {err}")
finally:
    cursor.close()
    conn.close()