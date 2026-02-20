from models.db import get_connection

def get_usuarios():
    """Obtiene usuarios con rol y ejecutivo."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("""
                SELECT 
                    u.id,
                    u.username,
                    u.nombre,
                    u.estado,
                    u.id_rol,
                    r.nombre AS rol,
                    u.id_ejecutivo,
                    e.nombre AS ejecutivo
                FROM usuarios u
                LEFT JOIN roles r ON r.idRol = u.id_rol
                LEFT JOIN ejecutivos e ON e.idEjecutivo = u.id_ejecutivo
                ORDER BY u.id ASC
            """)
            rows = cur.fetchall() or []
        except Exception:
            # Fallback al SP original (sin ejecutivo)
            cur.callproc('sp_listar_usuarios')
            rows = []
            for result in cur.stored_results():
                rows = result.fetchall()
                break
        # Asegurar orden por id asc incluso si el SP cambia el orden
        try:
            rows = sorted(rows, key=lambda r: (r.get('id') if isinstance(r, dict) else r[0]))
        except Exception:
            pass
        return rows
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

def update_usuario_ejecutivo(user_id, ejecutivo_id):
    """Actualiza el ejecutivo asignado a un usuario."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET id_ejecutivo = %s WHERE id = %s", (ejecutivo_id, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user ejecutivo: {e}")
        return False
    finally:
        conn.close()
