from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, abort
from config import db_config, Config
from werkzeug.utils import secure_filename
import bcrypt
import mysql.connector
import logging
import os

# Configuracion de la aplicación Flask
app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']


# Ruta principal de la aplicación
@app.route('/')
def index():
    return render_template('index.html')

# Ruta de registro de alumnos
@app.route('/register_alumnos')
def register_alumnos():
    return render_template('alumnos/register_alumnos.html')

# Metodo para registrar a un alumno en la tabla alumnos
@app.route('/registro_alumnos', methods=['POST', 'GET'])
def registro_alumnos():
    # Registra a un nuevo alumno en la base de datos
    if request.method == 'POST':
        # Recolecta los datos del formulario
        names = request.form['names']
        last_name1 = request.form['last_name1']
        last_name2 = request.form['last_name2']
        control_number = request.form['control_number']
        # Encripta la contraseña
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            # Conecta a la base de datos
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            print("Conexión a la base de datos establecida")
            # Verifica si el numero de control ya existe en jornadas_academicas
            cursor.execute("SELECT * FROM jornadas_academicas WHERE  ApellidoP = %s AND ApellidoM = %s AND Nombres = %s AND NoControl = %s", (last_name1, last_name2, names, control_number,))
            jornada_academica = cursor.fetchone()
            # Verifica si el numero de control ya existe en tutorias
            cursor.execute("SELECT * FROM tutorias WHERE ApellidoP = %s AND ApellidoM = %s AND Nombres = %s AND NoControl = %s", (last_name1, last_name2, names, control_number,))
            tutoria = cursor.fetchone()
            if jornada_academica or tutoria:
                # Verifica si el alumno ya esta registrado en la tabla alumnos
                cursor.execute("SELECT * FROM alumnos WHERE ApellidoP = %s AND ApellidoM = %s AND Nombres = %s AND NoControl = %s", (last_name1, last_name2, names, control_number,))
                user = cursor.fetchone()
                if user:
                    flash('Usuario ya registrado', 'error')
                else:
                    # Inserta un nuevo registro en la tabla alumnos
                    cursor.execute("INSERT INTO alumnos (Nombres, ApellidoP, ApellidoM, Contraseña, NoControl) VALUES (%s, %s, %s, %s, %s)",(names, last_name1, last_name2, password, control_number))
                    conn.commit()
                    print(f"Alumno registrado: {control_number}")
                    return redirect(url_for('login_alumnos'))
            else:
                flash('Usuario no encontrado en la base de datos', 'error')
        except mysql.connector.Error as err:
            print(f"Error en la base de datos: {err}")
            flash(f"Error en la base de datos: {err}", 'error')
        finally:
            # Cierra la conexion a la base de datos
            cursor.close()
            conn.close()
            print("Conexión a la base de datos cerrada")
    return render_template('alumnos/register_alumnos.html')

# Ruta para mostrar la tabla de las jornadas academicas de los alumnos
@app.route('/alumnos_jornadas', methods=['GET', 'POST'])
def alumnos_jornadas():
    # Muestra el dashboard de los alumnos donde pueden subir archivos
    if 'user_id' in session and session.get('user_role') == 'alumno':
        control_number = session['user_id']
        if request.method == 'POST':
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                print("Conexión a la base de datos establecida")
                # Obtener todas las columnas de la tabla jornadas_academicas
                cursor.execute("SHOW COLUMNS FROM jornadas_academicas")
                all_columns = [row[0] for row in cursor.fetchall()]
                # Filtrar las columnas relevantes para los alumnos
                student_columns = [col for col in all_columns if col not in ['Estado', 'Conteo', 'Atendidos']]
                cursor.execute("SELECT * FROM jornadas_academicas WHERE NoControl = %s", (control_number,))
                alumno_data = cursor.fetchall()
                # Convertir los datos de la tabla en un diccionario para pasarlo a la plantilla
                alumnos_dict = [dict(zip(student_columns, row)) for row in alumno_data]
                print(f"Datos del alumno: {alumnos_dict}")
                return render_template('alumnos/alumnos_jornadas.html', alumnos=alumnos_dict, columns=student_columns)
            except mysql.connector.Error as err:
                print(f"Error en la base de datos: {err}")
                flash(f"Error en la base de datos: {err}", 'error')
                return redirect(url_for('iniciar_alumnos'))
            finally:
                cursor.close()
                conn.close()
                print("Conexión a la base de datos cerrada")
    return redirect(url_for('login_alumnos'))

# Ruta que se mostrara al ingresar en el login de alumnos
@app.route('/login_alumnos')
def login_alumnos():
    return render_template('alumnos/login_alumnos.html')

# Metodo para que los alumnos inicien sesion
@app.route('/iniciar_alumnos', methods=['POST', 'GET'])
def iniciar_alumnos():
    if request.method == 'POST':
        # Obtiene el numero de control y la contraseña del formulario
        control_number = request.form.get('control_number')
        password = request.form.get('password')
        print(f"Intento de inicio de sesión para número de control: {control_number}")
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            print("Conexión a la base de datos establecida")
            # Busca al usuario en la base de datos
            cursor.execute("SELECT NoControl, Nombres, ApellidoP, ApellidoM, Contraseña FROM alumnos WHERE NoControl = %s", (control_number,))
            user = cursor.fetchone()
            # Verifica si el usuario existe y la contraseña es correcta
            if user and bcrypt.checkpw(password.encode('utf-8'), user[4].encode('utf-8')):
                session['user_id'] = user[0]
                session['user_role'] = 'alumno'
                session['user_name'] = user[1] + ' ' + user[2] + ' ' + user[3]
                print(f"Ingreso exitoso para usuario: {session['user_name']}")
                return redirect(url_for('index'))
            else:
                flash('Número de control o contraseña no válido', 'error')
                print("Número de control o contraseña no válido")
        except mysql.connector.Error as err:
            print(f"Error en la base de datos: {err}")
            flash(f"Error en la base de datos: {err}", 'error')
    return render_template('alumnos/login_alumnos.html')

@app.route('/alumnos_tutorias', methods=['GET', 'POST'])
def alumnos_tutorias():
    if 'user_id' in session and session.get('user_role') == 'alumno':
        control_number = session['user_id']
        if request.method == 'POST':
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                print("Conexión a la base de datos establecida")
                cursor.execute("SHOW COLUMNS FROM tutorias")
                all_columns = [row[0] for row in cursor.fetchall()]
                student_columns = [col for col in all_columns if col not in ['Estado', 'Conteo', 'Atendidos']]
                cursor.execute("SELECT * FROM tutorias WHERE NoControl = %s", (control_number,))
                alumno_data = cursor.fetchall()
                alumnos_dict = [dict(zip(student_columns, row)) for row in alumno_data]
                print(f"Datos del alumno: {alumnos_dict}")
                return render_template('alumnos/alumnos_tutorias.html', alumnos=alumnos_dict, columns=student_columns)
            except mysql.connector.Error as err:
                print(f"Error en la base de datos: {err}")
                flash(f"Error en la base de datos: {err}", 'error')
                return redirect(url_for('iniciar_alumnos'))
            finally:
                cursor.close()
                conn.close()
                print("Conexión a la base de datos cerrada")
    return redirect(url_for('login_alumnos'))


# Ruta que se mostrará al ingresar en el login de profesores
@app.route('/login_profesores')
def login_profesores():
    return render_template('profesores/login_profesores.html')

# Metodo para que los profesores inicien sesion
@app.route('/iniciar_profesores', methods=['POST', 'GET'])
def iniciar_profesores():
    if request.method == 'POST':
        # Obtiene el numero de trabajador, nombre y clave del formulario
        worker_number = request.form.get('worker_number')
        names = request.form.get('names')
        key = request.form.get('key')
        print(f"Intento de inicio de sesión para número de trabajador: {worker_number}")
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            print("Conexión a la base de datos establecida")
            # Busca al usuario en la base de datos
            cursor.execute("SELECT * FROM profesores WHERE NoTrabajador = %s AND Nombres = %s", (worker_number, names,))
            user = cursor.fetchone()
            # Verifica si el usuario existe y la clave es correcta
            if user:
                if bcrypt.checkpw(key.encode('utf-8'), user[2].encode('utf-8')):
                    session['user_id'] = user[0]
                    session['user_role'] = 'profesor'
                    session['user_name'] = user[1]
                    print(f"Ingreso exitoso para profesor: {session['user_name']}")
                    return redirect(url_for('index'))
                else:
                    flash('Nombres o clave incorrectos', 'error')
                    print("Nombres o clave incorrectos")
            else:
                flash('Profesor no encontrado', 'error')
                print("Profesor no encontrado")
        except mysql.connector.Error as err:
            print(f"Error en la base de datos: {err}")
            flash(f"Error en la base de datos: {err}", 'error')
        finally:
            cursor.close()
            conn.close()
            print("Conexión a la base de datos cerrada")
    return render_template('profesores/login_profesores.html')

# Ruta para mostrar la tabla de las jornadas académicas de los alumnos
@app.route('/profesores_jornadas', methods=['POST', 'GET'])
def profesores_jornadas():
    # Verifica si el usuario está autenticado y es un profesor
    if 'user_id' in session and session.get('user_role') == 'profesor':
        if request.method == 'POST':
            # Manejo de la adicion de columnas
            if 'add_column' in request.form:
                column_name = request.form['column_name']
                if column_name:
                    print(f"Intentando agregar columna: {column_name}")
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        print("Conexión a la base de datos establecida")
                        # Obtiene las columnas actuales de la tabla
                        cursor.execute("SHOW COLUMNS FROM jornadas_academicas")
                        columns = [row[0] for row in cursor.fetchall() if row[0] not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Estado', 'Atendidos']]
                        print(f"Columnas existentes: {columns}")
                        # Agrega la nueva columna después de 'Conteo' si existe, o al final de la tabla
                        if 'Conteo' in columns:
                            conteo_column = columns.index('Conteo')
                            cursor.execute(f"ALTER TABLE jornadas_academicas ADD COLUMN `{column_name}` BOOLEAN DEFAULT 0 AFTER `{columns[conteo_column-1]}`")
                        else:
                            cursor.execute(f"ALTER TABLE jornadas_academicas ADD COLUMN `{column_name}` BOOLEAN DEFAULT 0")
                        conn.commit()
                        flash('Columna agregada con éxito', 'success')
                        print(f"Columna {column_name} agregada con éxito")
                    except mysql.connector.Error as err:
                        print(f"Error en la base de datos: {err}")
                        flash(f"Error en la base de datos: {err}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
                        print("Conexión a la base de datos cerrada")
            # Manejo de la eliminación de columnas
            elif 'remove_column' in request.form:
                column_name = request.form['column_name']
                if column_name:
                    print(f"Intentando eliminar columna: {column_name}")
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        print("Conexión a la base de datos establecida")
                        # Elimina la columna de la tabla
                        cursor.execute(f"ALTER TABLE jornadas_academicas DROP COLUMN `{column_name}`")
                        conn.commit()
                        flash('Columna eliminada con éxito', 'success')
                        print(f"Columna {column_name} eliminada con éxito")
                    except mysql.connector.Error as err:
                        print(f"Error en la base de datos: {err}")
                        flash(f"Error en la base de datos: {err}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
                        print("Conexión a la base de datos cerrada")
            elif 'search_student' in request.form:
                number_control = request.form['number_control']
                try:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    print("Conexión a la base de datos establecida")
                    # Obtiene las columnas actuales de la tabla
                    cursor.execute("SHOW COLUMNS FROM jornadas_academicas")
                    columns = [row[0] for row in cursor.fetchall() if row[0] not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Estado', 'Atendidos']]
                    print(f"Columnas existentes: {columns}")
                    # Ajusta la lista de columnas para incluir 'Conteo' en la posición correcta
                    if 'Conteo' in columns:
                        conteo_column = columns.index('Conteo')
                        columns = columns[:conteo_column]
                        columns.append('Conteo')
                    cursor.execute("SELECT * FROM jornadas_academicas WHERE NoControl = %s", (number_control,))
                    alumnos = cursor.fetchall()
                    # Prepara los datos de los alumnos para la plantilla
                    column_names = ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres'] + columns + ['Estado', 'Atendidos']
                    alumnos_dict = [dict(zip(column_names, row)) for row in alumnos]
                    # Calcula el conteo de valores no vacíos para cada alumno
                    for row in alumnos_dict:
                        count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado', 'Atendidos'] and row[key]==1)
                        row['Conteo'] = count_non_empty
                    return render_template('profesores/profesores_jornadas.html', alumnos=alumnos_dict, columns=column_names)
                except mysql.connector.Error as err:
                    print(f"Error en la base de datos: {err}")
                    flash(f"Error en la base de datos: {err}", 'error')
                finally:
                    cursor.close()
                    conn.close()
                    print("Conexión a la base de datos cerrada")
            elif 'search_cancel' in request.form:
                return redirect(url_for('profesores_jornadas'))
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            print("Conexión a la base de datos establecida")
            # Obtiene las columnas actuales de la tabla
            cursor.execute("SHOW COLUMNS FROM jornadas_academicas")
            columns = [row[0] for row in cursor.fetchall() if row[0] not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Estado', 'Atendidos']]
            print(f"Columnas existentes: {columns}")
            # Ajusta la lista de columnas para incluir 'Conteo' en la posición correcta
            if 'Conteo' in columns:
                conteo_column = columns.index('Conteo')
                columns = columns[:conteo_column]
                columns.append('Conteo')
            cursor.execute("SELECT * FROM jornadas_academicas")
            alumnos = cursor.fetchall()
            # Prepara los datos de los alumnos para la plantilla
            column_names = ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres'] + columns + ['Estado', 'Atendidos']
            alumnos_dict = [dict(zip(column_names, row)) for row in alumnos]
            # Calcula el conteo de valores no vacíos para cada alumno
            for row in alumnos_dict:
                count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado', 'Atendidos'] and row[key]==1)
                row['Conteo'] = count_non_empty
            return render_template('profesores/profesores_jornadas.html', alumnos=alumnos_dict, columns=column_names)
        except mysql.connector.Error as err:
            print(f"Error en la base de datos: {err}")
            flash(f"Error en la base de datos: {err}", 'error')
            return redirect(url_for('iniciar_profesores'))
        finally:
            cursor.close()
            conn.close()
            print("Conexión a la base de datos cerrada")
    return redirect(url_for('iniciar_profesores'))

# Ruta para editar un registro de alumno
@app.route('/edit_record_jornadas/<record_id>', methods=['GET', 'POST'])
def edit_record_jornadas(record_id):
    if 'user_id' in session and session.get('user_role') == 'profesor':
        if request.method == 'POST':
            # Manejo de guardar cambios
            if 'save_changes' in request.form:
                print(f"Iniciando el guardado de cambios para el registro {record_id}")
                try:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    print("Conexión a la base de datos establecida")
                    # Recorre todos los elementos del formulario
                    for column, value in request.form.items():
                        # Verifica que la columna no sea una de las excluidas
                        if column not in ['NoControl', 'save_changes', 'columns_to_clear']:
                            # Imprime el nombre de la columna y el valor que se va a actualizar
                            print(f"Actualizando columna {column} con valor {value}")
                            cursor.execute(f"UPDATE jornadas_academicas SET `{column}` = %s WHERE NoControl = %s", (value, record_id))
                    # Obtiene la lista de columnas que deben ser limpiadas (establecidas a 0)
                    columns_to_clear = request.form.getlist('columns_to_clear')
                    # Imprime las columnas que se van a limpiar
                    print(f"Columnas a limpiar: {columns_to_clear}")
                    # Recorre las columnas que deben ser limpiadas
                    for column_name in columns_to_clear:
                        # Establece el valor de la columna a 0 o 1 para el registro especificado
                        cursor.execute(f"UPDATE jornadas_academicas SET `{column_name}` = CASE WHEN `{column_name}` = 0 THEN 1 ELSE 0 END WHERE NoControl = %s", (record_id,))
                        print(f"Columna {column_name} limpiada")
                    conn.commit()
                    print("Cambios guardados con éxito")
                    flash('Cambios guardados con éxito', 'success')
                except mysql.connector.Error as err:
                    print(f"Error en la base de datos: {err}")
                    flash(f"Error en la base de datos: {err}", 'error')
                finally:
                    cursor.close()
                    conn.close()
                    print("Conexión a la base de datos cerrada")
                return redirect(url_for('profesores_jornadas'))
            # Manejo de eliminación de registros
            elif 'delete_record' in request.form:
                print(f"Iniciando eliminación del registro {record_id}")
                try:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    print("Conexión a la base de datos establecida")
                    
                    cursor.execute("DELETE FROM jornadas_academicas WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en jornadas_academicas para {record_id}")
                    cursor.execute("DELETE FROM alumnos WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en alumnos para {record_id}")
                    conn.commit()
                    flash('Registro eliminado con éxito', 'success')
                except mysql.connector.Error as err:
                    print(f"Error en la base de datos: {err}")
                    flash(f"Error en la base de datos: {err}", 'error')
                finally:
                    cursor.close()
                    conn.close()
                    print("Conexión a la base de datos cerrada")
                return redirect(url_for('profesores_jornadas'))
            # Manejo de la acción de volver al dashboard
            elif 'go_back' in request.form:
                print("Regresando al dashboard de profesores")
                return redirect(url_for('profesores_jornadas'))
        # Manejo de la solicitud GET para cargar el registro
        else:
            print(f"Cargando datos para el registro {record_id}")
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor(dictionary=True)
                print("Conexión a la base de datos establecida")
                cursor.execute("SELECT * FROM jornadas_academicas WHERE NoControl = %s", (record_id,))
                record = cursor.fetchone()
                if record:
                    print(f"Registro encontrado: {record}")
                    return render_template('action_pages/editar_alumno_jornadas.html', record=record)
                else:
                    print(f"Registro {record_id} no encontrado")
                    flash('Registro no encontrado', 'error')
                    return redirect(url_for('profesores_jornadas'))
            except mysql.connector.Error as err:
                print(f"Error en la base de datos: {err}")
                flash(f"Error en la base de datos: {err}", 'error')
                return redirect(url_for('profesores_jornadas'))
            finally:
                cursor.close()
                conn.close()
                print("Conexión a la base de datos cerrada")
    # Redirige al dashboard de profesores si el usuario no esta autenticado o no es profesor
    print("Redirigiendo al dashboard de profesores")
    return redirect(url_for('profesores_jornadas'))

@app.route('/profesores_tutorias', methods=['POST', 'GET'])
def profesores_tutorias():
    if 'user_id' in session and session.get('user_role') == 'profesor':
        if request.method == 'POST':
            # Manejo de la adición de columnas
            if 'add_column' in request.form:
                column_name = request.form['column_name']
                if column_name:
                    print(f"Intentando agregar columna: {column_name}")
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        print("Conexión a la base de datos establecida")
                        # Obtiene las columnas actuales de la tabla
                        cursor.execute("SHOW COLUMNS FROM tutorias")
                        columns = [row[0] for row in cursor.fetchall() if row[0] not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Estado']]
                        print(f"Columnas existentes: {columns}")
                        # Agrega la nueva columna después de 'Conteo' si existe, o al final de la tabla
                        if 'Conteo' in columns:
                            conteo_column = columns.index('Conteo')
                            cursor.execute(f"ALTER TABLE tutorias ADD COLUMN `{column_name}` VARCHAR(255) AFTER `{columns[conteo_column-1]}`")
                        else:
                            cursor.execute(f"ALTER TABLE tutorias ADD COLUMN `{column_name}` VARCHAR(255)")
                        conn.commit()
                        flash('Columna agregada con éxito', 'success')
                        print(f"Columna {column_name} agregada con éxito")
                    except mysql.connector.Error as err:
                        print(f"Error en la base de datos: {err}")
                        flash(f"Error en la base de datos: {err}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
                        print("Conexión a la base de datos cerrada")
            # Manejo de la eliminación de columnas
            elif 'remove_column' in request.form:
                column_name = request.form['column_name']
                if column_name:
                    print(f"Intentando eliminar columna: {column_name}")
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        print("Conexión a la base de datos establecida")
                        # Elimina la columna de la tabla
                        cursor.execute(f"ALTER TABLE tutorias DROP COLUMN `{column_name}`")
                        conn.commit()
                        flash('Columna eliminada con éxito', 'success')
                        print(f"Columna {column_name} eliminada con éxito")
                    except mysql.connector.Error as err:
                        print(f"Error en la base de datos: {err}")
                        flash(f"Error en la base de datos: {err}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
                        print("Conexión a la base de datos cerrada")
            elif 'search_student' in request.form:
                number_control = request.form['number_control']
                try:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    print("Conexión a la base de datos establecida")
                    # Obtiene las columnas actuales de la tabla
                    cursor.execute("SHOW COLUMNS FROM tutorias")
                    columns = [row[0] for row in cursor.fetchall() if row[0] not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Estado']]
                    print(f"Columnas existentes: {columns}")
                    # Ajusta la lista de columnas para incluir 'Conteo' en la posición correcta
                    if 'Conteo' in columns:
                        conteo_column = columns.index('Conteo')
                        columns = columns[:conteo_column]
                        columns.append('Conteo')
                    cursor.execute("SELECT * FROM tutorias WHERE NoControl = %s", (number_control,))
                    alumnos = cursor.fetchall()
                    # Prepara los datos de los alumnos para la plantilla
                    column_names = ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres'] + columns + ['Estado']
                    alumnos_dict = [dict(zip(column_names, row)) for row in alumnos]
                    # Calcula el conteo de valores no vacíos para cada alumno
                    for row in alumnos_dict:
                        count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado'] and row[key]==1)
                        row['Conteo'] = count_non_empty
                    return render_template('profesores/profesores_tutorias.html', alumnos=alumnos_dict, columns=column_names)
                except mysql.connector.Error as err:
                    print(f"Error en la base de datos: {err}")
                    flash(f"Error en la base de datos: {err}", 'error')
                finally:
                    cursor.close()
                    conn.close()
                    print("Conexión a la base de datos cerrada")
            elif 'search_cancel' in request.form:
                return redirect(url_for('profesores_tutorias'))
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            print("Conexión a la base de datos establecida")
            # Obtiene las columnas actuales de la tabla
            cursor.execute("SHOW COLUMNS FROM tutorias")
            columns = [row[0] for row in cursor.fetchall() if row[0] not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Estado']]
            print(f"Columnas existentes: {columns}")
            # Ajusta la lista de columnas para incluir 'Conteo' en la posición correcta
            if 'Conteo' in columns:
                conteo_column = columns.index('Conteo')
                columns = columns[:conteo_column]
                columns.append('Conteo')
            cursor.execute("SELECT * FROM tutorias")
            alumnos = cursor.fetchall()
            # Prepara los datos de los alumnos para la plantilla
            column_names = ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres'] + columns + ['Estado']
            alumnos_dict = [dict(zip(column_names, row)) for row in alumnos]
            # Calcula el conteo de valores no vacíos para cada alumno
            for row in alumnos_dict:
                count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado'] and row[key]==1)
                row['Conteo'] = count_non_empty
            return render_template('profesores/profesores_tutorias.html', alumnos=alumnos_dict, columns=column_names)
        except mysql.connector.Error as err:
            print(f"Error en la base de datos: {err}")
            flash(f"Error en la base de datos: {err}", 'error')
            return redirect(url_for('iniciar_profesores'))
        finally:
            cursor.close()
            conn.close()
            print("Conexión a la base de datos cerrada")
    return redirect(url_for('iniciar_profesores'))

# Ruta para editar un registro de alumno 
@app.route('/edit_record_tutorias/<record_id>', methods=['GET', 'POST'])
def edit_record_tutorias( record_id):
    if 'user_id' in session and session.get('user_role') == 'profesor':
        if request.method == 'POST':
            # Manejo de guardar cambios
            if 'save_changes' in request.form:
                print(f"Iniciando el guardado de cambios para el registro {record_id} en la tabla tutorias")
                try:
                    # Conecta a la base de datos
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    print("Conexión a la base de datos establecida")
                    # Recorre todos los elementos del formulario
                    for column, value in request.form.items():
                        # Verifica que la columna no sea una de las excluidas
                        if column not in ['NoControl', 'save_changes', 'columns_to_clear']:
                            # Imprime el nombre de la columna y el valor que se va a actualizar
                            print(f"Actualizando columna {column} con valor {value}")
                            cursor.execute(f"UPDATE tutorias SET `{column}` = %s WHERE NoControl = %s", (value, record_id))
                    # Obtiene la lista de columnas que deben ser limpiadas (establecidas a NULL)
                    columns_to_clear = request.form.getlist('columns_to_clear')
                    # Imprime las columnas que se van a limpiar
                    print(f"Columnas a limpiar: {columns_to_clear}")
                    # Recorre las columnas que deben ser limpiadas
                    for column_name in columns_to_clear:
                        # Establece el valor de la columna a NULL para el registro especificado
                        cursor.execute(f"UPDATE tutorias SET `{column_name}` = CASE WHEN `{column_name}` = 0 THEN 1 ELSE 0 END WHERE NoControl = %s", (record_id,))
                        print(f"Columna {column_name} limpiada")
                    conn.commit()
                    print("Cambios guardados con éxito")
                    flash('Cambios guardados con éxito', 'success')
                except mysql.connector.Error as err:
                    print(f"Error en la base de datos: {err}")
                    flash(f"Error en la base de datos: {err}", 'error')
                finally:
                    cursor.close()
                    conn.close()
                    print("Conexión a la base de datos cerrada")
                return redirect(url_for('profesores_tutorias'))
            # Manejo de eliminación de registros
            elif 'delete_record' in request.form:
                print(f"Iniciando eliminación del registro {record_id} en la tabla tutorias")
                try:
                    # Conecta a la base de datos
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    print("Conexión a la base de datos establecida")

                    cursor.execute(f"DELETE FROM tutorias WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en tutorias para {record_id}")
                    cursor.execute("DELETE FROM alumnos WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en alumnos para {record_id}")
                    conn.commit()
                    flash('Registro eliminado con éxito', 'success')
                except mysql.connector.Error as err:
                    print(f"Error en la base de datos: {err}")
                    flash(f"Error en la base de datos: {err}", 'error')
                finally:
                    cursor.close()
                    conn.close()
                    print("Conexión a la base de datos cerrada")
                return redirect(url_for('profesores_tutorias'))
            # Manejo de la acción de volver al dashboard
            elif 'go_back' in request.form:
                print("Regresando al dashboard de profesores")
                return redirect(url_for('profesores_tutorias'))
        # Manejo de la solicitud GET para cargar el registro
        else:
            print(f"Cargando datos para el registro {record_id} en la tabla tutorias")
            try:
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor(dictionary=True)
                print("Conexión a la base de datos establecida")
                cursor.execute(f"SELECT * FROM tutorias WHERE NoControl = %s", (record_id,))
                record = cursor.fetchone()
                if record:
                    print(f"Registro encontrado: {record}")
                    return render_template('action_pages/editar_alumno_tutorias.html', record=record)
                else:
                    print(f"Registro {record_id} no encontrado")
                    flash('Registro no encontrado', 'error')
                    return redirect(url_for('profesores_tutorias'))
            except mysql.connector.Error as err:
                print(f"Error en la base de datos: {err}")
                flash(f"Error en la base de datos: {err}", 'error')
                return redirect(url_for('profesores_tutorias'))
            finally:
                cursor.close()
                conn.close()
                print("Conexión a la base de datos cerrada")
    # Redirige al dashboard de alumnos si el usuario no esta autenticado o no es alumno
    print("Redirigiendo al dashboard de alumnos")
    return redirect(url_for('profesores_tutorias'))


# Metodo para manejar el cierre de sesion del usuario
@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    # Limpia toda la información de la sesión del usuario
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    print(f"Usuario con ID {user_id} ha cerrado sesión.")
    return redirect(url_for('index'))

# Configura el logger para registrar errores en un archivo
logging.basicConfig(filename='app_errors.log', level=logging.ERROR)

# Configura el logger para registrar los errores en un archivo con formato específico
logging.basicConfig(filename='app_errors.log',
                    level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Función para manejar errores 404 (página no encontrada)
@app.errorhandler(404)
def page_not_found(error):
    # Registra el error 404 en el archivo de logs con la ruta que causo el error
    logging.error(f"404 Error: {request.path} - {error}")
    return render_template('errores/404.html'), 404

# Función para manejar errores 500 (error interno del servidor)
@app.errorhandler(500)
def internal_server_error(error):
    # Registra el error 500 en el archivo de logs
    logging.error(f"500 Error: {error}")
    return render_template('errores/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)