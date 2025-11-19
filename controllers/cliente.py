# módulo: controllers/cliente.py
def get_clientes_data():
    from models.db import get_connection

    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute("CALL sp_list_clientes()")
        db_rows = cur.fetchall()
        while cur.nextset():
            pass
        cur.close()
        cnx.close()

        for dr in db_rows:
            fec = dr.get('fecha_registro')
            fec_str = fec.strftime('%d-%m-%Y') if hasattr(fec, 'strftime') else (str(fec) if fec else '')
            rows.append({
                'fec_reg': fec_str,
                'razon_social': dr.get('razon_social'),
                'doc': dr.get('tipo_documento'),
                'n_doc': dr.get('numero_documento'),
                'tel': dr.get('telefono'),
                'subagente': dr.get('subagente'),
                'email': dr.get('email'),
                'direccion': dr.get('direccion'),
            })
    except Exception:
        rows = []

    filters = {
        "orders": ["F. Reg.", "Razón Social", "Doc", "N.Doc", "Tel", "Email", "Subagente", "Dirección", "Estado"]
    }
    return {"rows": rows, "filters": filters, "title": "Clientes"}