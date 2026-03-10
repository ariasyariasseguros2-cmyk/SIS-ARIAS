from models.db import get_connection


def get_vendedores():
    """Retorna lista de agentes (vendedores) usando sp_listar_agentes."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.callproc('sp_listar_agentes')
            rows = []
            for result in cur.stored_results():
                rows = result.fetchall()
                break
        except Exception:
            cur.execute(
                "SELECT id, codigo_agente, nombre_vendedor, tipo_menor, tipo_regular, estado "
                "FROM agentes ORDER BY nombre_vendedor ASC"
            )
            rows = cur.fetchall() or []
        cur.close()
        return rows
    except Exception as e:
        print(f"[maestros.vendedores] get_vendedores error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_vendedor_by_id(v_id):
    """Obtiene un agente por id."""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, codigo_agente, nombre_vendedor, tipo_menor, tipo_regular, estado "
            "FROM agentes WHERE id = %s",
            (v_id,)
        )
        row = cur.fetchone()
        cur.close()
        return row
    except Exception as e:
        print(f"[maestros.vendedores] get_vendedor_by_id error: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def insertar_vendedor(codigo_agente, nombre_vendedor, tipo_menor, tipo_regular):
    """
    Inserta un agente usando sp_insertar_agente(IN codigo, IN nombre, IN tipo_menor, IN tipo_regular, OUT new_id).
    Fallback: INSERT directo.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        new_id = None
        try:
            cur.callproc('sp_insertar_agente', [
                (codigo_agente or '').strip(),
                (nombre_vendedor or '').strip(),
                float(tipo_menor or 0),
                float(tipo_regular or 0),
                0   # OUT p_new_id placeholder
            ])
            # Leer el OUT param
            cur.execute("SELECT @_sp_insertar_agente_4 AS new_id")
            r = cur.fetchone()
            new_id = r[0] if r else None
        except Exception:
            cur.execute(
                "INSERT INTO agentes (codigo_agente, nombre_vendedor, tipo_menor, tipo_regular) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
                (
                    (codigo_agente or '').strip(),
                    (nombre_vendedor or '').strip(),
                    float(tipo_menor or 0),
                    float(tipo_regular or 0),
                )
            )
            new_id = cur.lastrowid
        conn.commit()
        cur.close()
        return new_id
    except Exception as e:
        print(f"[maestros.vendedores] insertar_vendedor error: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def actualizar_vendedor(v_id, codigo_agente, nombre_vendedor, tipo_menor, tipo_regular, estado='ACTIVO'):
    """
    Actualiza un agente usando sp_editar_agente(IN id, IN codigo, IN nombre, IN tipo_menor, IN tipo_regular, IN estado).
    Fallback: UPDATE directo.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.callproc('sp_editar_agente', [
                int(v_id),
                (codigo_agente or '').strip(),
                (nombre_vendedor or '').strip(),
                float(tipo_menor or 0),
                float(tipo_regular or 0),
                estado or 'ACTIVO',
            ])
        except Exception:
            cur.execute(
                "UPDATE agentes "
                "SET codigo_agente = %s, nombre_vendedor = %s, "
                "    tipo_menor = %s, tipo_regular = %s, estado = %s "
                "WHERE id = %s",
                (
                    (codigo_agente or '').strip(),
                    (nombre_vendedor or '').strip(),
                    float(tipo_menor or 0),
                    float(tipo_regular or 0),
                    estado or 'ACTIVO',
                    int(v_id),
                )
            )
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"[maestros.vendedores] actualizar_vendedor error: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def eliminar_vendedor(v_id):
    """
    Elimina un agente usando sp_delete_agente(IN id, OUT deleted).
    Fallback: DELETE directo.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.callproc('sp_delete_agente', [int(v_id), 0])
            cur.execute("SELECT @_sp_delete_agente_1 AS deleted")
            r = cur.fetchone()
            deleted = r[0] if r else 0
        except Exception:
            cur.execute("DELETE FROM agentes WHERE id = %s", (int(v_id),))
            deleted = cur.rowcount
        conn.commit()
        cur.close()
        return deleted
    except Exception as e:
        print(f"[maestros.vendedores] eliminar_vendedor error: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

