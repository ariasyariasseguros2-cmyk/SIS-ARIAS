class Roles:
    BROKER = 'BROKER'
    EJECUTIVO = 'EJECUTIVO DE CUENTAS'
    OPERADOR = 'OPERADOR'
    SUB_AGENTE = 'SUB AGENTE'

def can_view_maestros(role_name):
    return role_name in [Roles.BROKER, Roles.EJECUTIVO, Roles.OPERADOR, Roles.SUB_AGENTE]

def can_access_maestros(role_name):
    return role_name == Roles.BROKER

def can_delete(role_name):
    # BROKER: Yes
    # EJECUTIVO: Yes ("solo mira y ELIMINA")
    # OPERADOR: No
    # SUB AGENTE: No
    return role_name in [Roles.BROKER, Roles.EJECUTIVO]

def can_edit(role_name):
    # BROKER: Yes
    # EJECUTIVO: No ("solo mira y ELIMINA" implies no edit?) - User said "solo mira". Usually means Read Only.
    # But OPERADOR "adiciona, actualiza".
    # So EJECUTIVO cannot edit.
    # OPERADOR: Yes
    # SUB AGENTE: Yes ("adiciona") - presumably updates too? "Acceso a solo sus cuentas... adiciona, NO ELIMINA". 
    # Usually "adiciona" implies creation. Updates? Let's assume yes for own accounts.
    return role_name in [Roles.BROKER, Roles.OPERADOR, Roles.SUB_AGENTE]

def can_create(role_name):
    return role_name in [Roles.BROKER, Roles.OPERADOR, Roles.SUB_AGENTE]


def can_create_poliza(role_name):
    # Crear/renovar pólizas habilitado para EJECUTIVO sin ampliar create global.
    return role_name in [Roles.BROKER, Roles.OPERADOR, Roles.SUB_AGENTE, Roles.EJECUTIVO]

def get_role_scope(role_name):
    if role_name == Roles.SUB_AGENTE:
        return 'OWN'
    return 'ALL'


def can_restore(role_name):
    """Permiso para restaurar o anular (acciones sobre estado)."""
    # Según la política actual BROKER y OPERADOR pueden realizar restauraciones/anulaciones
    return role_name in [Roles.BROKER, Roles.OPERADOR]


# ------------------ Decoradores y utilidades de autorización ------------------
from functools import wraps
from flask import session, jsonify, redirect, url_for

def _unauthorized(response_mode='json'):
    if response_mode == 'redirect':
        return redirect(url_for('main.home'))
    return jsonify({'ok': False, 'error': 'No autorizado'}), 403

def require_permission(check_fn, response_mode='json', ownership_check_fn=None):
    """
    Decorador general para rutas que requieren permiso.

    - check_fn(role_name) -> bool
    - response_mode: 'json' (por defecto) o 'redirect' (para vistas HTML)
    - ownership_check_fn: opcional función(*args, **kwargs) -> owner_identifier
      Si el rol tiene scope 'OWN' (según get_role_scope) y owner != session['user'] entonces se deniega.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            role = session.get('role_name')
            if not role:
                return _unauthorized(response_mode)

            try:
                if not check_fn(role):
                    return _unauthorized(response_mode)
            except Exception:
                return _unauthorized(response_mode)

            # Restricción adicional por ownership para roles con scope OWN.
            if ownership_check_fn:
                scope = get_role_scope(role)
                if scope == 'OWN':
                    try:
                        owner = ownership_check_fn(*args, **kwargs)
                    except Exception:
                        owner = None
                    if owner and owner != session.get('user'):
                        return _unauthorized(response_mode)

            return f(*args, **kwargs)
        return wrapper
    return decorator


