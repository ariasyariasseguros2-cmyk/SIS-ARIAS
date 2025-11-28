
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
    normalized = []
    for it in items:
        # Calcular prima_neta = prima_comercial / 1.03 y +IGV = comercial*1.18
        prima_comercial_str = it.get("prima_comercial")
        prima_neta_str = it.get("prima_neta")
        prima_neta_calc = None
        prima_comercial_calc = None
        prima_comercial_igv_calc = None
        try:
            if prima_comercial_str:
                val = float(str(prima_comercial_str).replace(',', '.').replace(' ', ''))
                prima_neta_calc = f"{(val / 1.03):.2f}"
                prima_comercial_calc = f"{val:.2f}"
                prima_comercial_igv_calc = f"{(val * 1.18):.2f}"
            elif prima_neta_str:
                val = float(str(prima_neta_str).replace(',', '.').replace(' ', ''))
                prima_comercial_calc = f"{(val * 1.03):.2f}"
                prima_neta_calc = f"{val:.2f}"
                prima_comercial_igv_calc = f"{(float(prima_comercial_calc) * 1.18):.2f}"
        except Exception:
            pass

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
            "prima_comercial": prima_comercial_calc if prima_comercial_calc is not None else it.get("prima_comercial"),
            "prima_neta": prima_neta_calc if prima_neta_calc is not None else it.get("prima_neta"),
            "prima_total": it.get("prima_total"),
            "prima_comercial_igv": prima_comercial_igv_calc if prima_comercial_igv_calc is not None else it.get("prima_comercial_igv"),
            "estado": it.get("estado"),
            "comision_compania_pct": it.get("comision_compania_pct"),
            "comision_compania_importe": it.get("comision_compania_importe"),
            "comision_subagente_pct": it.get("comision_subagente_pct"),
            "comision_subagente_importe": it.get("comision_subagente_importe"),
            # cliente seleccionado
            "cliente": (selected or {}).get("razon_social") or (selected or {}).get("nombre"),
            "n_doc": (selected or {}).get("n_doc"),
            "subagente": (selected or {}).get("subagente"),
        })
    # Devuelve conteo para confirmar guardado
    return {"ok": True, "count": len(normalized)}