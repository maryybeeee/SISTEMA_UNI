from flask import Flask, render_template, request, redirect, url_for, session, flash
import bcrypt, logging, mysql.connector

# Configuración de la base de datos
db_config = {'user': 'root', 'host': 'localhost', 'database': 'bd'}
app = Flask(__name__)
app.secret_key = 'MiguelProyectoIta009.'

# Ruta que se mostrará al ingresar en la página
@app.route('/')
def index():
    return render_template('index.html')

# Ruta que se mostrará al ingresar en el registro de alumnos
@app.route('/register_alumnos')
def register_alumnos():
    return render_template('register_alumnos.html')

# Método para registrar a un alumno y guardarlo en la tabla alumno
@app.route('/registro_alumnos', methods=['POST'])
def registro_alumnos():
    error = None
    if request.method == 'POST':
        nombres = request.form['nombres']
        apellidoP = request.form['apellido_paterno']
        apellidoM = request.form['apellido_materno']
        correo = request.form['correo']
        no_control = request.form['no_control']
        contraseña = bcrypt.hashpw(request.form['contraseña'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jornadas_academicas WHERE NoControl = %s", (no_control,))
            jornada_academica = cursor.fetchone()
            if jornada_academica:
                cursor.execute("SELECT * FROM alumnos WHERE NoControl = %s", (no_control,))
                user = cursor.fetchone()
                if user:
                    error = 'Número de control ya registrado'
                else:
                    cursor.execute("INSERT INTO alumnos (Nombres, ApellidoP, ApellidoM, Correo, Contraseña, NoControl) VALUES (%s, %s, %s, %s, %s, %s)", (nombres, apellidoP, apellidoM, correo, contraseña, no_control,))
                    conn.commit()
                    return redirect(url_for('login_alumnos'))
            else:
                error = 'Número de control no encontrado en jornadas académicas'
        except mysql.connector.Error as err:
            error = f"Error en la base de datos: {err}"
        finally:
            cursor.close()
            conn.close()
    return render_template('register_alumnos.html', error=error)

# Ruta para mostrar los archivos de los alumnos
@app.route('/alumnos_dashboard')
def alumnos_dashboard():
    if 'user_id' in session and session.get('user_role') == 'alumno':
        no_control = session['user_id']
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jornadas_academicas WHERE NoControl = %s", (no_control,))
            alumno = cursor.fetchall()
        except mysql.connector.Error as err:
            error = f"Error en la base de datos: {err}"
            return render_template('alumnos_dashboard.html', error=error)
        finally:
            cursor.close()
            conn.close()
        return render_template('alumnos_dashboard.html', alumno=alumno)
    else:
        return redirect(url_for('login_alumnos'))

# Ruta que se mostrará al ingresar en el login de alumnos
@app.route('/login_alumnos')
def login_alumnos():
    return render_template('login_alumnos.html')

# Método para que los alumnos inicien sesión
@app.route('/iniciar_alumnos', methods=['POST'])
def iniciar_alumnos():
    error = None
    if request.method == 'POST':
        no_control = request.form.get('no_control')
        contraseña = request.form.get('contraseña')
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT NoControl, Nombres, ApellidoP, ApellidoM, Contraseña FROM alumnos WHERE NoControl = %s", (no_control,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(contraseña.encode('utf-8'), user[4].encode('utf-8')):
                session['user_id'] = user[0]
                session['user_role'] = 'alumno'
                return redirect(url_for('alumnos_dashboard'))
            else:
                error = 'Número de control o contraseña incorrectos'
        except mysql.connector.Error as err:
            error = f"Error en la base de datos: {err}"
        finally:
            cursor.close()
            conn.close()
    return render_template('login_alumnos.html', error=error)

# Ruta que se mostrará al ingresar en el login de profesores
@app.route('/login_profesores')
def login_profesores():
    return render_template('login_profesores.html')

# Método para que los profesores inicien sesión
@app.route('/iniciar_profesores', methods=['GET', 'POST'])
def iniciar_profesores():
    error = None
    if request.method == 'POST':
        no_trabajador = request.form.get('no_trabajador')
        nombres = request.form.get('nombres')
        clave = request.form.get('clave')
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profesores WHERE NoTrabajador = %s AND Nombres = %s", (no_trabajador, nombres,))
            user = cursor.fetchone()
            if user:
                if bcrypt.checkpw(clave.encode('utf-8'), user[2].encode('utf-8')):
                    session['user_id'] = user[0]
                    session['user_role'] = 'profesor'
                    return redirect(url_for('profesores_dashboard'))
                else:
                    error = 'Nombres o contraseña incorrectos'
            else:
                error = 'Profesor no encontrado'
        except mysql.connector.Error as err:
            error = f"Error en la base de datos: {err}"
        finally:
            cursor.close()
            conn.close()
    return render_template('login_profesores.html', error=error)

# Ruta para mostrar la tabla de las jornadas académicas de los alumnos
@app.route('/profesores_dashboard', methods=['GET', 'POST'])
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
                            cursor.execute(f"ALTER TABLE jornadas_academicas ADD COLUMN `{column_name}` VARCHAR(255) NOT NULL AFTER `{columns[conteo_column-1]}`")
                        else:
                            cursor.execute(f"ALTER TABLE jornadas_academicas ADD COLUMN `{column_name}` VARCHAR(255) NOT NULL")
                        conn.commit()
                        cursor.close()
                        conn.close()
                        flash('Columna agregada con éxito', 'success')
                    except mysql.connector.Error as err:
                        flash(f"Error en la base de datos: {err}", 'error')
            elif 'remove_column' in request.form:
                column_name = request.form['column_name']
                if column_name:
                    try:
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        cursor.execute(f"ALTER TABLE jornadas_academicas DROP COLUMN `{column_name}`")
                        conn.commit()
                        cursor.close()
                        conn.close()
                        flash('Columna eliminada con éxito', 'success')
                    except mysql.connector.Error as err:
                        flash(f"Error en la base de datos: {err}", 'error')

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
            cursor.close()
            conn.close()

            # Convertir resultados a una lista de diccionarios
            column_names = ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres'] + columns + ['Estado', 'Atendidos']
            alumnos_dict = [dict(zip(column_names, row)) for row in alumnos]

            # Contar valores vacíos y no vacíos
            for row in alumnos_dict:
                count_non_empty = sum(1 for key in row if key not in ['NoControl', 'ApellidoP', 'ApellidoM', 'Nombres', 'Conteo', 'Estado', 'Atendidos'] and row[key] not in [None, ''])
                row['Conteo'] = count_non_empty
            
            return render_template('profesores_dashboard.html', alumnos=alumnos_dict, columns=column_names)
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
            return redirect(url_for('iniciar_profesores'))

    return redirect(url_for('iniciar_profesores'))

#Metodo para ir a la ruta para actualizar el alumno
@app.route('/edit_record/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    if 'user_id' in session and session.get('user_role') == 'profesor':
        if request.method == 'POST':
            if 'save_changes' in request.form:
                try:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()

                    # Guardar los cambios de las celdas
                    for column, value in request.form.items():
                        if column not in ['NoControl', 'save_changes', 'columns_to_clear']:
                            cursor.execute(f"UPDATE jornadas_academicas SET `{column}` = %s WHERE NoControl = %s", (value, record_id))

                    # Eliminar los valores que se han marcado para eliminar
                    columns_to_clear = request.form.getlist('columns_to_clear')
                    for column_name in columns_to_clear:
                        cursor.execute(f"UPDATE jornadas_academicas SET `{column_name}` = NULL WHERE NoControl = %s", (record_id,))

                    conn.commit()
                    cursor.close()
                    conn.close()
                    flash('Cambios guardados con éxito', 'success')
                    return redirect(url_for('profesores_dashboard'))
                except mysql.connector.Error as err:
                    flash(f"Error en la base de datos: {err}", 'error')

            elif 'delete_record' in request.form:
                try:
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM jornadas_academicas WHERE NoControl = %s", (record_id,))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    flash('Registro eliminado con éxito', 'success')
                    return redirect(url_for('profesores_dashboard'))
                except mysql.connector.Error as err:
                    flash(f"Error en la base de datos: {err}", 'error')

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM jornadas_academicas WHERE NoControl = %s", (record_id,))
            record = cursor.fetchone()
            cursor.close()
            conn.close()
            if record:
                return render_template('action_pages/actualizar_alumno.html', record=record)
            else:
                flash('Registro no encontrado', 'error')
                return redirect(url_for('profesores_dashboard'))
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
            return redirect(url_for('profesores_dashboard'))
    return redirect(url_for('iniciar_profesores'))

#Metodo para eliminar el valor de una celda
@app.route('/delete_value/<int:record_id>', methods=['POST'])
def delete_value(record_id):
    column_name = request.form.get('column_name')
    if 'user_id' in session and session.get('user_role') == 'profesor':
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(f"UPDATE jornadas_academicas SET `{column_name}` = NULL WHERE NoControl = %s", (record_id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Valor eliminado con éxito', 'success')
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
        return redirect(url_for('edit_record', record_id=record_id))
    return redirect(url_for('iniciar_profesores'))

#Metodo para borrar a un alumno
@app.route('/delete_record/<int:record_id>', methods=['POST'])
def delete_record(record_id):
    if 'user_id' in session and session.get('user_role') == 'profesor':
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jornadas_academicas WHERE NoControl = %s", (record_id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Registro eliminado con éxito', 'success')
        except mysql.connector.Error as err:
            flash(f"Error en la base de datos: {err}", 'error')
        return redirect(url_for('profesores_dashboard'))
    return redirect(url_for('iniciar_profesores'))

#Metodo para el boton de cerrar session
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
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