
from models.db import get_connection, get_encrypt_key
import mysql.connector
from flask import session, current_app
from werkzeug.utils import secure_filename
import os
import time
from datetime import datetime

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

def save_polizas(items: list, selected: dict | None = None, anexos: list = None, facturas: list = None, facturas_by_index: dict | None = None) -> dict:
    # Insertar en BD usando SP
    saved_anexos = []
    saved_facturas = []
    saved_facturas_by_index = {}
    if anexos:
        try:
            upload_folder = os.path.join(current_app.root_path, 'uploads', 'polizas')
            os.makedirs(upload_folder, exist_ok=True)
            for file in anexos:
                if file and file.filename:
                    original_name = file.filename
                    safe_name = secure_filename(original_name)
                    ts = int(time.time())
                    disk_name = f"{ts}_{safe_name}"
                    save_path = os.path.join(upload_folder, disk_name)
                    file.save(save_path)
                    saved_anexos.append({
                        'ruta': f"polizas/{disk_name}",
                        'nombre': original_name
                    })
        except Exception as e:
            print(f"[save_polizas] Error saving anexos: {e}")
    if facturas:
        try:
            upload_folder = os.path.join(current_app.root_path, 'uploads', 'cuotas')
            os.makedirs(upload_folder, exist_ok=True)
            for file in facturas:
                if file and file.filename:
                    original_name = file.filename
                    safe_name = secure_filename(original_name)
                    ts = int(time.time())
                    disk_name = f"{ts}_{safe_name}"
                    save_path = os.path.join(upload_folder, disk_name)
                    file.save(save_path)
                    saved_facturas.append({
                        'ruta': f"cuotas/{disk_name}",
                        'nombre': original_name
                    })
        except Exception as e:
            print(f"[save_polizas] Error saving facturas: {e}")
    if facturas_by_index:
        try:
            upload_folder = os.path.join(current_app.root_path, 'uploads', 'cuotas')
            os.makedirs(upload_folder, exist_ok=True)
            for k, files in facturas_by_index.items():
                arr = []
                for file in (files or []):
                    if file and file.filename:
                        original_name = file.filename
                        safe_name = secure_filename(original_name)
                        ts = int(time.time())
                        disk_name = f"{ts}_{safe_name}"
                        save_path = os.path.join(upload_folder, disk_name)
                        file.save(save_path)
                        arr.append({
                            'ruta': f"cuotas/{disk_name}",
                            'nombre': original_name
                        })
                if arr:
                    try:
                        idx_int = int(k)
                        saved_facturas_by_index[idx_int] = arr
                    except Exception:
                        pass
        except Exception as e:
            print(f"[save_polizas] Error saving facturas_by_index: {e}")

    try:
        if items:
            print(f"[DEBUG] save_polizas items[0]: {items[0]}")
        
        if selected:
            print(f"[DEBUG] save_polizas selected: {selected}")
            print(f"[DEBUG] pdf_filename in selected: {selected.get('pdf_filename')}")

        def parse_date(s: str | None) -> str | None:
            if not s:
                return None
            t = str(s).strip()
            if not t:
                return None
            t = t.replace('-', '/')
            # dd/mm/yyyy
            try:
                parts = t.split('/')
                if len(parts) == 3:
                    d, m, y = parts
                    d = int(str(d).strip())
                    m = int(str(m).strip())
                    y = int(str(y).strip())
                    dt = datetime(y, m, d)
                    return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
            # yyyy/mm/dd
            try:
                parts = t.split('/')
                if len(parts) == 3:
                    y, m, d = parts
                    y = int(str(y).strip())
                    m = int(str(m).strip())
                    d = int(str(d).strip())
                    dt = datetime(y, m, d)
                    return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
            return None

        def parse_decimal(s: str | float | int | None) -> float | None:
            if s is None or s == '':
                return None
            try:
                txt = str(s).strip()
                # Conservar solo dígitos, separadores y signo
                raw = ''.join(ch for ch in txt if (ch.isdigit() or ch in '.,-'))
                if not raw or raw in {'-', '.', ',', '-.', '-,'}:
                    return None
                # Determinar separador decimal por la última aparición de '.' o ','
                last_dot = raw.rfind('.')
                last_comma = raw.rfind(',')
                if last_dot == -1 and last_comma == -1:
                    # Solo dígitos (posible signo)
                    return float(raw)
                # Elegir el separador decimal como el que aparece más a la derecha
                if last_dot > last_comma:
                    # '.' es decimal; eliminar comas (miles)
                    cleaned = raw.replace(',', '')
                elif last_comma > last_dot:
                    # ',' es decimal; eliminar puntos (miles) y cambiar ',' por '.'
                    cleaned = raw.replace('.', '').replace(',', '.')
                else:
                    # Empate extraño; fallback: eliminar todos los separadores menos el último y usar '.'
                    sep_idx = max(last_dot, last_comma)
                    int_part = ''.join(ch for ch in raw[:sep_idx] if (ch.isdigit() or ch == '-'))
                    dec_part = ''.join(ch for ch in raw[sep_idx+1:] if ch.isdigit())
                    cleaned = f"{int_part}.{dec_part}" if dec_part else int_part
                # Si por algún motivo quedaron múltiples puntos, conservar el último como decimal
                if cleaned.count('.') > 1:
                    # Tomar signo si existe
                    sign = ''
                    if cleaned.startswith('-'):
                        sign = '-'
                        cleaned = cleaned[1:]
                    parts = cleaned.split('.')
                    int_part = ''.join(parts[:-1]).replace('.', '').replace(',', '')
                    dec_part = parts[-1]
                    cleaned = f"{sign}{int_part}.{dec_part}" if dec_part else f"{sign}{int_part}"
                return float(cleaned)
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
                    WHERE u.username COLLATE utf8mb4_0900_ai_ci = CAST(%s AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_ai_ci
                    LIMIT 1
                """, (session.get('user'),))
                r2 = c2.fetchone()
                if r2 and r2[0]:
                    default_ejecutivo = r2[0]
                c2.close()
        except Exception:
            default_ejecutivo = None

        usuario_display = session.get('user')
        try:
            if session.get('user'):
                c3 = cnx.cursor()
                c3.execute(
                    "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username COLLATE utf8mb4_0900_ai_ci = CAST(%s AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_ai_ci LIMIT 1",
                    (session.get('user'),),
                )
                r3 = c3.fetchone()
                if r3 and r3[0]:
                    usuario_display = r3[0]
                c3.close()
        except Exception:
            usuario_display = session.get('user')

        def find_client_doc(doc, name, cursor):
            # Prioridad: documento
            if doc:
                k = get_encrypt_key()
                cursor.execute("""
                    SELECT 
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                            CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                            numero_documento
                        ) AS n
                    FROM clientes 
                    WHERE 
                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR) = %s
                        OR CAST(AES_DECRYPT(numero_documento, %s) AS CHAR) = %s
                        OR numero_documento = %s
                    LIMIT 1
                """, (k, k, k, doc, k, doc, doc))
                res = cursor.fetchone()
                if res: return res[0]
            # Fallback: nombre (razon_social)
            if name:
                k = get_encrypt_key()
                cursor.execute("""
                    SELECT 
                        COALESCE(
                            CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR),
                            CAST(AES_DECRYPT(numero_documento, %s) AS CHAR),
                            numero_documento
                        ) AS n
                    FROM clientes 
                    WHERE 
                        CAST(AES_DECRYPT(FROM_BASE64(razon_social), %s) AS CHAR) = %s
                        OR CAST(AES_DECRYPT(razon_social, %s) AS CHAR) = %s
                        OR razon_social = %s
                    LIMIT 1
                """, (k, k, k, name, k, name, name))
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

        errors: list[str] = []
        for idx, row in enumerate(normalized, start=1):
            # Validaciones de fecha: si hay valor y no parsea, es error
            for f in ("fecha_emision", "inicio_vigencia", "vencimiento", "ultimo_dia_pago", "fecha_vencimiento"):
                val = row.get(f)
                if val:
                    if parse_date(val) is None:
                        errors.append(f"Fila {idx}: '{f}' inválida. Formato esperado DD/MM/AAAA.")
            # Validaciones numéricas: si hay valor y no parsea, es error
            for f in ("prima_comercial", "prima_neta", "prima_comercial_igv", "prima_total",
                      "comision_compania_pct", "comision_compania_importe",
                      "comision_subagente_pct", "comision_subagente_importe"):
                val = row.get(f)
                if val not in (None, '') and parse_decimal(val) is None:
                    errors.append(f"Fila {idx}: '{f}' debe ser numérico.")
        if errors:
            try:
                cur.close()
                cnx.close()
            except Exception:
                pass
            return {"ok": False, "errors": errors}

        for i, row in enumerate(normalized):
            real_poliza_id = None
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
                f"polizas/{(selected or {}).get('pdf_filename')}" if (selected or {}).get("pdf_filename") else None,
                usuario_display
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
                try:
                    cur.execute("SELECT LAST_INSERT_ID()")
                    lid_row_any = cur.fetchone()
                    lid_any = lid_row_any[0] if lid_row_any else 0
                    if args[32]:
                        cur.execute("SELECT poliza_id FROM poliza_archivos WHERE idArchivo = %s", (lid_any,))
                        pid_row_any = cur.fetchone()
                        if pid_row_any:
                            real_poliza_id = pid_row_any[0]
                    else:
                        real_poliza_id = lid_any
                except Exception:
                    real_poliza_id = None

                # Encriptar campos sensibles de la póliza recién creada (asegurado, poliza, recibo, contrato_nro, nro)
                try:
                    if real_poliza_id:
                        enc_asegurado = U(row.get("colectivo_asegurado") or row.get("asegurado") or "")
                        enc_poliza = U(row.get("numero_poliza") or "")
                        enc_recibo = U(row.get("recibo") or "")
                        enc_contrato_nro = U(row.get("contrato_nro") or row.get("recibo") or "")
                        enc_nro = U(row.get("nro") or "")
                        k_enc = get_encrypt_key()
                        c_enc = cnx.cursor()
                        c_enc.execute("""
                            UPDATE polizas SET
                              asegurado = CASE WHEN %s IS NULL THEN asegurado ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END,
                              poliza = CASE WHEN %s IS NULL THEN poliza ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END,
                              recibo = CASE WHEN %s IS NULL THEN recibo ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END,
                              contrato_nro = CASE WHEN %s IS NULL THEN contrato_nro ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END,
                              nro = CASE WHEN %s IS NULL THEN nro ELSE TO_BASE64(AES_ENCRYPT(%s, %s)) END
                            WHERE idPoliza = %s
                        """, (
                            enc_asegurado, enc_asegurado, k_enc,
                            enc_poliza, enc_poliza, k_enc,
                            enc_recibo, enc_recibo, k_enc,
                            enc_contrato_nro, enc_contrato_nro, k_enc,
                            enc_nro, enc_nro, k_enc,
                            real_poliza_id,
                        ))
                        c_enc.close()
                except Exception as _e_enc:
                    print(f"[save_polizas] Error encrypting new poliza {real_poliza_id}: {_e_enc}")

                # NUEVO: Vincular Anexos
                if saved_anexos:
                    try:
                        if real_poliza_id:
                            for sa in saved_anexos:
                                cur.execute("""
                                    INSERT INTO poliza_archivos 
                                    (poliza_id, numero_poliza, ruta_archivo, nombre_original, ramo, producto, usuario, compania, origen)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ANEXO')
                                """, (
                                    real_poliza_id, 
                                    row.get('poliza') or row.get('numero_poliza') or "", 
                                    sa['ruta'], 
                                    sa['nombre'], 
                                    row.get('ramo') or "", 
                                    row.get('ramos_producto') or "", 
                                    usuario_display, 
                                    row.get('cia') or ""
                                ))
                    except Exception as e_anexos:
                        print(f"[save_polizas] Error linking anexos: {e_anexos}")

                # INSERTAR CUOTA AUTOMÁTICA
                try:
                    c_poliza = U(row.get("numero_poliza") or "")
                    c_cupon = U(row.get("recibo") or "")
                    c_fec_venc = (
                        parse_date(row.get("fecha_vencimiento")) or
                        parse_date(row.get("vencimiento")) or
                        parse_date((selected or {}).get("fecha_vencimiento")) or
                        parse_date((selected or {}).get("vencimiento")) or
                        parse_date((selected or {}).get("vig_hasta")) or
                        datetime.today().strftime('%Y-%m-%d')
                    )
                    c_moneda = U(row.get("moneda") or "S/.")
                    c_importe = parse_decimal(row.get("prima_comercial_igv"))
                    if c_importe is None:
                         c_importe = parse_decimal(row.get("prima_total"))
                    if c_importe is None:
                         c_importe = 0.0
                    c_fecha_pago = parse_date(row.get("fecha_pago"))
                    c_factura = U(row.get("factura") or "")
                    if not c_poliza and real_poliza_id:
                        try:
                            cur.execute(
                                """
                                SELECT 
                                    COALESCE(CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                                             CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                                             poliza) AS pval,
                                    COALESCE(CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR),
                                             CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR),
                                             recibo) AS rval,
                                    DATE_FORMAT(vig_hasta, '%Y-%m-%d') AS fh
                                FROM polizas
                                WHERE idPoliza = %s
                                """,
                                (real_poliza_id,)
                            )
                            rp = cur.fetchone()
                            if rp:
                                c_poliza = U(rp[0] or "")
                                c_cupon = U((c_cupon or rp[1] or ""))
                                c_fec_venc = c_fec_venc or (rp[2] or datetime.today().strftime('%Y-%m-%d'))
                        except Exception:
                            pass
                    if c_poliza:
                        target_poliza_id = real_poliza_id
                        if not target_poliza_id:
                            try:
                                if c_cupon:
                                    cur.execute(
                                        """
                                        SELECT idPoliza
                                        FROM polizas
                                        WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                                          AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) USING utf8mb4), recibo) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                                        ORDER BY creado_en DESC
                                        LIMIT 1
                                        """,
                                        (c_poliza, c_cupon),
                                    )
                                else:
                                    cur.execute(
                                        """
                                        SELECT idPoliza
                                        FROM polizas
                                        WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                                        ORDER BY creado_en DESC
                                        LIMIT 1
                                        """,
                                        (c_poliza,),
                                    )
                                rpid = cur.fetchone()
                                if rpid:
                                    target_poliza_id = rpid[0]
                            except Exception:
                                target_poliza_id = None

                        if target_poliza_id:
                            cur.execute(
                                "SELECT IFNULL(MAX(numero_cuota), 0) + 1 FROM cuotas WHERE poliza_id = %s",
                                (target_poliza_id,),
                            )
                        else:
                            cur.execute(
                                """
                                SELECT IFNULL(MAX(numero_cuota), 0) + 1 
                                FROM cuotas 
                                WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                                """,
                                (c_poliza,),
                            )
                        rnc = cur.fetchone()
                        numero_cuota = rnc[0] if rnc and rnc[0] is not None else 1

                        if c_factura:
                            cur.execute("SELECT 1 FROM cuotas WHERE factura = %s AND activo = 1 LIMIT 1", (c_factura,))
                            if cur.fetchone():
                                raise Exception("El número de factura ya existe.")
                        if c_cupon:
                            cur.execute(
                                """
                                SELECT 1 FROM cuotas 
                                WHERE TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), poliza) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                                  AND TRIM(COALESCE(CONVERT(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) USING utf8mb4), cupon) COLLATE utf8mb4_0900_ai_ci) = TRIM(CAST(%s AS CHAR) COLLATE utf8mb4_0900_ai_ci)
                                  AND activo = 1 
                                LIMIT 1
                                """,
                                (c_poliza, c_cupon),
                            )
                            if cur.fetchone():
                                pass

                        try:
                            cur.execute(
                                "CALL sp_insert_cuota(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                (
                                    c_poliza,
                                    c_cupon or None,
                                    c_fec_venc,
                                    c_moneda,
                                    c_importe,
                                    c_fecha_pago,
                                    c_factura or None,
                                    None,
                                    usuario_display,
                                    numero_cuota,
                                ),
                            )
                            while cur.nextset():
                                pass
                            cur.execute(
                                """
                                SELECT 1 FROM cuotas 
                                WHERE (poliza_id = %s OR TRIM(poliza)=TRIM(%s))
                                  AND numero_cuota = %s
                                  AND activo = 1
                                LIMIT 1
                                """,
                                (target_poliza_id, c_poliza, numero_cuota),
                            )
                            exists_row = cur.fetchone()
                            if not exists_row:
                                raise Exception("SP did not insert cuota")
                        except Exception as e_ins_cuota:
                            print(f"[WARNING] sp_insert_cuota failed: {e_ins_cuota}")
                            try:
                                cur.execute(
                                    """
                                    INSERT INTO cuotas (
                                        poliza_id,
                                        poliza,
                                        cupon,
                                        fecha_vencimiento,
                                        moneda,
                                        importe,
                                        fecha_pago,
                                        factura,
                                        observacion,
                                        usuario_registro,
                                        numero_cuota,
                                        activo
                                    ) VALUES (
                                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, 1
                                    )
                                    """,
                                    (
                                        target_poliza_id,
                                        c_poliza,
                                        c_cupon,
                                        c_fec_venc,
                                        c_moneda,
                                        c_importe,
                                        c_fecha_pago,
                                        c_factura,
                                        None,
                                        usuario_display,
                                        numero_cuota,
                                    ),
                                )
                                try:
                                    last_id = cur.lastrowid
                                    cur.execute(
                                        "UPDATE cuotas SET poliza = TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY)), cupon = TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY)) WHERE idCuota = %s",
                                        (c_poliza, c_cupon, last_id)
                                    )
                                except Exception:
                                    pass
                            except Exception as e_manual:
                                print(f"[ERROR] manual cuota insert failed: {e_manual}")

                        final_poliza_id = target_poliza_id
                        if final_poliza_id is not None:
                            cur.execute(
                                """
                                SELECT COUNT(*)
                                FROM cuotas
                                WHERE poliza_id = %s
                                  AND (
                                    fecha_pago IS NULL
                                    OR factura IS NULL OR factura = ''
                                  )
                                  AND activo = 1
                                """,
                                (final_poliza_id,),
                            )
                            row_p = cur.fetchone()
                            pendientes = row_p[0] if row_p and row_p[0] is not None else 0
                            nuevo_estado = 'PENDIENTE' if pendientes > 0 else 'CANCELADO'
                            try:
                                tdoc_sel = (((selected or {}).get("tipo_doc") or (selected or {}).get("tipo_documento") or "")).strip().upper()
                            except Exception:
                                tdoc_sel = ""
                            est_row = (U(row.get("estado") or "") or "")
                            forma_pago_row = (U(row.get("forma_pago") or "") or "")
                            if tdoc_sel == 'NETEO' or est_row == 'SIN PRIMA' or forma_pago_row == 'SIN PRIMA':
                                nuevo_estado = 'SIN PRIMA'
                            cur.execute("UPDATE polizas SET estado = %s WHERE idPoliza = %s", (nuevo_estado, final_poliza_id))
                except Exception as ex_cuota:
                    print(f"[WARNING] No se pudo crear cuota automática: {ex_cuota}")
                    # No bloqueamos el flujo principal, pero lo logueamos
                    pass
                try:
                    files_for_row = saved_facturas_by_index.get(i, saved_facturas)
                    if files_for_row:
                        pid_for_files = real_poliza_id
                        if not pid_for_files:
                            try:
                                cur.execute(
                                    "SELECT idPoliza FROM polizas WHERE TRIM(poliza) COLLATE utf8mb4_0900_ai_ci = TRIM(CAST(%s AS CHAR CHARACTER SET utf8mb4)) COLLATE utf8mb4_0900_ai_ci ORDER BY creado_en DESC LIMIT 1",
                                    ((row.get('numero_poliza') or row.get('poliza') or ''),)
                                )
                                rpid = cur.fetchone()
                                if rpid:
                                    pid_for_files = rpid[0]
                            except Exception:
                                pid_for_files = None
                        if pid_for_files:
                            for sf in files_for_row:
                                nombre_doc = f"[CUOTA {U(row.get('recibo') or '')}] {sf['nombre']}".strip()
                                try:
                                    cur.execute(
                                        """INSERT INTO poliza_archivos
                                           (poliza_id, numero_poliza, ruta_archivo, nombre_original, origen, ramo, producto, usuario, compania)
                                           VALUES (%s,%s,%s,%s,'CUOTA',%s,%s,%s,%s)""",
                                        (
                                            pid_for_files,
                                            U(row.get('numero_poliza') or ''),
                                            sf['ruta'],
                                            nombre_doc or sf['nombre'],
                                            U(row.get('ramo') or ''),
                                            U(row.get('ramos_producto') or ''),
                                            usuario_display,
                                            U(row.get('cia') or '')
                                        )
                                    )
                                except Exception as ex_f:
                                    print(f"[save_polizas] Error linking factura archivo: {ex_f}")
                except Exception as _ex:
                    print(f"[save_polizas] Facturas vinculo error: {_ex}")

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
