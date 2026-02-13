from models.db import get_connection

def get_usuarios():
    """Obtiene la lista de usuarios con su rol asignado."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        # Usamos el SP creado en la migración
        cur.callproc('sp_listar_usuarios')
        # fetch results from stored procedure
        for result in cur.stored_results():
            return result.fetchall()
        return []
    except Exception as e:
        print(f"Error getting users: {e}")
        return []
    finally:
        conn.close()

def get_roles():
    """Obtiene la lista de roles disponibles."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.callproc('sp_listar_roles')
        for result in cur.stored_results():
            return result.fetchall()
        return []
    except Exception as e:
        print(f"Error getting roles: {e}")
        return []
    finally:
        conn.close()

def update_usuario_rol(user_id, role_id):
    """Actualiza el rol de un usuario."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.callproc('sp_actualizar_usuario_rol', (user_id, role_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user role: {e}")
        return False
    finally:
        conn.close()
