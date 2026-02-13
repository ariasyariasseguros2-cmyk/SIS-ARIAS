import os
from flask import Flask, render_template, request, redirect, url_for, session
from routes.route import bp as main_bp

app = Flask(__name__)
app.secret_key = 'cambia-esta-secret'  # Cambia esta clave por una segura
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.register_blueprint(main_bp)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # Import lazy para evitar tocar imports globales
        from models.db import get_connection

        error = None
        row = None

        try:
            cnx = get_connection()
            cur = cnx.cursor(dictionary=True)
            # Usar el SP para obtener el usuario
            cur.execute("CALL sp_login_usuario(%s)", (username,))
            row = cur.fetchone()
            # Consumir cualquier conjunto de resultados adicional del SP
            while cur.nextset():
                pass
            cur.close()
            cnx.close()
        except Exception:
            error = 'Error de conexión a base de datos.'
            return render_template('view/login.html', error=error)

        def verify_password(plain: str, stored: str) -> bool:
            # Acepta hash (Werkzeug) o texto plano
            if stored == plain:
                return True
            try:
                from werkzeug.security import check_password_hash
                # Intentar validar formato hash típico
                if stored and (stored.count('$') >= 2 or stored.startswith(('pbkdf2:', 'scrypt:', 'argon2:', 'sha256:'))):
                    return check_password_hash(stored, plain)
            except Exception:
                pass
            return False

        if row and verify_password(password, row['password']):
            session['user'] = row['username']
            session['user_id'] = row['id']
            session['role_id'] = row['id_rol']
            session['role_name'] = row['rol_nombre']
            return redirect(url_for('main.home'))
        else:
            error = 'Credenciales inválidas. Intenta nuevamente.'
            return render_template('view/login.html', error=error)
    return render_template('view/login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)