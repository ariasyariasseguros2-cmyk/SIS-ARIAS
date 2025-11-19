def get_polizas_data(selection=None):
    # 1) Tomar valores desde la selección guardada en sesión (seguro)
    nombre_q = (selection.get('nombre') if selection else None)
    tipo_q   = (selection.get('tipo_doc') if selection else None)
    numero_q = (selection.get('n_doc') if selection else None)
    tel_q    = (selection.get('tel') if selection else None)

    # 2) Si tenemos número de documento, intentar cargar desde BD
    cli = None
    if numero_q:
        try:
            from models.db import get_connection
            cnx = get_connection()
            cur = cnx.cursor(dictionary=True)
            # Usamos el buscador, luego filtramos por coincidencia exacta de documento
            cur.execute("CALL sp_buscar_cliente(%s)", (numero_q,))
            db_rows = cur.fetchall() or []
            while cur.nextset():
                pass
            cur.close()
            cnx.close()

            # Elegir el que coincida exactamente con el número de documento
            for r in db_rows:
                if str(r.get('numero_documento', '')).strip() == str(numero_q).strip():
                    cli = r
                    break
            # Si no hay coincidencia exacta, tomar el primero como aproximación
            if not cli and db_rows:
                cli = db_rows[0]
        except Exception:
            cli = None

    # 3) Construir detalles con prioridad: BD → selección → valores por defecto
    nombre   = (cli.get('razon_social') if cli else None) or nombre_q or "-"
    tipo     = (cli.get('tipo_documento') if cli else None) or tipo_q or "-"
    numero   = (cli.get('numero_documento') if cli else None) or numero_q or "-"
    telefono = (cli.get('telefono') if cli else None) or tel_q or "-"

    details = {
        "nombre_completo": nombre,
        "tipo_documento": tipo,
        "numero_documento": numero,
        "telefono": telefono
    }

    # 4) Filas de pólizas (demo). Cuando tengas TB pólizas, aquí consultamos por cliente.
    rows = [
        {
            "contratante": nombre,
            "asegurado": nombre,
            "cia": "Mapfre",
            "ramo": "SOAT",
            "producto": "CARGA",
            "poliza": "3200524075804",
            "nro": "345",
            "moneda": "PEN",
            "vig_desde": "17-11-2025",
            "vig_hasta": "17-11-2026",
            "sub_agente": "RAMOS YORK PAMELA",
            "asegurada": "A0C945"
        }
    ]

    return {
        "title": "Pólizas",
        "details": details,
        "rows": rows
    }