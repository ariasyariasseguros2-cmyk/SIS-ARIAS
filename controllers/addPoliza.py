
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

        # NUEVO: calcular Importe Comisión Compañía desde Prima Neta y % (soporta 1.1..100 como porcentaje)
        # Calcular Importe Comisión Compañía en backend (por si el front no lo envía)
        com_pct_str = it.get("comision_compania_pct")
        com_importe_calc = None
        try:
            if com_pct_str:
                pct_val = float(str(com_pct_str).replace(',', '.').replace(' ', ''))
                # Si el valor es <=1, se interpreta como ratio (p.ej. 0.185); si es >1, como porcentaje (p.ej. 18.5)
                ratio = pct_val if pct_val <= 1 else (pct_val / 100.0)
                neta_base_str = (prima_neta_calc if prima_neta_calc is not None else it.get("prima_neta"))
                neta_val = float(str(neta_base_str).replace(',', '.').replace(' ', '')) if neta_base_str else None
                if neta_val is not None:
                    com_importe_calc = f"{(neta_val * ratio):.2f}"
        except Exception:
            pass

        # NUEVO: calcular Importe Comisión Sub Agente desde Importe Cía y % Sub Agente
        sub_pct_str = it.get("comision_subagente_pct")
        sub_importe_calc = None
        try:
            if sub_pct_str:
                pct_val = float(str(sub_pct_str).replace(',', '.').replace(' ', ''))
                ratio = pct_val if pct_val <= 1 else (pct_val / 100.0)
                # base: importe compañía (calculado o enviado)
                base_comp_str = com_importe_calc if com_importe_calc is not None else it.get("comision_compania_importe")
                base_comp_val = float(str(base_comp_str).replace(',', '.').replace(' ', '')) if base_comp_str else None
                if base_comp_val is not None:
                    sub_importe_calc = f"{(base_comp_val * ratio):.2f}"
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
            "motivo": it.get("motivo"),                      # NUEVO
            "ramos_producto": it.get("ramos_producto"),      # NUEVO
            "comision_compania_pct": it.get("comision_compania_pct"),
            "comision_compania_importe": com_importe_calc if com_importe_calc is not None else it.get("comision_compania_importe"),
            "comision_subagente_pct": it.get("comision_subagente_pct"),
            "comision_subagente_importe": sub_importe_calc if sub_importe_calc is not None else it.get("comision_subagente_importe"),
            # cliente seleccionado
            "cliente": (selected or {}).get("razon_social") or (selected or {}).get("nombre"),
            "n_doc": (selected or {}).get("n_doc"),
            "subagente": (selected or {}).get("subagente"),
            "tipo_doc": (selected or {}).get("tipo_doc"),  # NUEVO (opcional)
        })
    # Devuelve conteo para confirmar guardado
    return {"ok": True, "count": len(normalized)}