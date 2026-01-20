
from models.db import get_connection
import mysql.connector
from flask import session

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
        
        if selected:
            print(f"[DEBUG] save_polizas selected: {selected}")
            print(f"[DEBUG] pdf_filename in selected: {selected.get('pdf_filename')}")

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

        # VALIDACIÓN: cliente seleccionado (numero_documento o nombre)
        numero_documento = (selected or {}).get("n_doc") or (selected or {}).get("numero_documento") or ""
        razon_social_selected = (selected or {}).get("razon_social") or (selected or {}).get("contratante") or ""
        
        if not numero_documento and not razon_social_selected:
            return {"ok": False, "errors": ["Falta seleccionar cliente (documento o nombre)."]}

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

        def find_client_doc(doc, name, cursor):
            # Prioridad: documento
            if doc:
                cursor.execute("SELECT numero_documento FROM clientes WHERE numero_documento = %s LIMIT 1", (doc,))
                res = cursor.fetchone()
                if res: return res[0]
            # Fallback: nombre (razon_social)
            if name:
                cursor.execute("SELECT numero_documento FROM clientes WHERE razon_social = %s LIMIT 1", (name,))
                res = cursor.fetchone()
                if res: return res[0]
            return None

        # Validar si el cliente existe (por documento o nombre)
        found_doc = find_client_doc(numero_documento, razon_social_selected, cur)
        if not found_doc:
            cur.close()
            cnx.close()
            return {"ok": False, "errors": ["El cliente no existe (ni por documento ni por nombre), debes registrar cliente nuevo"]}
        
        # Actualizar numero_documento con el encontrado (para usarlo como default)
        numero_documento = found_doc

        inserted = 0

        for row in normalized:
            # NUEVO: Validar cliente de la fila (por documento o nombre)
            row_doc = row.get("numero_documento_extracted")
            row_name = row.get("contratante") or row.get("razon_social")
            
            target_doc = numero_documento # Default: el seleccionado globalmente
            
            if row_doc or row_name:
                found_row_doc = find_client_doc(row_doc, row_name, cur)
                if not found_row_doc:
                    cur.close()
                    cnx.close()
                    err_ident = row_doc or row_name
                    return {"ok": False, "errors": [f"El cliente '{err_ident}' (extraído del PDF) no existe. Debes registrar cliente nuevo."]}
                
                # VALIDACIÓN ADICIONAL: Si se seleccionó un cliente explícito y el PDF trae otro, RECHAZAR.
                # numero_documento viene del 'selected' global. found_row_doc es lo que hallamos en la BD para el PDF.
                if numero_documento and found_row_doc != numero_documento:
                    cur.close()
                    cnx.close()
                    return {
                        "ok": False, 
                        "errors": [
                            f"El PDF corresponde al cliente {found_row_doc}, pero estás intentando guardarlo en la cuenta de {numero_documento}. Verifica el archivo o cambia de cliente."
                        ]
                    }
                
                target_doc = found_row_doc

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
                f"uploads/{(selected or {}).get('pdf_filename')}" if (selected or {}).get("pdf_filename") else None,
                session.get('user')
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
                    "%s,%s,%s,%s"           # ramos_producto, estado, pdf_path, usuario_registro
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