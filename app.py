import os
import time
import glob
import threading
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from routes.route import bp as main_bp

app = Flask(__name__)
app.secret_key = os.environ.get('SIS_ARIAS_SECRET_KEY') or 'cambia-esta-secret'  # Cambia esta clave por una segura
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
# Cierra la sesión tras 1 hora sin actividad (Flask renueva la cookie en cada request)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SESSION_IDLE_TIMEOUT_SECS'] = 60 * 60
app.config['SESSION_PING_INTERVAL_SECS'] = 5 * 60
app.config['SESSION_WARNING_SECS'] = 60
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ── Limpieza automática de uploads/temp/ ──────────────────────────────────────
# Elimina archivos con más de 1 hora de antigüedad cada 60 minutos.
_TEMP_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
_TEMP_MAX_AGE_SECS = 3600  # 1 hora

def _cleanup_temp_loop():
    os.makedirs(_TEMP_FOLDER, exist_ok=True)
    while True:
        time.sleep(_TEMP_MAX_AGE_SECS)
        threshold = time.time() - _TEMP_MAX_AGE_SECS
        for f in glob.glob(os.path.join(_TEMP_FOLDER, '*')):
            if os.path.isfile(f) and os.path.getmtime(f) < threshold:
                try:
                    os.remove(f)
                    print(f'[cleanup_temp] eliminado: {f}')
                except Exception as _e:
                    print(f'[cleanup_temp] error al eliminar {f}: {_e}')

_cleanup_thread = threading.Thread(target=_cleanup_temp_loop, daemon=True, name='cleanup-temp')
_cleanup_thread.start()
# ──────────────────────────────────────────────────────────────────────────────

app.register_blueprint(main_bp)

# Exponer helpers de RBAC al contexto de Jinja para plantillas
try:
    from utils.rbac import (
        Roles,
        can_create,
        can_create_poliza,
        can_edit,
        can_delete,
        can_view_maestros,
        can_access_maestros,
        can_restore,
        can_hard_delete,
        get_role_scope,
        can_view_dashboard_charts,
    )

    @app.context_processor
    def inject_rbac():
        def get_initials(name):
            if not name: return "?"
            parts = name.strip().split()
            if len(parts) >= 2:
                return (parts[0][0] + parts[1][0]).upper()
            return parts[0][0].upper()

        notifications = []
        if session.get('user'):
            try:
                from controllers.dashboard import get_expired_policy_notifications
                notifications = get_expired_policy_notifications(limit=10)
            except Exception as e:
                print(f"[context.notifications] {e}")

        return {
            'Roles': Roles,
            'can_create': can_create,
            'can_create_poliza': can_create_poliza,
            'can_edit': can_edit,
            'can_delete': can_delete,
            'can_view_maestros': can_view_maestros,
            'can_access_maestros': can_access_maestros,
            'can_restore': can_restore,
            'can_hard_delete': can_hard_delete,
            'get_role_scope': get_role_scope,
            'can_view_dashboard_charts': can_view_dashboard_charts,
            'get_initials': get_initials,
            'notifications': notifications,
        }
except Exception:
    # Si falla la importación, seguimos sin inyectar (evita romper arranque)
    pass

@app.before_request
def require_login():
    if request.path.startswith('/static/'):
        return None

    if request.path in ('/', '/login', '/logout', '/FacturaVentas'):
        return None

    if session.get('user'):
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
    if session.get('user'):
        return redirect(url_for('main.dashboard'))
    return render_template('view/landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    timeout_error = 'Tu sesión expiró por inactividad. Vuelve a iniciar sesión.'
    if request.method == 'GET' and session.get('user'):
        return redirect(url_for('main.dashboard'))
    if request.method == 'GET':
        error = timeout_error if request.args.get('reason') == 'timeout' else None
        return render_template('view/login.html', error=error)
    if request.method == 'POST':
        session.clear()

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # Import lazy para evitar tocar imports globales
        from models.db import get_connection

        error = None
        row = None

        try:
            cnx = get_connection()
            cur = cnx.cursor(dictionary=True)
            try:
                # Intentar usar el SP (que puede fallar si no se ha actualizado la tabla)
                cur.execute("CALL sp_login_usuario(%s)", (username,))
                row = cur.fetchone()
                while cur.nextset(): pass
            except Exception as sp_err:
                print(f"[login] SP falló, intentando SELECT directo: {sp_err}")
                # Fallback a SELECT directo si el SP falla (ej. por columnas faltantes)
                cur.execute("""
                    SELECT u.id, u.username, u.password, u.id_rol, u.nombre, 
                           r.nombre as rol_nombre
                    FROM usuarios u
                    LEFT JOIN roles r ON u.id_rol = r.idRol
                    WHERE u.username = %s LIMIT 1
                """, (username,))
                row = cur.fetchone()
            cur.close()
            cnx.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            error = f'Error de conexión: {e}'
            return render_template('view/login.html', error=error)

        def verify_password(plain: str, stored: str) -> bool:
            # Acepta hash (Werkzeug) o texto plano
            if stored is None:
                return False
            stored = str(stored).strip()
            plain = str(plain).strip()
            if stored == plain:
                return True
            try:
                from werkzeug.security import check_password_hash
                # Intentar validar formato hash típico
                if stored and (stored.count('$') >= 2 or stored.startswith(('pbkdf2:', 'scrypt:', 'argon2:', 'sha256:'))):
                    return check_password_hash(stored, plain)
            except Exception:
                pass
            try:
                from models.db import load_settings
                from utils.crypto import decrypt_password

                cfg = load_settings() or {}
                key_phrase = cfg.get("key_encrypt_bd")
                salt = cfg.get("salt_encrypt", "SIS-ARIAS")
                decrypted = decrypt_password(stored, key_phrase, salt)
                return (decrypted or '').strip() == plain
            except Exception:
                pass
            return False

        stored_password = (row or {}).get('password')
        if row and stored_password and verify_password(password, stored_password):
            session.permanent = True
            session['user'] = row['username']
            session['user_id'] = row['id']
            session['role_id'] = row['id_rol']
            session['timeout_session_id'] = os.urandom(16).hex()
            
            # FIX: Normalizar el nombre del rol para evitar problemas de permisos por mayúsculas/minúsculas o espacios.
            rol_nombre = (row.get('rol_nombre') or '').strip().upper()
            session['role_name'] = rol_nombre

            session['user_display_name'] = (row.get('nombre') or row.get('name') or '').strip()
            
            # Fetch foto_perfil separately if not in row
            session['foto_perfil'] = row.get('foto_perfil')
            session['color_avatar'] = row.get('color_avatar') or '#3b82f6'
            
            if not session.get('user_display_name') or session.get('foto_perfil') is None or 'color_avatar' not in session:
                try:
                    cnx = get_connection()
                    cur = cnx.cursor(dictionary=True)
                    # Intentar obtener solo las columnas que existan para no romper
                    cur.execute("SHOW COLUMNS FROM usuarios LIKE 'foto_perfil'")
                    has_foto = cur.fetchone()
                    cur.execute("SHOW COLUMNS FROM usuarios LIKE 'color_avatar'")
                    has_color = cur.fetchone()
                    
                    cols = ["nombre"]
                    if has_foto: cols.append("foto_perfil")
                    if has_color: cols.append("color_avatar")
                    
                    cur.execute(
                        f"SELECT {', '.join(cols)} FROM usuarios WHERE id = %s LIMIT 1",
                        (row['id'],)
                    )
                    u_row = cur.fetchone()
                    if u_row:
                        nombre_final = (u_row.get('nombre') or row.get('username') or '').strip()
                        session['user_display_name'] = nombre_final if nombre_final else row.get('username')
                        session['foto_perfil'] = u_row.get('foto_perfil') if has_foto else None
                        session['color_avatar'] = u_row.get('color_avatar') if has_color else '#3b82f6'
                    cur.close()
                    cnx.close()
                except Exception as e:
                    print(f"Error fetching extra user data: {e}")
                    if not session.get('user_display_name'):
                        session['user_display_name'] = row.get('username')

            return redirect(url_for('main.home'))
        else:
            error = 'Credenciales inválidas. Intenta nuevamente.'
            return render_template('view/login.html', error=error)
    return render_template('view/login.html')

@app.route('/api/session/ping', methods=['POST'])
def session_ping():
    if not session.get('user'):
        session.clear()
        return jsonify({'ok': False, 'error': 'No autenticado'}), 401
    session.permanent = True
    session.modified = True
    return jsonify({'ok': True})

@app.route('/logout')
def logout():
    reason = request.args.get('reason')
    session.clear()
    if reason:
        return redirect(url_for('login', reason=reason))
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('view/404.html', requested_url=request.path), 404

if __name__ == '__main__':
    app.run(debug=True)
