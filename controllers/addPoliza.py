
def get_rows():
    # Filas de ayuda para la vista (placeholder)
    return [
        {"label": "Sube tu PDF de la póliza y valida los campos"},
        {"label": "Se soporta La Positiva, MAPFRE; EPS/Vida/Seguros"},
    ]

def save_polizas(items: list, selected: dict | None = None) -> dict:
    # Insertar en BD usando SP
    try:
        if items:
            print(f"[DEBUG] save_polizas items[0]: {items[0]}")

        from models.db import get_connection
        import mysql.connector

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

        # Normalizador a MAYÚSCULAS para campos de texto
        def U(s):
            t = '' if s is None else str(s).strip()
            return t.upper() if t else ''

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
                # Completar asegurada si falta
                if not row.get("asegurada") and selected.get("asegurada"):
                    row["asegurada"] = selected["asegurada"]
                # Completar motivo si falta
                if not row.get("motivo") and selected.get("motivo"):
                    row["motivo"] = selected["motivo"]
                # SIEMPRE aplicar ramos_producto del bloque superior si existe
                if selected.get("ramos_producto"):
                    row["ramos_producto"] = selected["ramos_producto"]
                # Completar subagente si falta
                if not row.get("subagente") and selected.get("subagente"):
                    row["subagente"] = selected["subagente"]
                # NUEVO: completar ejecutivo si falta
                if not row.get("ejecutivo") and selected.get("ejecutivo"):
                    row["ejecutivo"] = selected["ejecutivo"]
            normalized.append(row)

        if not normalized:
            return {"ok": False, "errors": ["No hay pólizas para guardar."]}

        cnx = get_connection()
        cur = cnx.cursor()

        # Validar si el cliente existe
        cur.execute("SELECT idCliente FROM clientes WHERE numero_documento = %s LIMIT 1", (numero_documento,))
        if not cur.fetchone():
            cur.close()
            cnx.close()
            return {"ok": False, "errors": ["El cliente no existe debes registrar cliente nuevo"]}

        inserted = 0

        for row in normalized:
            # NUEVO: Si la fila tiene un documento extraído (RUC/DNI), validar que exista en BD
            # y usar ese documento para la inserción en lugar del seleccionado por defecto.
            row_doc = row.get("numero_documento_extracted")
            target_doc = numero_documento
            if row_doc:
                cur.execute("SELECT idCliente FROM clientes WHERE numero_documento = %s LIMIT 1", (row_doc,))
                if not cur.fetchone():
                    # Si el documento extraído del PDF no existe, bloquear TODO el proceso (o solo esta fila)
                    # Según requerimiento: "no deberia añadir la poliza debe decir el cliente no existe"
                    cur.close()
                    cnx.close()
                    return {"ok": False, "errors": [f"El cliente con documento {row_doc} (extraído del PDF) no existe. Debes registrar cliente nuevo."]}
                target_doc = row_doc

            args = (
                str(target_doc).strip(),  # documento (puede ser el extraído o el seleccionado)
                U((selected or {}).get("tipo_doc") or (selected or {}).get("tipo_documento") or ""),
                U(row.get("colectivo_asegurado") or row.get("asegurado") or ""),
                U(row.get("cia") or ""),
                U(row.get("ramo") or ""),

                U(row.get("numero_poliza") or ""),
                U(row.get("recibo") or ""),
                U(row.get("contrato_nro") or row.get("recibo") or ""),  # Fallback: contrato_nro = recibo
                U(row.get("nro") or ""),

                U(row.get("moneda") or ""),
                parse_date(row.get("fecha_emision")),
                parse_date(row.get("inicio_vigencia")),
                parse_date(row.get("vencimiento")),
                parse_date(row.get("ultimo_dia_pago")),
                parse_date(row.get("fecha_vencimiento")),  # NUEVO
                U(row.get("forma_pago") or ""),
                U(row.get("subagente") or (selected or {}).get("subagente") or ""),
                # NUEVO: ejecutivo
                U(row.get("ejecutivo") or (selected or {}).get("ejecutivo") or ""),
                U(row.get("asegurada") or ""),
                U(row.get("motivo") or (selected or {}).get("motivo") or ""),
                parse_decimal(row.get("prima_comercial")),
                parse_decimal(row.get("prima_neta")),
                parse_decimal(row.get("prima_comercial_igv")),
                parse_decimal(row.get("prima_total")),

                parse_decimal(row.get("comision_compania_pct")),
                parse_decimal(row.get("comision_compania_importe")),
                parse_decimal(row.get("comision_subagente_pct")),
                parse_decimal(row.get("comision_subagente_importe")),

                U(row.get("ramos_producto") or (selected or {}).get("ramos_producto") or ""),
                U(row.get("estado") or "PENDIENTE"),
            )

            try:
                cur.execute(
                    "CALL sp_insert_poliza_por_numero("
                    "%s,%s,%s,%s,%s,"        # doc, tipo_doc, asegurado, cia, ramo
                    "%s,%s,%s,%s,"          # poliza, recibo, contrato_nro, nro
                    "%s,%s,%s,%s,%s,%s,%s," # moneda, fecha_emision, vig_desde, vig_hasta, ultimo_dia_pago, fecha_vencimiento, forma_pago
                    "%s,%s,"                # sub_agente, ejecutivo
                    "%s,%s,%s,%s,%s,%s,"    # asegurada, motivo, prima_comercial, prima_neta, prima_comercial_igv, prima_total
                    "%s,%s,%s,%s,"          # porc_compania, imp_compania, porc_subagente, imp_subagente
                    "%s,%s"                 # ramos_producto, estado
                    ")",
                    args
                )
                while cur.nextset():
                    pass
                inserted += 1
            except mysql.connector.Error as err:
                # Detecta SIGNAL SQLSTATE '45000' del SP (duplicado / cliente no existe)
                if getattr(err, 'sqlstate', '') == '45000':
                    try:
                        cnx.rollback()
                    except Exception:
                        pass
                    try:
                        cur.close()
                    except Exception:
                        pass
                    try:
                        cnx.close()
                    except Exception:
                        pass
                    # Devuelve el mensaje claro del SP
                    return {"ok": False, "errors": [str(getattr(err, 'msg', err))]}
                # Otros errores → deja que los maneje el except general
                raise

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