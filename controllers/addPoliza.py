
def get_rows():
    # Filas de ayuda para la vista (placeholder)
    return [
        {"label": "Sube tu PDF de la póliza y valida los campos"},
        {"label": "Se soporta La Positiva, MAPFRE; EPS/Vida/Seguros"},
    ]

def save_polizas(items: list, selected: dict | None = None) -> dict:
    # Insertar en BD usando SP
    try:
        from models.db import get_connection

        def parse_date(s: str | None) -> str | None:
            if not s:
                return None
            t = str(s).strip().replace('-', '/')
            parts = t.split('/')
            if len(parts) == 3:
                # dd/mm/yyyy → yyyy-mm-dd
                d, m, y = parts
                return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            # yyyy-mm-dd o yyyy/mm/dd → normalize
            parts = t.split('/')
            if len(parts) == 3:
                y, m, d = parts
                return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            return None

        def parse_decimal(s: str | float | int | None) -> float | None:
            if s is None or s == '':
                return None
            try:
                return float(str(s).replace(',', '.').replace(' ', ''))
            except Exception:
                return None

        # VALIDACIÓN: cliente seleccionado (numero_documento)
        numero_documento = (selected or {}).get("n_doc") or (selected or {}).get("numero_documento") or ""
        if not numero_documento:
            return {"ok": False, "errors": ["Falta seleccionar cliente (documento)."]}

        # FIX: construir 'normalized' desde 'items' y completar campos globales
        normalized: list[dict] = []
        for it in (items or []):
            row = dict(it or {})
            # Completar desde el bloque superior si falta en la fila
            if selected:
                # Mapear Motivo al campo 'asegurada' si 'asegurada' está vacío
                if not row.get("asegurada") and selected.get("motivo"):
                    row["asegurada"] = selected["motivo"]
                if not row.get("ramos_producto") and selected.get("ramos_producto"):
                    row["ramos_producto"] = selected["ramos_producto"]
                if not row.get("subagente") and selected.get("subagente"):
                    row["subagente"] = selected["subagente"]
            normalized.append(row)

        if not normalized:
            return {"ok": False, "errors": ["No hay pólizas para guardar."]}

        cnx = get_connection()
        cur = cnx.cursor()

        inserted = 0

        for row in normalized:
            args = (
                numero_documento,
                row.get("colectivo_asegurado") or row.get("asegurado") or "",
                row.get("cia") or "",

                row.get("ramo") or "",

                row.get("numero_poliza") or "",
                row.get("recibo") or "",
                row.get("contrato_nro") or "",
                row.get("nro") or "",

                row.get("moneda") or "",
                parse_date(row.get("fecha_emision")),
                parse_date(row.get("inicio_vigencia")),
                parse_date(row.get("vencimiento")),
                parse_date(row.get("ultimo_dia_pago")),
                row.get("forma_pago") or "",

                row.get("subagente") or (selected or {}).get("subagente") or "",

                row.get("asegurada") or "",
                parse_decimal(row.get("prima_comercial")),
                parse_decimal(row.get("prima_neta")),
                parse_decimal(row.get("prima_comercial_igv")),
                parse_decimal(row.get("prima_total")),

                parse_decimal(row.get("comision_compania_pct")),
                parse_decimal(row.get("comision_compania_importe")),
                parse_decimal(row.get("comision_subagente_pct")),
                parse_decimal(row.get("comision_subagente_importe")),

                row.get("ramos_producto") or (selected or {}).get("ramos_producto") or "",
                # Quitado: motivo (se guarda en 'asegurada' según tu requerimiento)
                row.get("estado") or "PENDIENTE",
            )

            cur.execute(
                "CALL sp_insert_poliza_por_numero("
                "%s,%s,%s,%s,"          # doc, asegurado, cia, ramo
                "%s,%s,%s,%s,"          # poliza, recibo, contrato_nro, nro
                "%s,%s,%s,%s,%s,%s,"    # moneda, fecha_emision, vig_desde, vig_hasta, ultimo_dia_pago, forma_pago
                "%s,"                   # sub_agente
                "%s,%s,%s,%s,%s,"       # asegurada, prima_comercial, prima_neta, prima_comercial_igv, prima_total
                "%s,%s,%s,%s,"          # porc_compania, imp_compania, porc_subagente, imp_subagente
                "%s,%s"                 # ramos_producto, estado
                ")",
                args
            )

            while True:
                if not cur.nextset():
                    break

            inserted += 1

        cnx.commit()
        cur.close()
        cnx.close()

        return {"ok": True, "count": inserted}
    except Exception as e:
        # Responder con detalle del error y asegurar cierre/rollback
        try:
            cur.close()
        except Exception:
            pass
        try:
            cnx.rollback()
        except Exception:
            pass
        try:
            cnx.close()
        except Exception:
            pass
        return {"ok": False, "errors": [str(e)]}