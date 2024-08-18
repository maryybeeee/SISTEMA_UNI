from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, abort
from config import db_config, secret_key, UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from werkzeug.utils import secure_filename
from datetime import timedelta
import bcrypt
import mysql.connector
import logging
import os

app = Flask(__name__)
app.secret_key = secret_key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_unique_filename(filename):
    """Genera un nombre único para el archivo si ya existe uno con el mismo nombre."""
    base, extension = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], new_filename)):
        new_filename = f"{base}_{counter}{extension}"
        counter += 1
    return new_filename

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path)

# Ruta que se mostrará al ingresar en la página
@app.route('/')
def index():
    return render_template('index.html')

# Ruta que se mostrará al ingresar en el registro de alumnos
@app.route('/register_alumnos')
def register_alumnos():
    return render_template('register_alumnos.html')

# Método para registrar a un alumno y guardarlo en la tabla alumno
@app.route('/registro_alumnos', methods=['POST', 'GET'])
def registro_alumnos():
    if request.method == 'POST':
        names = request.form['names']
        last_name1 = request.form['last_name1']
        last_name2 = request.form['last_name2']
        control_number = request.form['control_number']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jornadas_academicas WHERE NoControl = %s", (control_number,))
            jornada_academica = cursor.fetchone()
            if jornada_academica:
                cursor.execute("SELECT * FROM alumnos WHERE NoControl = %s", (control_number,))
                user = cursor.fetchone()
                if user:
                    flash('Número de control ya registrado', 'error')
                else:
                    cursor.execute("INSERT INTO alumnos (Nombres, ApellidoP, ApellidoM, Contraseña, NoControl) VALUES (%s, %s, %s, %s, %s)", (names, last_name1, last_name2, password, control_number,))
                    conn.commit()
                    return redirect(url_for('login_alumnos'))
            else:
                flash('Número de control no encontrado en jornadas académicas', 'error')
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
        finally:
            cursor.close()
            conn.close()
    return render_template('register_alumnos.html')

# Ruta para servir archivos desde la carpeta de subida
@app.route('/uploads/<user_id>/<filename>')
def uploaded_file(user_id, filename):
    if 'user_role' in session and session.get('user_role') == 'profesor':
        uploads_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id)
        file_path = os.path.join(uploads_dir, filename)
        if os.path.isfile(file_path):
            return send_from_directory(uploads_dir, filename)
        else:
            abort(404)
    else:
        abort(403)

# Ruta para mostrar la tabla de las jornadas académicas de los alumnos para que puedan subir sus archivos
@app.route('/alumnos_dashboard', methods=['GET', 'POST'])
def alumnos_dashboard():
    if 'user_id' in session and session.get('user_role') == 'alumno':
        control_number = session['user_id']
        if request.method == 'POST':
            files = request.files.getlist('file')
            column_names = request.form.getlist('column_name')
            for file, column_name in zip(files, column_names):
                if file and column_name:
                    upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(control_number))
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(upload_folder, filename)
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()

                        # Verificar si ya existe un archivo en esa columna
                        cursor.execute("SELECT id, ruta_archivo FROM rutas_pdf WHERE no_control = %s AND tabla_referencia = %s", (control_number, column_name))
                        existing_file = cursor.fetchone()

                        if existing_file:
                            existing_id, existing_path = existing_file
                            flash(f"El archivo ({filename}) asociado con la columna '{column_name}' ya existe. Se reemplazará el archivo anterior.", 'info')
                            # Eliminar el archivo físico existente
                            if os.path.exists(existing_path):
                                os.remove(existing_path)
                            # Eliminar el registro existente en la base de datos
                            cursor.execute("DELETE FROM rutas_pdf WHERE id = %s", (existing_id,))

                        # Guardar el nuevo archivo
                        file.save(save_path)

                        # Insertar o actualizar la ruta del archivo en la base de datos
                        cursor.execute("INSERT INTO rutas_pdf (no_control, nombre_archivo, ruta_archivo, tabla_referencia) VALUES (%s, %s, %s, %s)", (control_number, filename, save_path, column_name))

                        # Actualizar la tabla jornadas_academicas
                        cursor.execute(f"UPDATE jornadas_academicas SET `{column_name}` = %s WHERE NoControl = %s", (filename, control_number))
                        
                        # Reordenar los IDs en rutas_pdf para que sean consecutivos
                        cursor.execute("SET @count = 0;")
                        cursor.execute("UPDATE rutas_pdf SET id = @count:= @count + 1;")
                        cursor.execute("ALTER TABLE rutas_pdf AUTO_INCREMENT = 1;")
                        print("IDs en rutas_pdf reordenados")

                        conn.commit()
                        if existing_file:
                            flash(f"Archivo '{filename}' reemplazado con éxito.", 'success')
                        else:
                            flash(f"Archivo '{filename}' subido y guardado con éxito", 'success')

                    except mysql.connector.Error as err:
                        flash(f"Error en la base de datos: {err}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SHOW COLUMNS FROM jornadas_academicas")
            all_columns = [row[0] for row in cursor.fetchall()]
            student_columns = [col for col in all_columns if col not in ['Estado', 'Conteo', 'Atendidos']]
            cursor.execute("SELECT * FROM jornadas_academicas WHERE NoControl = %s", (control_number,))
            alumno_data = cursor.fetchall()
            alumnos_dict = [dict(zip(student_columns, row)) for row in alumno_data]
            return render_template('alumnos_dashboard.html', alumnos=alumnos_dict, columns=student_columns)
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
            return redirect(url_for('iniciar_alumnos'))
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login_alumnos'))

# Ruta que se mostrará al ingresar en el login de alumnos
@app.route('/login_alumnos')
def login_alumnos():
    return render_template('login_alumnos.html')

# Método para que los alumnos inicien sesión
@app.route('/iniciar_alumnos', methods=['POST', 'GET'])
def iniciar_alumnos():
    if request.method == 'POST':
        control_number = request.form.get('control_number')
        password = request.form.get('password')
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT NoControl, Nombres, ApellidoP, ApellidoM, Contraseña FROM alumnos WHERE NoControl = %s", (control_number,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode('utf-8'), user[4].encode('utf-8')):
                session['user_id'] = user[0]
                session['user_role'] = 'alumno'
                session['user_name'] = user[1] + ' ' + user[2] + ' ' + user[3]
                return redirect(url_for('alumnos_dashboard'))
            else:
                flash('Número de control o contraseña no valido', 'error')
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
        finally:
            cursor.close()
            conn.close()
    return render_template('login_alumnos.html')

# Ruta que se mostrará al ingresar en el login de profesores
@app.route('/login_profesores')
def login_profesores():
    return render_template('login_profesores.html')

# Método para que los profesores inicien sesión
@app.route('/iniciar_profesores', methods=['POST', 'GET'])
def iniciar_profesores():
    if request.method == 'POST':
        worker_number = request.form.get('worker_number')
        names = request.form.get('names')
        key = request.form.get('key')
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profesores WHERE NoTrabajador = %s AND Nombres = %s", (worker_number, names,))
            user = cursor.fetchone()
            if user:
                if bcrypt.checkpw(key.encode('utf-8'), user[2].encode('utf-8')):
                    session['user_id'] = user[0]
                    session['user_role'] = 'profesor'
                    session['user_name'] = user[1]
                    return redirect(url_for('profesores_dashboard'))
                else:
                    flash('Nombres o clave incorrectos', 'error')
            else:
                flash('Profesor no encontrado', 'error')
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
        finally:
            cursor.close()
            conn.close()
    return render_template('login_profesores.html')

# Ruta para mostrar la tabla de las jornadas académicas de los alumnos
@app.route('/profesores_dashboard', methods=['POST', 'GET'])
def profesores_dashboard():
    if 'user_id' in session and session.get('user_role') == 'profesor':
        if request.method == 'POST':
            if 'add_column' in request.form:
                column_name = request.form['column_name']
                if column_name:
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        cursor.execute("SHOW COLUMNS FROM jornadas_academicas")
                        columns = [row[0] for row in cursor.fetchall() if row[0] not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Estado', 'Atendidos']]
                        if 'Conteo' in columns:
                            conteo_column = columns.index('Conteo')
                            cursor.execute(f"ALTER TABLE jornadas_academicas ADD COLUMN `{column_name}` VARCHAR(255) AFTER `{columns[conteo_column-1]}`")
                        else:
                            cursor.execute(f"ALTER TABLE jornadas_academicas ADD COLUMN `{column_name}` VARCHAR(255)")
                        conn.commit()
                        flash('Columna agregada con éxito', 'success')
                    except mysql.connector.Error as err:
                        flash(f"Error en la base de datos: {err}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
            elif 'remove_column' in request.form:
                column_name = request.form['column_name']
                if column_name:
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT `{column_name}` FROM jornadas_academicas")
                        file_paths = cursor.fetchall()
                        for (file_path,) in file_paths:
                            if file_path:
                                full_path = os.path.join('static/uploads/', file_path)
                                if os.path.exists(full_path):
                                    os.remove(full_path)
                        cursor.execute(f"ALTER TABLE jornadas_academicas DROP COLUMN `{column_name}`")
                        conn.commit()
                        flash('Columna eliminada con éxito', 'success')
                    except mysql.connector.Error as err:
                        flash(f"Error en la base de datos: {err}", 'error')
                    except Exception as e:
                        flash(f"Error al eliminar archivos: {e}", 'error')
                    finally:
                        cursor.close()
                        conn.close()
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SHOW COLUMNS FROM jornadas_academicas")
            columns = [row[0] for row in cursor.fetchall() if row[0] not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Estado', 'Atendidos']]
            if 'Conteo' in columns:
                conteo_column = columns.index('Conteo')
                columns = columns[:conteo_column]
                columns.append('Conteo')
            cursor.execute("SELECT * FROM jornadas_academicas")
            alumnos = cursor.fetchall()
            column_names = ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres'] + columns + ['Estado', 'Atendidos']
            alumnos_dict = [dict(zip(column_names, row)) for row in alumnos]
            cursor.execute("SELECT no_control, nombre_archivo, ruta_archivo FROM rutas_pdf")
            archivos = cursor.fetchall()
            archivos_dict = {}
            for archivo in archivos:
                no_control = archivo[0]
                if no_control not in archivos_dict:
                    archivos_dict[no_control] = []
                archivos_dict[no_control].append({'nombre': archivo[1], 'ruta': os.path.basename(archivo[2])})
            for row in alumnos_dict:
                count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado', 'Atendidos'] and row[key] not in [None, ''])
                row['Conteo'] = count_non_empty
            return render_template('profesores_dashboard.html', alumnos=alumnos_dict, columns=column_names)
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
            return redirect(url_for('iniciar_profesores'))
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('iniciar_profesores'))

#Metodo para ir a la ruta para actualizar el alumno
@app.route('/edit_record/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    if 'user_id' in session and session.get('user_role') == 'profesor':
        if request.method == 'POST':
            if 'save_changes' in request.form:
                print(f"Iniciando el guardado de cambios para el registro {record_id}")
                try:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    print("Conexión a la base de datos establecida")
                    # Actualizar columnas
                    for column, value in request.form.items():
                        if column not in ['NoControl', 'save_changes', 'columns_to_clear']:
                            print(f"Actualizando columna {column} con valor {value}")
                            cursor.execute(f"UPDATE jornadas_academicas SET `{column}` = %s WHERE NoControl = %s", (value, record_id))
                    # Limpiar columnas
                    columns_to_clear = request.form.getlist('columns_to_clear')
                    print(f"Columnas a limpiar: {columns_to_clear}")
                    for column_name in columns_to_clear:
                        cursor.execute(f"UPDATE jornadas_academicas SET `{column_name}` = NULL WHERE NoControl = %s", (record_id,))
                        print(f"Columna {column_name} limpiada")
                        # Buscar y eliminar archivos asociados
                        cursor.execute("SELECT ruta_archivo FROM rutas_pdf WHERE no_control = %s AND tabla_referencia = %s", (record_id, column_name))
                        file_paths = cursor.fetchall()
                        # Verificación adicional
                        if not file_paths:
                            print(f"No se encontraron rutas de archivos para no_control={record_id} y tabla_referencia={column_name}")
                        else:
                            print(f"Rutas de archivos encontradas para {column_name}: {file_paths}")
                        for file_path in file_paths:
                            file_path = file_path[0]
                            if os.path.exists(file_path):
                                print(f"Eliminando archivo: {file_path}")
                                os.remove(file_path)
                            else:
                                print(f"Archivo no encontrado: {file_path}")
                            # Solo eliminar el registro en la base de datos si el archivo existe o si quieres hacerlo de todos modos
                            cursor.execute("DELETE FROM rutas_pdf WHERE no_control = %s AND tabla_referencia = %s", (record_id, column_name))
                            print(f"Registro eliminado en rutas_pdf para {column_name}")
                        # Reordenar los IDs en rutas_pdf para que sean consecutivos
                        cursor.execute("SET @count = 0;")
                        cursor.execute("UPDATE rutas_pdf SET id = @count:= @count + 1;")
                        cursor.execute("ALTER TABLE rutas_pdf AUTO_INCREMENT = 1;")
                        print("IDs en rutas_pdf reordenados")

                    conn.commit()
                    print("Cambios guardados en la base de datos")
                    flash('Cambios guardados con éxito', 'success')
                except mysql.connector.Error as err:
                    print(f"Error en la base de datos: {err}")
                    flash(f"Error en la base de datos: {err}", 'error')
                finally:
                    cursor.close()
                    conn.close()
                    print("Conexión a la base de datos cerrada")
                return redirect(url_for('profesores_dashboard'))

            elif 'delete_record' in request.form:
                print(f"Iniciando eliminación del registro {record_id}")
                try:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    print("Conexión a la base de datos establecida")

                    # Eliminar archivos asociados
                    cursor.execute("SELECT ruta_archivo FROM rutas_pdf WHERE no_control = %s", (record_id,))
                    file_paths = cursor.fetchall()
                    print(f"Rutas de archivos encontradas: {file_paths}")
                    for file_path in file_paths:
                        file_path = file_path[0]
                        if os.path.exists(file_path):
                            print(f"Eliminando archivo: {file_path}")
                            os.remove(file_path)
                        else:
                            print(f"Archivo no encontrado: {file_path}")

                    # Eliminar registro en rutas_pdf y jornadas_academicas
                    cursor.execute("DELETE FROM rutas_pdf WHERE no_control = %s", (record_id,))
                    print(f"Registros eliminados en rutas_pdf para {record_id}")
                    cursor.execute("DELETE FROM jornadas_academicas WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en jornadas_academicas para {record_id}")
                    cursor.execute("DELETE FROM alumnos WHERE NoControl = %s", (record_id,))
                    print(f"Registros eliminados en alumnos para {record_id}")
                    conn.commit()

                    # Reordenar los IDs en rutas_pdf para que sean consecutivos
                    cursor.execute("SET @count = 0;")
                    cursor.execute("UPDATE rutas_pdf SET id = @count:= @count + 1;")
                    cursor.execute("ALTER TABLE rutas_pdf AUTO_INCREMENT = 1;")
                    print("IDs en rutas_pdf reordenados")

                    flash('Registro y archivos eliminados con éxito', 'success')
                except mysql.connector.Error as err:
                    print(f"Error en la base de datos: {err}")
                    flash(f"Error en la base de datos: {err}", 'error')
                finally:
                    cursor.close()
                    conn.close()
                    print("Conexión a la base de datos cerrada")
                return redirect(url_for('profesores_dashboard'))

            elif 'go_back' in request.form:
                print("Regresando al dashboard de profesores")
                return redirect(url_for('profesores_dashboard'))

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
                    return render_template('action_pages/actualizar_alumno.html', record=record)
                else:
                    print(f"Registro {record_id} no encontrado")
                    flash('Registro no encontrado', 'error')
                    return redirect(url_for('profesores_dashboard'))
            except mysql.connector.Error as err:
                print(f"Error en la base de datos: {err}")
                flash(f"Error en la base de datos: {err}", 'error')
                return redirect(url_for('profesores_dashboard'))
            finally:
                cursor.close()
                conn.close()
                print("Conexión a la base de datos cerrada")
    print("Redirigiendo al dashboard de profesores")
    return redirect(url_for('profesores_dashboard'))

#Metodo para el boton de cerrar session
@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('index'))

# Configura el logger
logging.basicConfig(filename='app_errors.log', level=logging.ERROR)

# Configura el logger para registrar los errores en un archivo
logging.basicConfig(filename='app_errors.log',
                    level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Función para manejar errores 404
@app.errorhandler(404)
def page_not_found(error):
    logging.error(f"404 Error: {request.path} - {error}")
    return render_template('errores/404.html'), 404

# Función para manejar errores 500
@app.errorhandler(500)
def internal_server_error(error):
    logging.error(f"500 Error: {error}")
    return render_template('errores/500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)