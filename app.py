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

# Verifica si la carpeta de subidas existe, si no, la crea
if not os.path.exists(app.config ['UPLOAD_FOLDER']):
    os.makedirs(app.config ['UPLOAD_FOLDER'])

def get_unique_filename(filename):
    # Genera un nombre unico para el archivo si ya existe uno con el mismo nombre
    base, extension = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    # Verifica si el archivo ya existe, y si es asi, genera un nuevo nombre unico
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], new_filename)):
        new_filename = f"{base}_{counter}{extension}"
        counter += 1
    return new_filename

def allowed_file(filename):
    # Verifica si el archivo tiene una extensión permitida
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.template_filter('basename')
def basename_filter(path):
    # Filtro de plantilla para obtener el nombre base del archivo desde una ruta
    return os.path.basename(path)

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

# Ruta para servir archivos desde la carpeta de subida
@app.route('/uploads/<user_id>/<filename>')
def uploaded_file(user_id, filename):
    # Sirve archivos desde la carpeta de subida para profesores
    if 'user_role' in session and session.get('user_role') == 'profesor':
        uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id)
        file_path = os.path.join(uploads_dir, filename)
        if os.path.isfile(file_path):
            print(f"Archivo solicitado: {file_path}")
            return send_from_directory(uploads_dir, filename)
        else:
            print(f"Archivo no encontrado: {file_path}")
            abort(404)
    else:
        print(f"Acceso denegado para el usuario: {session.get('user_id')}")
        abort(403)

# Ruta para mostrar la tabla de las jornadas academicas de los alumnos
@app.route('/alumnos_jornadas', methods=['GET', 'POST'])
def alumnos_jornadas():
    # Muestra el dashboard de los alumnos donde pueden subir archivos
    if 'user_id' in session and session.get('user_role') == 'alumno':
        control_number = session['user_id']
        if request.method == 'POST':
            # Recorre cada archivo y su nombre de columna asociado
            files = request.files.getlist('file')  # Obtiene la lista de archivos subidos en el formulario
            column_names = request.form.getlist('column_name')  # Obtiene la lista de nombres de columnas asociadas a los archivos
            # Define el tamaño máximo permitido en bytes (100 KB)
            max_file_size = 100 * 1024  # 100 KB en bytes
            for file, column_name in zip(files, column_names):
                if file and column_name:
                    # Verifica el tamaño del archivo
                    if len(file.read()) > max_file_size:
                        flash(f"El archivo '{file.filename}' supera los 100 KB. Por favor, sube un archivo más pequeño.", 'error')
                        return redirect(url_for('alumnos_jornadas'))
                    # Regresar el cursor al inicio después de leer el archivo para verificar el tamaño
                    file.seek(0)
                    # Resto del código para guardar el archivo
                    upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(control_number))
                    # Si la carpeta no existe, la crea
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                        print(f"Creada carpeta para el usuario {control_number}: {upload_folder}")
                    # Obtiene un nombre seguro para el archivo
                    filename = secure_filename(file.filename)
                    # Construye la ruta completa donde se guardara el archivo
                    save_path = os.path.join(upload_folder, filename)
                    print(f"Ruta para guardar el archivo: {save_path}")
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        print("Conexión a la base de datos establecida")
                        # Verifica si ya existe un archivo para esa columna en la base de datos
                        cursor.execute("SELECT ID, Ruta_archivo FROM rutas_pdf_jornadas WHERE NoControl = %s AND Columna_ref = %s", (control_number, column_name))
                        existing_file = cursor.fetchone()
                        if existing_file:
                            existing_id, existing_path = existing_file
                            flash(f"El archivo ({filename}) asociado con la columna '{column_name}' ya existe. Se reemplazará el archivo anterior.", 'info')
                            print(f"Reemplazando archivo existente en {existing_path}")
                            # Eliminar el archivo físico existente
                            if os.path.exists(existing_path):
                                os.remove(existing_path)
                            # Elimina el registro existente en la base de datos
                            cursor.execute("DELETE FROM rutas_pdf_jornadas WHERE ID = %s", (existing_id,))
                        # Guardar el nuevo archivo
                        file.save(save_path)
                        print(f"Archivo guardado en {save_path}")
                        # Insertar o actualizar la ruta del archivo en la base de datos
                        cursor.execute("INSERT INTO rutas_pdf_jornadas (NoControl, Nombre_archivo, Ruta_archivo, Columna_ref) VALUES (%s, %s, %s, %s)", (control_number, filename, save_path, column_name))
                        # Actualizar la tabla jornadas_academicas
                        cursor.execute(f"UPDATE jornadas_academicas SET `{column_name}` = %s WHERE NoControl = %s", (filename, control_number))
                        # Reordenar los IDs en rutas_pdf_jornadas para que sean consecutivos
                        cursor.execute("SET @count = 0;")
                        cursor.execute("UPDATE rutas_pdf_jornadas SET ID = @count:= @count + 1;")
                        cursor.execute("ALTER TABLE rutas_pdf_jornadas AUTO_INCREMENT = 1;")
                        print("IDs en rutas_pdf_jornadas reordenados")
                        conn.commit()
                        print("Cambios guardados en la base de datos")
                        if existing_file:
                            flash(f"Archivo '{filename}' reemplazado con éxito.", 'success')
                        else:
                            flash(f"Archivo '{filename}' subido y guardado con éxito", 'success')
                    except mysql.connector.Error as err:
                        print(f"Error en la base de datos: {err}")
                        flash(f"Error en la base de datos: {err}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
                        print("Conexión a la base de datos cerrada")
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
            files = request.files.getlist('file')
            column_names = request.form.getlist('column_name')
            max_file_size = 100 * 1024  # 100 KB en bytes
            for file, column_name in zip(files, column_names):
                if file and column_name:
                    if len(file.read()) > max_file_size:
                        flash(f"El archivo '{file.filename}' supera los 100 KB. Por favor, sube un archivo más pequeño.", 'error')
                        return redirect(url_for('alumnos_tutorias'))
                    file.seek(0)
                    tipo_carpeta = 'tutorias'
                    upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(control_number), tipo_carpeta)
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                        print(f"Creada carpeta para el usuario {control_number}: {upload_folder}")
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(upload_folder, filename)
                    print(f"Ruta para guardar el archivo: {save_path}")
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        print("Conexión a la base de datos establecida")
                        cursor.execute("SELECT ID, Ruta_archivo FROM rutas_pdf_tutorias WHERE NoControl = %s AND Columna_ref = %s", (control_number, column_name))
                        existing_file = cursor.fetchone()
                        if existing_file:
                            existing_id, existing_path = existing_file
                            flash(f"El archivo ({filename}) asociado con la columna '{column_name}' ya existe. Se reemplazará el archivo anterior.", 'info')
                            print(f"Reemplazando archivo existente en {existing_path}")
                            if os.path.exists(existing_path):
                                os.remove(existing_path)
                            cursor.execute("DELETE FROM rutas_pdf_tutorias WHERE ID = %s", (existing_id,))
                        file.save(save_path)
                        print(f"Archivo guardado en {save_path}")
                        cursor.execute("INSERT INTO rutas_pdf_tutorias (NoControl, Nombre_archivo, Ruta_archivo, Columna_ref) VALUES (%s, %s, %s, %s)", (control_number, filename, save_path, column_name))
                        cursor.execute(f"UPDATE tutorias SET `{column_name}` = %s WHERE NoControl = %s", (filename, control_number))
                        cursor.execute("SET @count = 0;")
                        cursor.execute("UPDATE rutas_pdf_tutorias SET ID = @count:= @count + 1;")
                        cursor.execute("ALTER TABLE rutas_pdf_tutorias AUTO_INCREMENT = 1;")
                        print("IDs en rutas_pdf_tutorias reordenados")
                        conn.commit()
                        print("Cambios guardados en la base de datos")
                        if existing_file:
                            flash(f"Archivo '{filename}' reemplazado con éxito.", 'success')
                        else:
                            flash(f"Archivo '{filename}' subido y guardado con éxito", 'success')
                    except mysql.connector.Error as err:
                        print(f"Error en la base de datos: {err}")
                        flash(f"Error en la base de datos: {err}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
                        print("Conexión a la base de datos cerrada")
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
                            cursor.execute(f"ALTER TABLE jornadas_academicas ADD COLUMN `{column_name}` VARCHAR(255) AFTER `{columns[conteo_column-1]}`")
                        else:
                            cursor.execute(f"ALTER TABLE jornadas_academicas ADD COLUMN `{column_name}` VARCHAR(255)")
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
                        # Obtiene los archivos asociados con la columna a eliminar
                        cursor.execute(f"SELECT NoControl, `{column_name}` FROM jornadas_academicas")
                        file_paths = cursor.fetchall()
                        print(f"Rutas de archivos encontrados: {file_paths}")
                        # Recorre los resultados de la consulta para eliminar los archivos
                        for no_control, file_name in file_paths:
                            if file_name: # Verifica que file_name no sea None o una cadena vacía
                                # Construye la ruta completa usando el número de control
                                file_path = os.path.join('static', 'uploads', str(no_control), file_name)
                                file_path = os.path.abspath(file_path) # Convierte a una ruta absoluta
                                print(f"Verificando la existencia del archivo: {file_path}")
                                if os.path.exists(file_path):
                                    print(f"Eliminando archivo: {file_path}")
                                    os.remove(file_path)
                                else:
                                    print(f"Archivo no encontrado: {file_path}")
                            else:
                                print(f"Archivo no válido en la base de datos: NoControl {no_control}, Archivo {file_name}")
                        # Eliminar registros de rutas_pdf_jornadas, jornadas_academicas y alumnos
                        cursor.execute("DELETE FROM rutas_pdf_jornadas WHERE Columna_ref = %s", (column_name,))
                        print(f"Registros eliminados en rutas_pdf_jornadas para {column_name}")
                        cursor.execute("SET @count = 0;")
                        cursor.execute("UPDATE rutas_pdf_jornadas SET ID = @count:= @count + 1;")
                        cursor.execute("ALTER TABLE rutas_pdf_jornadas AUTO_INCREMENT = 1;")
                        print("IDs en rutas_pdf_jornadas reordenados")
                        # Elimina la columna de la tabla
                        cursor.execute(f"ALTER TABLE jornadas_academicas DROP COLUMN `{column_name}`")
                        conn.commit()
                        flash('Columna eliminada con éxito', 'success')
                        print(f"Columna {column_name} eliminada con éxito")
                    except mysql.connector.Error as err:
                        print(f"Error en la base de datos: {err}")
                        flash(f"Error en la base de datos: {err}", 'error')
                    except Exception as e:
                        flash(f"Error al eliminar archivos: {e}", 'error')
                        print(f"Error al eliminar archivos: {e}")
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
                    # Obtiene los archivos asociados a los alumnos
                    cursor.execute("SELECT * FROM rutas_pdf_jornadas WHERE NoControl = %s", (number_control,))
                    archivos = cursor.fetchall()
                    # Crea un diccionario para almacenar los archivos por numero de control
                    archivos_dict = {}
                    # Recorre los resultados de la consulta
                    for archivo in archivos:
                        no_control = archivo[0] # Obtiene el número de control del alumno
                        if no_control not in archivos_dict:
                            # Si el numero de control no esta en el diccionario, inicializa una lista vacía
                            archivos_dict[no_control] = []
                        # Agrega la informacion del archivo (nombre y ruta) a la lista del numero de control correspondiente
                        archivos_dict[no_control].append({'nombre': archivo[1], 'ruta': os.path.basename(archivo[2])})
                    # Calcula el conteo de valores no vacíos para cada alumno
                    for row in alumnos_dict:
                        count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado', 'Atendidos'] and row[key] not in [None, ''])
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
            # Obtiene los archivos asociados a los alumnos
            cursor.execute("SELECT * FROM rutas_pdf_jornadas")
            archivos = cursor.fetchall()
            # Crea un diccionario para almacenar los archivos por numero de control
            archivos_dict = {}
            # Recorre los resultados de la consulta
            for archivo in archivos:
                no_control = archivo[0] # Obtiene el número de control del alumno
                if no_control not in archivos_dict:
                    # Si el numero de control no esta en el diccionario, inicializa una lista vacía
                    archivos_dict[no_control] = []
                # Agrega la informacion del archivo (nombre y ruta) a la lista del numero de control correspondiente
                archivos_dict[no_control].append({'nombre': archivo[1], 'ruta': os.path.basename(archivo[2])})
            # Calcula el conteo de valores no vacíos para cada alumno
            for row in alumnos_dict:
                count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado', 'Atendidos'] and row[key] not in [None, ''])
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
                    # Obtiene la lista de columnas que deben ser limpiadas (establecidas a NULL)
                    columns_to_clear = request.form.getlist('columns_to_clear')
                    # Imprime las columnas que se van a limpiar
                    print(f"Columnas a limpiar: {columns_to_clear}")
                    # Recorre las columnas que deben ser limpiadas
                    for column_name in columns_to_clear:
                        # Establece el valor de la columna a NULL para el registro especificado
                        cursor.execute(f"UPDATE jornadas_academicas SET `{column_name}` = NULL WHERE NoControl = %s", (record_id,))
                        print(f"Columna {column_name} limpiada")
                        # Obtener las rutas de archivo asociadas al 'record_id' y 'column_name'
                        cursor.execute("SELECT ruta_archivo FROM rutas_pdf_jornadas WHERE NoControl = %s AND Columna_ref = %s", (record_id, column_name))
                        file_paths = cursor.fetchall()
                        # Verificación adicional para asegurarse de que se encontraron rutas de archivos
                        if not file_paths:
                            print(f"No se encontraron rutas de archivos para NoControl={record_id} y Columna_ref={column_name}")
                        else:
                            print(f"Rutas de archivos encontradas para {column_name}: {file_paths}")
                        # Recorre cada ruta de archivo obtenida
                        for file_path in file_paths:
                            file_path = file_path[0]
                            # Verifica si el archivo existe en el sistema
                            if os.path.exists(file_path):
                                print(f"Eliminando archivo: {file_path}")
                                os.remove(file_path)
                            else:
                                print(f"Archivo no encontrado: {file_path}")
                            # Elimina el registro correspondiente en la tabla 'rutas_pdf_jornadas'
                            cursor.execute("DELETE FROM rutas_pdf_jornadas WHERE NoControl = %s AND Columna_ref = %s", (record_id, column_name))
                            print(f"Registro eliminado en rutas_pdf_jornadas para {column_name}")
                        cursor.execute("SET @count = 0;")
                        cursor.execute("UPDATE rutas_pdf_jornadas SET ID = @count:= @count + 1;")
                        cursor.execute("ALTER TABLE rutas_pdf_jornadas AUTO_INCREMENT = 1;")
                        print("IDs en rutas_pdf_jornadas reordenados")
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
                    # Eliminar archivos asociados al registro
                    cursor.execute("SELECT ruta_archivo FROM rutas_pdf_jornadas WHERE NoControl = %s", (record_id,))
                    file_paths = cursor.fetchall()
                    print(f"Rutas de archivos encontradas: {file_paths}")
                    # Recorre cada ruta de archivo obtenida
                    for file_path in file_paths:
                        file_path = file_path[0]
                        # Verifica si el archivo existe en el sistema
                        if os.path.exists(file_path):
                            print(f"Eliminando archivo: {file_path}")
                            os.remove(file_path)
                        else:
                            print(f"Archivo no encontrado: {file_path}")
                    # Eliminar registros de rutas_pdf_jornadas, jornadas_academicas y alumnos
                    cursor.execute("DELETE FROM rutas_pdf_jornadas WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en rutas_pdf_jornadas para {record_id}")
                    cursor.execute("DELETE FROM jornadas_academicas WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en jornadas_academicas para {record_id}")
                    cursor.execute("DELETE FROM alumnos WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en alumnos para {record_id}")
                    conn.commit()
                    cursor.execute("SET @count = 0;")
                    cursor.execute("UPDATE rutas_pdf_jornadas SET ID = @count:= @count + 1;")
                    cursor.execute("ALTER TABLE rutas_pdf_jornadas AUTO_INCREMENT = 1;")
                    print("IDs en rutas_pdf_jornadas reordenados")
                    flash('Registro y archivos eliminados con éxito', 'success')
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
                        # Obtiene los archivos asociados con la columna a eliminar
                        cursor.execute(f"SELECT NoControl, `{column_name}` FROM tutorias")
                        file_paths = cursor.fetchall()
                        print(f"Rutas de archivos encontrados: {file_paths}")
                        # Recorre los resultados de la consulta para eliminar los archivos
                        for no_control, file_name in file_paths:
                            if file_name: # Verifica que file_name no sea None o una cadena vacía
                                # Construye la ruta completa usando el número de control
                                file_path = os.path.join('static', 'uploads', str(no_control), file_name)
                                file_path = os.path.abspath(file_path) # Convierte a una ruta absoluta
                                print(f"Verificando la existencia del archivo: {file_path}")
                                if os.path.exists(file_path):
                                    print(f"Eliminando archivo: {file_path}")
                                    os.remove(file_path)
                                else:
                                    print(f"Archivo no encontrado: {file_path}")
                            else:
                                print(f"Archivo no válido en la base de datos: NoControl {no_control}, Archivo {file_name}")
                        # Eliminar registros de rutas_pdf_tutorias y tutorias
                        cursor.execute("DELETE FROM rutas_pdf_tutorias WHERE Columna_ref = %s", (column_name,))
                        print(f"Registros eliminados en rutas_pdf_tutorias para {column_name}")
                        # Reordenar los IDs en rutas_pdf_tutorias para que sean consecutivos
                        cursor.execute("SET @count = 0;")
                        cursor.execute("UPDATE rutas_pdf_tutorias SET ID = @count:= @count + 1;")
                        cursor.execute("ALTER TABLE rutas_pdf_tutorias AUTO_INCREMENT = 1;")
                        print("IDs en rutas_pdf_tutorias reordenados")
                        # Elimina la columna de la tabla
                        cursor.execute(f"ALTER TABLE tutorias DROP COLUMN `{column_name}`")
                        conn.commit()
                        flash('Columna eliminada con éxito', 'success')
                        print(f"Columna {column_name} eliminada con éxito")
                    except mysql.connector.Error as err:
                        print(f"Error en la base de datos: {err}")
                        flash(f"Error en la base de datos: {err}", 'error')
                    except Exception as e:
                        flash(f"Error al eliminar archivos: {e}", 'error')
                        print(f"Error al eliminar archivos: {e}")
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
                    # Obtiene los archivos asociados a los alumnos
                    cursor.execute("SELECT * FROM rutas_pdf_tutorias WHERE NoControl = %s", (number_control,))
                    archivos = cursor.fetchall()
                    # Crea un diccionario para almacenar los archivos por número de control
                    archivos_dict = {}
                    # Recorre los resultados de la consulta
                    for archivo in archivos:
                        no_control = archivo[0] # Obtiene el número de control del alumno
                        if no_control not in archivos_dict:
                            # Si el número de control no está en el diccionario, inicializa una lista vacía
                            archivos_dict[no_control] = []
                        # Agrega la información del archivo (nombre y ruta) a la lista del número de control correspondiente
                        archivos_dict[no_control].append({'nombre': archivo[1], 'ruta': os.path.basename(archivo[2])})
                    # Calcula el conteo de valores no vacíos para cada alumno
                    for row in alumnos_dict:
                        count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado'] and row[key] not in [None, ''])
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
            # Obtiene los archivos asociados a los alumnos
            cursor.execute("SELECT * FROM rutas_pdf_tutorias")
            archivos = cursor.fetchall()
            # Crea un diccionario para almacenar los archivos por número de control
            archivos_dict = {}
            # Recorre los resultados de la consulta
            for archivo in archivos:
                no_control = archivo[0] # Obtiene el número de control del alumno
                if no_control not in archivos_dict:
                    # Si el número de control no está en el diccionario, inicializa una lista vacía
                    archivos_dict[no_control] = []
                # Agrega la información del archivo (nombre y ruta) a la lista del número de control correspondiente
                archivos_dict[no_control].append({'nombre': archivo[1], 'ruta': os.path.basename(archivo[2])})
            # Calcula el conteo de valores no vacíos para cada alumno
            for row in alumnos_dict:
                count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado'] and row[key] not in [None, ''])
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
                        cursor.execute(f"UPDATE tutorias SET `{column_name}` = NULL WHERE NoControl = %s", (record_id,))
                        print(f"Columna {column_name} limpiada")
                        # Obtener las rutas de archivo asociadas al 'record_id' y 'column_name'
                        cursor.execute("SELECT ruta_archivo FROM rutas_pdf_tutorias WHERE NoControl = %s AND Columna_ref = %s", (record_id, column_name))
                        file_paths = cursor.fetchall()
                        # Verificación adicional para asegurarse de que se encontraron rutas de archivos
                        if not file_paths:
                            print(f"No se encontraron rutas de archivos para NoControl={record_id} y Columna_ref={column_name}")
                        else:
                            print(f"Rutas de archivos encontradas para {column_name}: {file_paths}")
                        # Recorre cada ruta de archivo obtenida
                        for file_path in file_paths:
                            file_path = file_path[0]
                            # Verifica si el archivo existe en el sistema
                            if os.path.exists(file_path):
                                print(f"Eliminando archivo: {file_path}")
                                os.remove(file_path)
                            else:
                                print(f"Archivo no encontrado: {file_path}")
                            # Elimina el registro correspondiente en la tabla 'rutas_pdf_tutorias'
                            cursor.execute("DELETE FROM rutas_pdf_tutorias WHERE NoControl = %s AND Columna_ref = %s", (record_id, column_name))
                            print(f"Registro eliminado en rutas_pdf_tutorias para {column_name}")
                        cursor.execute("SET @count = 0;")
                        cursor.execute("UPDATE rutas_pdf_tutorias SET ID = @count:= @count + 1;")
                        cursor.execute("ALTER TABLE rutas_pdf_tutorias AUTO_INCREMENT = 1;")
                        print("IDs en rutas_pdf_tutorias reordenados")
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
                    # Eliminar archivos asociados al registro
                    cursor.execute("SELECT ruta_archivo FROM rutas_pdf_tutorias WHERE NoControl = %s", (record_id,))
                    file_paths = cursor.fetchall()
                    print(f"Rutas de archivos encontradas: {file_paths}")
                    # Recorre cada ruta de archivo obtenida
                    for file_path in file_paths:
                        file_path = file_path[0]
                        # Verifica si el archivo existe en el sistema
                        if os.path.exists(file_path):
                            print(f"Eliminando archivo: {file_path}")
                            os.remove(file_path)
                        else:
                            print(f"Archivo no encontrado: {file_path}")
                    # Eliminar registros de rutas_pdf_tutorias, tutorias y alumnos
                    cursor.execute("DELETE FROM rutas_pdf_tutorias WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en rutas_pdf_tutorias para {record_id}")
                    cursor.execute(f"DELETE FROM tutorias WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en tutorias para {record_id}")
                    cursor.execute("DELETE FROM alumnos WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en alumnos para {record_id}")
                    conn.commit()
                    cursor.execute("SET @count = 0;")
                    cursor.execute("UPDATE rutas_pdf_tutorias SET ID = @count:= @count + 1;")
                    cursor.execute("ALTER TABLE rutas_pdf_tutorias AUTO_INCREMENT = 1;")
                    print("IDs en rutas_pdf_tutorias reordenados")
                    flash('Registro y archivos eliminados con éxito', 'success')
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