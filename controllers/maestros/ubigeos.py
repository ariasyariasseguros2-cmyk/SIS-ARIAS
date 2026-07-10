from models.db import get_connection


def get_departamentos() -> list[str]:
    rows = []
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT TRIM(nombdep) AS nombre
            FROM ubigeo
            WHERE TRIM(COALESCE(nombdep, '')) <> ''
            ORDER BY nombre ASC
            """
        )
        rows = [row[0] for row in (cur.fetchall() or []) if row and row[0]]
    except Exception as e:
        print(f"[maestros.ubigeos] get_departamentos error: {e}")
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return rows


def get_provincias(departamento: str) -> list[str]:
    if not str(departamento or "").strip():
        return []

    rows = []
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT TRIM(nombprov) AS nombre
            FROM ubigeo
            WHERE UPPER(TRIM(nombdep)) = UPPER(TRIM(%s))
              AND TRIM(COALESCE(nombprov, '')) <> ''
            ORDER BY nombre ASC
            """,
            (departamento,),
        )
        rows = [row[0] for row in (cur.fetchall() or []) if row and row[0]]
    except Exception as e:
        print(f"[maestros.ubigeos] get_provincias error: {e}")
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return rows


def get_distritos(departamento: str, provincia: str) -> list[str]:
    if not str(departamento or "").strip() or not str(provincia or "").strip():
        return []

    rows = []
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT TRIM(nombdist) AS nombre
            FROM ubigeo
            WHERE UPPER(TRIM(nombdep)) = UPPER(TRIM(%s))
              AND UPPER(TRIM(nombprov)) = UPPER(TRIM(%s))
              AND TRIM(COALESCE(nombdist, '')) <> ''
            ORDER BY nombre ASC
            """,
            (departamento, provincia),
        )
        rows = [row[0] for row in (cur.fetchall() or []) if row and row[0]]
    except Exception as e:
        print(f"[maestros.ubigeos] get_distritos error: {e}")
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
    return rows
