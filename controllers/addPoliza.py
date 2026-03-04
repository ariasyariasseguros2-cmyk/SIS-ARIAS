
from models.db import get_connection
import mysql.connector
from flask import session

def cia_to_col(cia_txt: str | None) -> str | None:
    if not cia_txt:
        return None
    s = (str(cia_txt) or '').strip().lower()
    if 'mapfre' in s:
        return 'mapfre'
    if 'pacif' in s:
        return 'pacifico'
    if 'sanitas' in s:
        return 'sanitas'
    if 'protecta' in s:
        return 'protecta'
    if 'crecer' in s:
        return 'crecer'
    if 'positiva' in s:
        if 'eps' in s:
            return 'pos_eps'
        if 'vida' in s:
            return 'pos_vsr'
        return 'pos_sr'
    if 'ohio' in s:
        return 'ohio_natural'
    return None

def lookup_commission_pct(cnx_, cia_txt: str | None, candidates: list[str]) -> float | None:
    col = cia_to_col(cia_txt)
    try:
        s = (str(cia_txt) or '').strip().lower()
        is_lpv = ('lpv' in s) or ('positiva' in s) or ('la positiva' in s)
        if is_lpv:
            for cand in (candidates or []):
                v = (str(cand) or '').strip().lower()
                if not v:
                    continue
                if ('salud' in v) or ('eps' in v):
                    col = 'pos_eps'
                    break
                if 'vida' in v:
                    col = 'pos_vsr'
                    break
                if 'pens' in v:
                    col = 'pos_sr'
                    break
        # Si no hay columna determinada aún y el texto de la cia trae pistas
        if not col and s:
            if 'mapfre' in s:
                col = 'mapfre'
            elif 'pacif' in s:
                col = 'pacifico'
            elif 'sanitas' in s:
                col = 'sanitas'
            elif 'protecta' in s:
                col = 'protecta'
            elif 'crecer' in s:
                col = 'crecer'
            elif 'ohio' in s:
                col = 'ohio_natural'
    except Exception:
        pass
    if not col:
        return None
    try:
        cdict = cnx_.cursor(dictionary=True)
        for cand in candidates:
            if not cand:
                continue
            val = (str(cand) or '').strip().upper()
            if not val:
                continue
            cdict.execute(
                """
                SELECT 
                  pos_eps, pos_vsr, pos_sr, pacifico, sanitas, protecta, mapfre, crecer, ohio_natural, factor
                FROM comisiones_temp
                WHERE UPPER(producto_abrev) = %s
                   OR UPPER(producto) = %s
                   OR UPPER(ramo_abreviacion) = %s
                   OR UPPER(ramo_nombre) = %s
                LIMIT 1
                """,
                (val, val, val, val)
            )
            rowc = cdict.fetchone()
            if rowc:
                pct = rowc.get(col)
                if pct is not None:
                    try:
                        return float(pct)
                    except Exception:
                        pass
                # Fallback: usar factor general si existe
                fac = rowc.get('factor')
                if fac is not None:
                    try:
                        return float(fac)
                    except Exception:
                        pass
        cdict.close()
    except Exception:
        try:
            cdict.close()
        except Exception:
            pass
        return None
    return None

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

        # Fallback: obtener ejecutivo por usuario actual (mapeado en usuarios.id_ejecutivo)
        default_ejecutivo = None
        try:
            if session.get('user'):
                c2 = cnx.cursor()
                c2.execute("""
                    SELECT e.nombre
                    FROM usuarios u
                    LEFT JOIN ejecutivos e ON e.idEjecutivo = u.id_ejecutivo
                    WHERE u.username = %s
                    LIMIT 1
                """, (session.get('user'),))
                r2 = c2.fetchone()
                if r2 and r2[0]:
                    default_ejecutivo = r2[0]
                c2.close()
        except Exception:
            default_ejecutivo = None

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
                            f"La proforma/cupón corresponde al cliente dni/ruc {found_row_doc}, estás intentando guardarlo en la cuenta de dni/ruc {numero_documento}. Verifica el archivo o cambia de cliente."
                        ]
                    }
                
                target_doc = found_row_doc

            # AUTOCOMPLETAR % COMISIÓN COMPAÑÍA DESDE comisiones_temp (por compañía + producto/ramo)
            try:
                cia_txt = row.get("cia") or (selected or {}).get("cia") or (selected or {}).get("issuer") or ''
                prod_candidates = [
                    row.get("producto"),
                    row.get("ramos_producto"),
                    row.get("ramo"),
                ]
                auto_pct = None
                # Solo intentar si el usuario no ingresó %
                if not parse_decimal(row.get("comision_compania_pct")):
                    auto_pct = lookup_commission_pct(cnx, cia_txt, prod_candidates)
                    if auto_pct is not None:
                        row["comision_compania_pct"] = auto_pct
                        # Calcular importe si hay prima neta
                        pn = parse_decimal(row.get("prima_neta"))
                        if pn is not None:
                            try:
                                row["comision_compania_importe"] = round(pn * (auto_pct / 100.0), 2)
                            except Exception:
                                pass
            except Exception as _e:
                # Falla silenciosa: no bloquear guardado si no se puede autocompletar
                pass

            # Determinar ejecutivo efectivo: fila -> seleccionado -> fallback por usuario
            efectivo_ejecutivo = U(row.get("ejecutivo") or (selected or {}).get("ejecutivo") or default_ejecutivo or "")

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
                U((selected or {}).get("tipo_vigencia") or ""),  # NUEVO
                U((selected or {}).get("endosatario") or ""),    # NUEVO
                U(row.get("forma_pago") or ""),
                U(row.get("subagente") or (selected or {}).get("subagente") or ""),
                # NUEVO: ejecutivo (con fallback por usuario)
                efectivo_ejecutivo,
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
                f"uploads/polizas/{(selected or {}).get('pdf_filename')}" if (selected or {}).get("pdf_filename") else None,
                session.get('user')
            )

            try:
                cur.execute(
                    "CALL sp_insert_poliza_por_numero("
                    "%s,%s,%s,%s,%s,"        # doc, tipo_doc, asegurado, cia, ramo
                    "%s,%s,%s,%s,"          # poliza, recibo, contrato_nro, nro
                    "%s,%s,%s,%s,%s,%s,%s,%s,%s," # moneda, fecha_emision, vig_desde, vig_hasta, ultimo_dia_pago, fecha_vencimiento, tipo_vigencia, endosatario, forma_pago
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

                # INSERTAR CUOTA AUTOMÁTICA
                try:
                    c_poliza = U(row.get("numero_poliza") or "")
                    c_cupon = U(row.get("recibo") or "")
                    # Prioridad: fecha_vencimiento (pago) > vencimiento (vigencia fin) > inicio_vigencia
                    c_fec_venc = parse_date(row.get("fecha_vencimiento"))
                    if not c_fec_venc:
                        c_fec_venc = parse_date(row.get("vencimiento"))
                    
                    c_moneda = U(row.get("moneda") or "SOLES")
                    c_importe = parse_decimal(row.get("prima_comercial_igv"))
                    if c_importe is None:
                         c_importe = parse_decimal(row.get("prima_total"))

                    # Solo insertar si tenemos los datos mínimos requeridos por la tabla cuotas (NOT NULL)
                    if c_poliza and c_fec_venc and c_importe is not None:
                        cur.execute(
                            "CALL sp_insert_cuota(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                            (
                                c_poliza,
                                c_cupon,
                                c_fec_venc,
                                c_moneda,
                                c_importe,
                                None,   # fecha_pago
                                None,   # factura
                                None, # observacion
                                session.get('user'),
                                1       # numero_cuota
                            )
                        )
                        while cur.nextset():
                            pass
                except Exception as ex_cuota:
                    print(f"[WARNING] No se pudo crear cuota automática: {ex_cuota}")
                    # No bloqueamos el flujo principal, pero lo logueamos
                    pass

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
