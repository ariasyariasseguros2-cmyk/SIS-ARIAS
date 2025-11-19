def get_polizas_data():
    # Datos del titular/cliente mostrados en el panel superior
    details = {
        "nombre_completo": "RAMOS VARGAS MELGAR",
        "tipo_documento": "DNI/CEDULA",
        "numero_documento": "22888140",
        "telefono": "930179202"
    }

    # Filas de la tabla de pólizas (ejemplo; integrar con BD después)
    rows = [
        {
            "contratante": "RAMOS VARGAS MELGAR",
            "asegurado": "RAMOS VARGAS MELGAR",
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

    return {"title": "Pólizas", "rows": rows, "details": details}