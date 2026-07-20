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


def resolve_ubigeo(
    ubigeo_code: str | None = None,
    departamento: str | None = None,
    provincia: str | None = None,
    distrito: str | None = None,
) -> dict[str, str]:
    result = {
        "ubigeo": "",
        "departamento": "",
        "provincia": "",
        "distrito": "",
    }

    code = str(ubigeo_code or "").strip()
    dep = str(departamento or "").strip()
    prov = str(provincia or "").strip()
    dist = str(distrito or "").strip()

    if not code and not dep and not prov and not dist:
        return result

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        if code:
            cur.execute(
                """
                SELECT
                    TRIM(ubigeo) AS ubigeo,
                    TRIM(nombdep) AS departamento,
                    TRIM(nombprov) AS provincia,
                    TRIM(nombdist) AS distrito
                FROM ubigeo
                WHERE TRIM(ubigeo) = TRIM(%s)
                LIMIT 1
                """,
                (code,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "ubigeo": row[0] or "",
                    "departamento": row[1] or "",
                    "provincia": row[2] or "",
                    "distrito": row[3] or "",
                }

        if dep and prov and dist:
            cur.execute(
                """
                SELECT
                    TRIM(ubigeo) AS ubigeo,
                    TRIM(nombdep) AS departamento,
                    TRIM(nombprov) AS provincia,
                    TRIM(nombdist) AS distrito
                FROM ubigeo
                WHERE UPPER(TRIM(nombdep)) = UPPER(TRIM(%s))
                  AND UPPER(TRIM(nombprov)) = UPPER(TRIM(%s))
                  AND UPPER(TRIM(nombdist)) = UPPER(TRIM(%s))
                LIMIT 1
                """,
                (dep, prov, dist),
            )
            row = cur.fetchone()
            if row:
                return {
                    "ubigeo": row[0] or "",
                    "departamento": row[1] or "",
                    "provincia": row[2] or "",
                    "distrito": row[3] or "",
                }

        if dep and prov:
            cur.execute(
                """
                SELECT
                    TRIM(ubigeo) AS ubigeo,
                    TRIM(nombdep) AS departamento,
                    TRIM(nombprov) AS provincia,
                    TRIM(nombdist) AS distrito
                FROM ubigeo
                WHERE UPPER(TRIM(nombdep)) = UPPER(TRIM(%s))
                  AND UPPER(TRIM(nombprov)) = UPPER(TRIM(%s))
                ORDER BY TRIM(nombdist) ASC
                LIMIT 1
                """,
                (dep, prov),
            )
            row = cur.fetchone()
            if row:
                return {
                    "ubigeo": row[0] or "",
                    "departamento": row[1] or "",
                    "provincia": row[2] or "",
                    "distrito": row[3] or "",
                }
    except Exception as e:
        print(f"[maestros.ubigeos] resolve_ubigeo error: {e}")
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

    return {
        "ubigeo": code,
        "departamento": dep,
        "provincia": prov,
        "distrito": dist,
    }
