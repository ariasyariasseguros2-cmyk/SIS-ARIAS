import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from routes.route import bp as main_bp

app = Flask(__name__)
app.secret_key = 'cambia-esta-secret'  # Cambia esta clave por una segura
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['ACTIVE_SESSIONS'] = {}

app.register_blueprint(main_bp)

@app.before_request
def require_login():
    if request.path.startswith('/static/'):
        return None

    if request.path in ('/login', '/logout'):
        return None

    token = session.get('auth_token')
    user = session.get('user')
    if token and user:
        active = app.config.get('ACTIVE_SESSIONS', {}).get(token)
        if active and active.get('user') == user:
            return None

    if request.path.startswith('/api/'):
        session.clear()
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401

    session.clear()
    return redirect(url_for('login'))

@app.after_request
def disable_cache(response):
    if request.path.startswith('/static/'):
        return response
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

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
            try:
                while cur.nextset():
                    pass
            except Exception:
                pass
            cur.close()
            cnx.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            error = f'Error de conexión: {e}'
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
            old_token = session.pop('auth_token', None)
            if old_token:
                app.config.get('ACTIVE_SESSIONS', {}).pop(old_token, None)

            session['user'] = row['username']
            session['user_id'] = row['id']
            session['role_id'] = row['id_rol']
            session['role_name'] = row['rol_nombre']
            session['user_display_name'] = (row.get('nombre') or row.get('name') or '').strip()
            if not session['user_display_name']:
                try:
                    cnx = get_connection()
                    cur = cnx.cursor()
                    cur.execute(
                        "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1",
                        (row['username'],),
                    )
                    name_row = cur.fetchone()
                    if name_row and name_row[0]:
                        session['user_display_name'] = str(name_row[0]).strip()
                    cur.close()
                    cnx.close()
                except Exception:
                    session['user_display_name'] = row['username']

            token = secrets.token_urlsafe(32)
            app.config.get('ACTIVE_SESSIONS', {})[token] = {
                'user': session.get('user'),
                'user_id': session.get('user_id'),
            }
            session['auth_token'] = token
            return redirect(url_for('main.home'))
        else:
            error = 'Credenciales inválidas. Intenta nuevamente.'
            return render_template('view/login.html', error=error)
    return render_template('view/login.html')

@app.route('/logout')
def logout():
    token = session.get('auth_token')
    if token:
        app.config.get('ACTIVE_SESSIONS', {}).pop(token, None)
    session.clear()
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('view/404.html', requested_url=request.path), 404

if __name__ == '__main__':
    app.run(debug=True)
