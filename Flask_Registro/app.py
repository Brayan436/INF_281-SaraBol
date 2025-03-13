import random
import re
import string
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

app = Flask(__name__)

app.secret_key = '123456'

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] =   # Cambia esto , añadir tu correo 
app.config['MAIL_PASSWORD'] =   # Cambia esto
app.config['MAIL_USE_TLS'] = True
mail = Mail(app)

# Datos de ejemplo para países y ciudades
paises_ciudades = {
    "Argentina": ["Buenos Aires", "Córdoba", "Rosario"],
    "México": ["Ciudad de México", "Guadalajara", "Monterrey"],
    "España": ["Madrid", "Barcelona", "Valencia"],
    "Bolivia": ["La Paz", "Cochabamba", "Santa Cruz", "Beni", "Pando", "Sucre", "Tarija", "Potosi","Oruro"],
    "España": ["Madrid", "Barcelona", "Valencia"],
    # Agrega más países y ciudades según sea necesario
}

# Función para obtener la conexión a la base de datos
def get_db_connection():
    return psycopg2.connect(
        dbname="SARA_BOL",
        user="postgres",
        password="0903",  
        host="localhost"
    )

# Ruta principal
@app.route('/')
def home():
    return redirect(url_for('inicio_sesion'))

# Ruta de inicio de sesión
@app.route('/inicio_sesion', methods=['GET', 'POST'])
def inicio_sesion():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']

        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
            user = cur.fetchone()

            if user and check_password_hash(user[4], contraseña):  # user[4] es la contraseña hasheada
                if user[9]:  # Verificar si el usuario está verificado (columna verificado)
                    session['usuario_id'] = user[0]
                    flash('Inicio de sesión exitoso', 'success')
                    return redirect(url_for('evento'))
                else:
                    flash('Debes verificar tu correo antes de iniciar sesión.', 'warning')
            else:
                flash('Correo o contraseña incorrectos', 'danger')

        except Exception as e:
            flash(f'Error de conexión a la base de datos: {str(e)}', 'danger')

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    return render_template('inicio_sesion.html')

# Ruta de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        correo = request.form.get('correo')
        contraseña = request.form.get('contraseña')
        confirmacion_contraseña = request.form.get('confirmacion_contraseña')
        genero = request.form.get('genero')
        telefono = request.form.get('telefono')
        pais = request.form.get('pais')
        ciudad = request.form.get('ciudad')
        
        # Validaciones
        if not correo or not contraseña or not confirmacion_contraseña or not pais or not ciudad:
            flash('Todos los campos obligatorios deben ser completados.', 'danger')
            return render_template('registro.html', paises=paises_ciudades.keys())

        if not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            flash('Correo inválido', 'danger')
            return render_template('registro.html', paises=paises_ciudades.keys())

        if contraseña != confirmacion_contraseña:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('registro.html', paises=paises_ciudades.keys())

        if not validar_contraseña(contraseña):
            flash('La contraseña debe tener al menos 8 caracteres, incluyendo una mayúscula, una minúscula, un número y un símbolo especial.', 'danger')
            return render_template('registro.html', paises=paises_ciudades.keys())

        contraseña_hash = generate_password_hash(contraseña)

        # Generar código de verificación
        codigo_verificacion = generar_codigo()

        # Insertar datos en la base de datos
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO usuarios (nombre, apellido, correo, contraseña, genero, telefono, pais, ciudad, codigo_verificacion, verificado) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                (nombre, apellido, correo, contraseña_hash, genero, telefono, pais, ciudad, codigo_verificacion, False)
            )
            conn.commit()

            # Enviar el correo de verificación
            msg = Message('Verificación de cuenta', sender=app.config['MAIL_USERNAME'], recipients=[correo])
            msg.body = f'Tu código de verificación es: {codigo_verificacion}'
            mail.send(msg)

            flash('Se ha enviado un código de verificación a tu correo.', 'success')
            session['correo_verificacion'] = correo  # Guardar correo en la sesión
            return redirect(url_for('verificar_codigo_registro'))  # Redirigir a verificación

        except Exception as e:
            flash(f'Error al registrar el usuario: {str(e)}', 'danger')
            if conn:
                conn.rollback()

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('registro.html', paises=paises_ciudades.keys())

# Ruta para obtener ciudades según el país seleccionado
@app.route('/obtener_ciudades/<pais>')
def obtener_ciudades(pais):
    ciudades = paises_ciudades.get(pais, [])
    return jsonify(ciudades)

# Ruta para verificar el código de registro
@app.route('/verificar_codigo_registro', methods=['GET', 'POST'])
def verificar_codigo_registro():
    correo = session.get('correo_verificacion')
    
    if request.method == 'POST':
        codigo_ingresado = request.form['codigo']

        # Verificar el código en la base de datos
        conn = None
        cur = None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT codigo_verificacion FROM usuarios WHERE correo = %s", (correo,))
            codigo_correcto = cur.fetchone()[0]

            if codigo_correcto == codigo_ingresado:
                # Código verificado, actualizar usuario como verificado
                cur.execute("UPDATE usuarios SET verificado = TRUE WHERE correo = %s", (correo,))
                conn.commit()
                flash('Cuenta verificada correctamente.', 'success')
                return redirect(url_for('inicio_sesion'))  # Redirigir a inicio de sesión
            else:
                flash('El código ingresado es incorrecto.', 'danger')

        except Exception as e:
            flash(f'Error al verificar el código: {str(e)}', 'danger')

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    return render_template('verificar_codigo_registro.html')

# Ruta para el evento
@app.route('/evento')
def evento():
    if 'usuario_id' not in session:
        flash('Por favor, inicia sesión primero.', 'warning')
        return redirect(url_for('inicio_sesion'))
    return render_template('evento.html')

# Función para validar la contraseña
def validar_contraseña(contraseña):
    if len(contraseña) < 8:
        return False
    if not any(char.isupper() for char in contraseña):
        return False
    if not any(char.islower() for char in contraseña):
        return False
    if not any(char.isdigit() for char in contraseña):
        return False
    if not any(char in "!@#$%^&*()_+" for char in contraseña):
        return False
    return True

# Función para generar códigos de verificación aleatorios
def generar_codigo(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

if __name__ == '__main__':
    app.run(debug=True)
