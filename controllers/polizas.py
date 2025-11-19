def get_polizas_data():
    # Dataset de ejemplo; integra BD cuando esté disponible
    rows = [
        {
            "poliza": "P-000001",
            "ramo": "SCTR Salud",
            "contratante": "Empresa X SAC",
            "vigencia_desde": "01/01/2025",
            "vigencia_hasta": "31/12/2025",
            "moneda": "PEN",
            "prima_total": "1,500.00"
        }
    ]
    return {"title": "Pólizas", "rows": rows}