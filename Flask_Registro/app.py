import random
import re
import string
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from flask_mail import Mail, Message

app = Flask(__name__)

app.secret_key = '123456'

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'sarananibolivia25@gmail.com'  # Cambia esto
app.config['MAIL_PASSWORD'] = 'xpyt iloj iwjj lrys'  # Cambia esto
app.config['MAIL_USE_TLS'] = True
mail = Mail(app)

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
    return redirect(url_for('registro'))

# Ruta de registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        telefono = request.form['telefono']
        
        # Validaciones
        if not nombre or not correo or not contraseña or not telefono:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('registro.html')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            flash('Correo inválido', 'danger')
            return render_template('registro.html')

        if not telefono.isdigit():
            flash('El teléfono debe contener solo números', 'danger')
            return render_template('registro.html')

        if not validar_contraseña(contraseña):
            flash('La contraseña debe tener al menos 8 caracteres, incluyendo una mayúscula, una minúscula, un número y un símbolo especial.', 'danger')
            return render_template('registro.html')

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
                "INSERT INTO usuarios (nombre, correo, contraseña, telefono, codigo_verificacion, verificado) "
                "VALUES (%s, %s, %s, %s, %s, %s)", 
                (nombre, correo, contraseña_hash, telefono, codigo_verificacion, False)
            )
            conn.commit()

            # Enviar el correo de verificación
            msg = Message('Verificación de cuenta', sender=app.config['MAIL_USERNAME'], recipients=[correo])
            msg.body = f'Tu código de verificación es: {codigo_verificacion}'
            mail.send(msg)

            flash('Se ha enviado un código de verificación a tu correo.', 'success')
            session['correo_verificacion'] = correo  # Guardar correo en la sesión
            return redirect(url_for('verificar_codigo_registro'))

        except Exception as e:
            flash(f'Error al registrar el usuario: {str(e)}', 'danger')
            if conn:
                conn.rollback()

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template('registro.html')

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
                return redirect(url_for('home'))
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