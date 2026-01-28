from models.db import get_connection

def get_endosatarios() -> list[dict]:
    """
    Retorna la lista de endosatarios activos (idEndosatario, nombre).
    En este caso, el SP sp_listar_endosatarios solo devuelve 'nombre',
    pero para consistencia con el template, devolveremos una lista de diccionarios
    o objetos que tengan atributo 'nombre'.
    """
    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("CALL sp_listar_endosatarios()")
        db_rows = cur.fetchall() or []
        cur.close()
        cnx.close()
        # El template espera objetos con atributo 'nombre'. 
        # db_rows ya es una lista de diccionarios [{'nombre': '...'}, ...]
        rows = db_rows
    except Exception as e:
        print(f"Error obteniendo endosatarios: {e}")
        rows = []
    return rows
