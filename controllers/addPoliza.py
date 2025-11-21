addpoliza.py

def get_rows():
    # Filas de ayuda para la vista (placeholder)
    return [
        {"label": "Sube tu PDF de la póliza y valida los campos"},
        {"label": "Se soporta La Positiva, MAPFRE; EPS/Vida/Seguros"},
    ]

def save_polizas(items: list, selected: dict | None = None) -> dict:
    # Aquí deberías insertar a DB. Por ahora validamos y devolvemos OK.
    if not items:
        return {"ok": False, "errors": ["No hay items para guardar."]}
    # Ejemplo de normalización básica
    normalized = []  # <- faltaba esta línea
    for it in items:
        normalized.append({
            "numero_poliza": it.get("numero_poliza"),
            "recibo": it.get("recibo"),
            "colectivo_asegurado": it.get("colectivo_asegurado"),
            "inicio_vigencia": it.get("inicio_vigencia"),
            "vencimiento": it.get("vencimiento"),
            "moneda": it.get("moneda"),
            "fecha_emision": it.get("fecha_emision"),
            "forma_pago": it.get("forma_pago"),
            "ultimo_dia_pago": it.get("ultimo_dia_pago"),
            "ramo": it.get("ramo"),
            "prima_comercial": it.get("prima_comercial"),
            "prima_neta": it.get("prima_neta"),
            "prima_total": it.get("prima_total"),
            "prima_comercial_igv": it.get("prima_comercial_igv"),
            "cliente": (selected or {}).get("razon_social") or (selected or {}).get("nombre"),
            "n_doc": (selected or {}).get("n_doc"),
            "subagente": (selected or {}).get("subagente"),
        })
    # Devuelve conteo para confirmar guardado
    return {"ok": True, "count": len(normalized)}