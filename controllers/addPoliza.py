
from models.db import get_connection, get_encrypt_key
import mysql.connector
from flask import session, current_app
from werkzeug.utils import secure_filename
import os
import time
import re
from datetime import datetime
import unicodedata

def cia_to_col(cia_txt: str | None) -> str | None:
    if not cia_txt:
        return None
    s = (str(cia_txt) or '').strip().lower()
    if 'grandia' in s:
        return 'grandia_eps'
    if 'mapfre' in s:
        return 'mapfre'
    if 'pacif' in s:
        return 'pacifico'
    if 'sanitas' in s:
        return 'sanitas'
    if 'protecta' in s or 'proctecta' in s:
        return 'protecta'
    if 'crecer' in s:
        return 'crecer'
    if ('positiva' in s) or ('lpv' in s) or ('lpv' in s) or ('lpeps' in s):
        if ('lpeps' in s) or ('eps' in s) or ('salud' in s):
            return 'pos_eps'
        if 'vida' in s:
            return 'pos_vsr'
        if ('pension' in s) or ('pensión' in s):
            return 'pos_sr'
        return 'pos_sr'
    if 'ohio' in s:
        return 'ohio_natural'
    return None

def normalize_tipo_vigencia(value: str | None) -> str:
    raw = (value or '').strip()
    if not raw:
        return ''
    try:
        upper = unicodedata.normalize('NFD', raw.upper())
        upper = ''.join(ch for ch in upper if unicodedata.category(ch) != 'Mn')
    except Exception:
        upper = raw.upper()
    upper = ' '.join(upper.split())
    if upper in {'MENSUAL', 'DECLARACION MENSUAL'}:
        return 'DECLARACION MENSUAL'
    if upper in {'TRIMESTRAL', 'PERIODICA', 'PERIÓDICA'}:
        return 'PERIODICA'
    if upper == 'ANUAL':
        return 'ANUAL'
    if upper in {'NO RENOVABLE', 'EVENTUAL', 'FLOTANTE'}:
        return upper
    return upper

def lookup_commission_pct(cnx_, cia_txt: str | None, candidates: list[str]) -> float | None:
    col = cia_to_col(cia_txt)
    try:
        s = (str(cia_txt) or '').strip().lower()
        is_lpv = ('lpv' in s) or ('lpv' in s) or ('lpeps' in s) or ('positiva' in s) or ('la positiva' in s)
        if is_lpv:
            if ('lpeps' in s) or ('eps' in s) or ('salud' in s):
                col = 'pos_eps'
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
            elif 'protecta' in s or 'proctecta' in s:
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
                    pos_eps, pos_vsr, pos_sr, pacifico, sanitas, protecta, mapfre, crecer, ohio_natural, grandia_eps, factor
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

def save_polizas(
    items: list,
    selected: dict | None = None,
    anexos: list = None,
    facturas: list = None,
    facturas_by_index: dict | None = None,
    facturas_by_cuota: dict | None = None,
) -> dict:
    # Insertar en BD usando SP
    saved_anexos = []
    saved_facturas = []
    saved_facturas_by_index = {}
    saved_facturas_by_cuota = {}
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
    if facturas_by_cuota:
        try:
            upload_folder = os.path.join(current_app.root_path, 'uploads', 'cuotas')
            os.makedirs(upload_folder, exist_ok=True)
            for row_idx, cuotas_files in (facturas_by_cuota or {}).items():
                row_map = {}
                for cuota_idx, files in (cuotas_files or {}).items():
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
                            row_map[int(cuota_idx)] = arr
                        except Exception:
                            pass
                if row_map:
                    try:
                        saved_facturas_by_cuota[int(row_idx)] = row_map
                    except Exception:
                        pass
        except Exception as e:
            print(f"[save_polizas] Error saving facturas_by_cuota: {e}")

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
                if not txt:
                    return None
                m = re.search(r'[-+]?\d[\d.,]*', txt)
                if not m:
                    return None
                raw = (m.group(0) or '').strip()
                if not raw:
                    return None
                if raw.startswith('+'):
                    raw = raw[1:]

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

        def normalize_dup_key(value: str | None) -> str | None:
            if value is None:
                return None
            try:
                t = str(value).replace('\u00A0', ' ').strip()
            except Exception:
                t = (value or '').strip() if isinstance(value, str) else None
            if not t:
                return None
            try:
                t = ' '.join(t.split())
            except Exception:
                pass
            return t

        # Normalizador a MAYÚSCULAS para campos de texto
        def U(s):
            t = '' if s is None else str(s).strip()
            return t.upper() if t else ''

        # VALIDACIÓN: cliente seleccionado (numero_documento o nombre)
        numero_documento = (selected or {}).get("n_doc") or (selected or {}).get("numero_documento") or ""
        razon_social_selected = (selected or {}).get("razon_social") or (selected or {}).get("contratante") or ""
        tipo_vigencia_selected = normalize_tipo_vigencia((selected or {}).get("tipo_vigencia") or "")
        if tipo_vigencia_selected and tipo_vigencia_selected not in {"ANUAL", "DECLARACION MENSUAL", "PERIODICA", "NO RENOVABLE", "EVENTUAL", "FLOTANTE"}:
            return {"ok": False, "errors": ["Tipo de vigencia inválido. Verifica el valor seleccionado."]}

        if not numero_documento and not razon_social_selected:
            return {"ok": False, "errors": ["Falta seleccionar cliente (documento o nombre)."]}

        # FIX: construir 'normalized' desde 'items' y completar campos globales
        normalized: list[dict] = []

        def _infer_lapositiva_cia(row: dict, selected_: dict | None) -> str | None:
            sel = selected_ or {}
            issuer = (row.get("issuer") or sel.get("issuer") or "").strip().lower()
            issuer_slug = (row.get("cia_value") or row.get("issuer") or sel.get("issuer") or "").strip().lower()
            cia_raw = (row.get("cia") or sel.get("cia") or "").strip().lower()
            is_lp = (
                ("lapositiva" in issuer)
                or ("lpv" in issuer_slug)
                or ("lpv" in issuer_slug)
                or ("lpeps" in issuer_slug)
                or ("positiva" in cia_raw)
                or ("lpv" in cia_raw)
                or ("lpv" in cia_raw)
                or ("lpeps" in cia_raw)
            )
            if not is_lp:
                return None

            parts = [
                row.get("producto"), row.get("ramos_producto"), row.get("ramo"),
                sel.get("producto"), sel.get("ramos_producto"), sel.get("ramo"),
            ]
            blob = " ".join((str(p) for p in parts if p)).lower()
            has_salud = ("salud" in blob) or ("eps" in blob)
            has_pension = ("pension" in blob) or ("pensión" in blob)
            has_vida_ley = ("vida" in blob) and ("ley" in blob)

            if has_salud:
                return "LPEPS"
            if has_pension or has_vida_ley:
                return "LPV"
            if "lapositiva_vida" in issuer:
                return "LPV"
            if "lapositiva" in issuer:
                return "LPEPS"
            return None

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

                if not row.get("cia") and selected.get("cia"):
                    row["cia"] = selected["cia"]

            inferred_cia = _infer_lapositiva_cia(row, selected)
            if inferred_cia:
                row["cia"] = inferred_cia

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

        def find_client_id(doc, cursor):
            if not doc:
                return None
            k = get_encrypt_key()
            cursor.execute(
                """
                SELECT idCliente
                FROM clientes
                WHERE (
                        CAST(AES_DECRYPT(FROM_BASE64(numero_documento), %s) AS CHAR) COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                     OR CAST(AES_DECRYPT(numero_documento, %s) AS CHAR)            COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                     OR numero_documento                                           COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                )
                  AND activo = 1
                LIMIT 1
                """,
                (k, doc, k, doc, doc),
            )
            r = cursor.fetchone()
            return int(r[0]) if r and r[0] is not None else None

        # Validar si el cliente existe (por documento o nombre)
        found_doc = find_client_doc(numero_documento, razon_social_selected, cur)
        if not found_doc:
            cur.close()
            cnx.close()
            return {"ok": False, "errors": ["El cliente no existe (ni por documento ni por nombre), debes registrar cliente nuevo"]}

        # Actualizar numero_documento con el encontrado (para usarlo como default)
        numero_documento = found_doc

        cliente_id_global = None
        try:
            cliente_id_global = find_client_id(numero_documento, cur)
        except Exception:
            cliente_id_global = None

        batch_dups = set()
        for idx, row in enumerate(normalized, start=1):
            rk = normalize_dup_key(row.get("recibo"))
            if not rk:
                continue
            k = rk.upper()
            if k in batch_dups:
                cur.close()
                cnx.close()
                return {"ok": False, "errors": [f"Fila {idx}: el recibo está repetido en el mismo guardado: {rk}"]}
            batch_dups.add(k)

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

            if row.get("recibo") is not None:
                rk = normalize_dup_key(row.get("recibo"))
            else:
                rk = None
            if rk:
                try:
                    cid = cliente_id_global if (target_doc == numero_documento) else find_client_id(target_doc, cur)
                except Exception:
                    cid = None
                if cid:
                    cur.execute(
                        """
                        SELECT 1
                        FROM polizas
                        WHERE cliente_id = %s
                          AND TRIM(COALESCE(
                                CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR),
                                CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR),
                                recibo
                              )) COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                          AND activo = 1
                          AND (anulado = 0 OR anulado IS NULL)
                        LIMIT 1
                        """,
                        (cid, rk),
                    )
                    if cur.fetchone():
                        cur.close()
                        cnx.close()
                        return {"ok": False, "errors": [f"El recibo ya existe para este cliente: {rk}"]}

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

            # VALIDACION: evitar recibo duplicado para el cliente
            try:
                recibo_key = U(row.get("recibo") or "")
                if recibo_key:
                    cur.execute(
                        """
                        SELECT idCliente
                        FROM clientes
                        WHERE (
                            CAST(AES_DECRYPT(FROM_BASE64(numero_documento), @SIS_KEY) AS CHAR) COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                                OR CAST(AES_DECRYPT(numero_documento, @SIS_KEY) AS CHAR)            COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                                OR numero_documento                                                 COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                            )
                          AND activo = 1
                            LIMIT 1
                        """,
                        (target_doc, target_doc, target_doc)
                    )
                    row_cli = cur.fetchone()
                    if row_cli and row_cli[0]:
                        cur.execute(
                            """
                            SELECT 1
                            FROM polizas
                            WHERE cliente_id = %s
                              AND TRIM(COALESCE(
                                    CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR),
                                    CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR),
                                    recibo
                                       )) COLLATE utf8mb4_0900_ai_ci = TRIM(%s) COLLATE utf8mb4_0900_ai_ci
                              AND activo = 1
                              AND (anulado = 0 OR anulado IS NULL)
                                LIMIT 1
                            """,
                            (row_cli[0], recibo_key)
                        )
                        if cur.fetchone():
                            cur.close()
                            cnx.close()
                            return {"ok": False, "errors": [f"El recibo ya existe para este cliente: {recibo_key}"]}
            except Exception as e_dup:
                try:
                    cur.close()
                except Exception:
                    pass
                try:
                    cnx.close()
                except Exception:
                    pass
                return {"ok": False, "errors": [f"No se pudo validar duplicado de recibo: {e_dup}"]}

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
                tipo_vigencia_selected,  # NUEVO
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
                real_poliza_id = None
                restored_poliza = False
                try:
                    cur.execute(
                        "CALL sp_insert_poliza_por_numero("
                        "%s,%s,%s,%s,%s,"
                        "%s,%s,%s,%s,"
                        "%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                        "%s,%s,"
                        "%s,%s,%s,%s,%s,%s,"
                        "%s,%s,%s,%s,"
                        "%s,%s,%s,%s"
                        ")",
                        args,
                    )
                    while cur.nextset():
                        pass
                except mysql.connector.Error as err_sp:
                    msg = str(getattr(err_sp, "msg", err_sp))
                    if getattr(err_sp, "errno", None) == 1062 and "uk_polizas_cliente_recibo" in msg:
                        cid_restore = None
                        try:
                            cid_restore = cliente_id_global if (target_doc == numero_documento) else find_client_id(target_doc, cur)
                        except Exception:
                            cid_restore = None
                        recibo_restore = normalize_dup_key(row.get("recibo"))
                        if cid_restore and recibo_restore:
                            cur.execute(
                                """
                                SELECT idPoliza, activo, anulado
                                FROM polizas
                                WHERE cliente_id = %s
                                  AND TRIM(COALESCE(
                                        CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR),
                                        CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR),
                                        recibo
                                      )) COLLATE utf8mb4_0900_ai_ci = %s COLLATE utf8mb4_0900_ai_ci
                                ORDER BY idPoliza DESC
                                LIMIT 1
                                """,
                                (cid_restore, recibo_restore),
                            )
                            rr = cur.fetchone()
                            if rr and rr[0]:
                                old_id = rr[0]
                                old_activo = int(rr[1] or 0)
                                old_anulado = int(rr[2] or 0)
                                if old_activo == 0 or old_anulado == 1:
                                    cur.execute(
                                        """
                                        UPDATE polizas
                                        SET asegurado = %s,
                                            cia = %s,
                                            ramo = %s,
                                            poliza = %s,
                                            recibo = %s,
                                            contrato_nro = %s,
                                            nro = %s,
                                            moneda = %s,
                                            fecha_emision = %s,
                                            vig_desde = %s,
                                            vig_hasta = %s,
                                            ultimo_dia_pago = %s,
                                            fecha_vencimiento = %s,
                                            tipo_vigencia = %s,
                                            endosatario = %s,
                                            forma_pago = %s,
                                            sub_agente = %s,
                                            ejecutivo = %s,
                                            tipo_doc = %s,
                                            asegurada = %s,
                                            motivo = %s,
                                            prima_comercial = %s,
                                            prima_neta = %s,
                                            prima_comercial_igv = %s,
                                            prima_total = %s,
                                            porc_compania = %s,
                                            imp_compania = %s,
                                            porc_subagente = %s,
                                            imp_subagente = %s,
                                            ramos_producto = %s,
                                            estado = %s,
                                            activo = 1,
                                            anulado = 0,
                                            usuario_edicion = %s,
                                            usuario_registro = COALESCE(usuario_registro, %s)
                                        WHERE idPoliza = %s
                                        """,
                                        (
                                            U(row.get("colectivo_asegurado") or row.get("asegurado") or ""),
                                            U(row.get("cia") or ""),
                                            U(row.get("ramo") or ""),
                                            U(row.get("numero_poliza") or ""),
                                            U(row.get("recibo") or ""),
                                            U(row.get("contrato_nro") or row.get("recibo") or ""),
                                            U(row.get("nro") or ""),
                                            U(row.get("moneda") or ""),
                                            parse_date(row.get("fecha_emision")),
                                            parse_date(row.get("inicio_vigencia")),
                                            parse_date(row.get("vencimiento")),
                                            parse_date(row.get("ultimo_dia_pago")),
                                            parse_date(row.get("fecha_vencimiento")),
                                            tipo_vigencia_selected,
                                            U((selected or {}).get("endosatario") or ""),
                                            U(row.get("forma_pago") or ""),
                                            U(row.get("subagente") or (selected or {}).get("subagente") or ""),
                                            efectivo_ejecutivo,
                                            U((selected or {}).get("tipo_doc") or (selected or {}).get("tipo_documento") or ""),
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
                                            usuario_display,
                                            usuario_display,
                                            old_id,
                                        ),
                                    )
                                    real_poliza_id = old_id
                                    restored_poliza = True
                                else:
                                    raise
                            else:
                                raise
                        else:
                            raise
                    else:
                        raise

                if real_poliza_id is None:
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

                inserted += 1
                try:
                    if restored_poliza and real_poliza_id and args[32]:
                        cur.execute(
                            """
                            INSERT INTO poliza_archivos (poliza_id, numero_poliza, ruta_archivo, nombre_original, ramo, producto, usuario, compania)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                            """,
                            (
                                real_poliza_id,
                                U(row.get("numero_poliza") or ""),
                                args[32],
                                (str(args[32]).split("/")[-1] if args[32] else None),
                                U(row.get("ramo") or ""),
                                U(row.get("ramos_producto") or (selected or {}).get("ramos_producto") or ""),
                                usuario_display,
                                U(row.get("cia") or ""),
                            ),
                        )
                except Exception:
                    pass

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

                # INSERTAR CUOTAS
                try:
                    row_cuotas = row.get("cuotas") or []
                    inserted_cuotas = {}
                    if not row_cuotas:
                        # Fallback: crear una cuota automática con los campos de la fila si no hay array de cuotas
                        row_cuotas = [{
                            "cupon": U(row.get("recibo") or ""),
                            "fecha_vencimiento": (
                                    row.get("fecha_vencimiento") or
                                    row.get("vencimiento") or
                                    (selected or {}).get("fecha_vencimiento") or
                                    (selected or {}).get("vencimiento") or
                                    (selected or {}).get("vig_hasta")
                            ),
                            "moneda": U(row.get("moneda") or "S/."),
                            "importe": row.get("prima_comercial_igv") or row.get("prima_total"),
                            "fecha_pago": row.get("fecha_pago"),
                            "factura": U(row.get("factura") or "")
                        }]

                    for ci, c_data in enumerate(row_cuotas, start=1):
                        c_poliza = U(row.get("numero_poliza") or "")
                        c_cupon = U(c_data.get("cupon") or row.get("recibo") or "")
                        c_cupon = c_cupon.strip() or None
                        c_fec_venc = parse_date(c_data.get("fecha_vencimiento")) or datetime.today().strftime('%Y-%m-%d')
                        c_moneda = U(c_data.get("moneda") or row.get("moneda") or "S/.")
                        c_importe = parse_decimal(c_data.get("importe")) or 0.0
                        c_fecha_pago = parse_date(c_data.get("fecha_pago"))
                        c_factura = U(c_data.get("factura") or "")
                        numero_cuota = ci

                        if c_poliza:
                            target_poliza_id = real_poliza_id
                            # (Omitir búsqueda redundante si ya tenemos real_poliza_id)

                            if c_factura:
                                cur.execute("SELECT 1 FROM cuotas WHERE factura = %s AND activo = 1 LIMIT 1", (c_factura,))
                                if cur.fetchone():
                                    # Solo avisar, no bloquear si es duplicado en el loop
                                    print(f"[WARNING] Factura duplicada: {c_factura}")
                                    continue
                            cur.execute(
                                """
                                INSERT INTO cuotas (
                                    poliza_id, poliza, cupon, fecha_vencimiento, moneda,
                                    importe, fecha_pago, factura, observacion, usuario_registro,
                                    numero_cuota, activo
                                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, 1)
                                """,
                                (
                                    target_poliza_id,
                                    c_poliza,
                                    c_cupon,
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
                            try:
                                last_id = cur.lastrowid
                                inserted_cuotas[ci - 1] = {
                                    'idCuota': last_id,
                                    'cupon': c_cupon,
                                    'numero_poliza': c_poliza,
                                }
                                cur.execute(
                                    """
                                    UPDATE cuotas
                                    SET poliza = TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY)),
                                        cupon = CASE
                                            WHEN %s IS NULL THEN NULL
                                            ELSE TO_BASE64(AES_ENCRYPT(%s, @SIS_KEY))
                                        END
                                    WHERE idCuota = %s
                                    """,
                                    (c_poliza, c_cupon, c_cupon, last_id),
                                )
                            except Exception:
                                pass

                    # Actualizar estado de la póliza basado en cuotas pendientes
                    if real_poliza_id:
                        cur.execute(
                            "SELECT COUNT(*) FROM cuotas WHERE poliza_id = %s AND (fecha_pago IS NULL OR factura IS NULL OR factura = '') AND activo = 1",
                            (real_poliza_id,)
                        )
                        row_p = cur.fetchone()
                        pendientes = row_p[0] if row_p and row_p[0] is not None else 0
                        nuevo_estado = 'PENDIENTE' if pendientes > 0 else 'PAGADO'

                        tdoc_sel = U((selected or {}).get("tipo_doc") or "").strip().upper()
                        est_row = U(row.get("estado") or "").strip().upper()
                        forma_pago_row = U(row.get("forma_pago") or "").strip().upper()

                        if tdoc_sel == 'NETEO' or est_row == 'SIN PRIMA' or forma_pago_row == 'SIN PRIMA':
                            nuevo_estado = 'SIN PRIMA'

                        cur.execute("UPDATE polizas SET estado = %s WHERE idPoliza = %s", (nuevo_estado, real_poliza_id))
                except Exception as ex_cuota:
                    print(f"[WARNING] Error procesando cuotas: {ex_cuota}")
                    pass
                try:
                    files_for_row = saved_facturas_by_index.get(i, saved_facturas)
                    files_for_cuota = saved_facturas_by_cuota.get(i, {})
                    if files_for_row or files_for_cuota:
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

                        def _save_cuota_archivos(cuota_meta, cuota_files):
                            if not cuota_meta or not cuota_files or not pid_for_files:
                                return
                            cuota_id = cuota_meta.get('idCuota')
                            cuota_cupon = U(cuota_meta.get('cupon') or '')
                            cuota_poliza = U(cuota_meta.get('numero_poliza') or row.get('numero_poliza') or '')
                            if not cuota_id:
                                return
                            for sf in cuota_files:
                                nombre_doc = f"[CUOTA {cuota_cupon}] {sf['nombre']}".strip() if cuota_cupon else sf['nombre']
                                try:
                                    cur.execute(
                                        """INSERT INTO cuota_archivos
                                           (cuota_id, poliza_id, numero_poliza, cupon, ruta_archivo, nombre_original, usuario)
                                           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                                        (
                                            cuota_id,
                                            pid_for_files,
                                            cuota_poliza,
                                            cuota_cupon or None,
                                            sf['ruta'],
                                            nombre_doc or sf['nombre'],
                                            usuario_display,
                                        )
                                    )
                                except Exception as ex_f:
                                    print(f"[save_polizas] Error linking cuota archivo: {ex_f}")

                        for cuota_idx, cuota_files in (files_for_cuota or {}).items():
                            _save_cuota_archivos(inserted_cuotas.get(int(cuota_idx)), cuota_files)

                        if files_for_row:
                            ordered_cuotas = [inserted_cuotas[k] for k in sorted(inserted_cuotas.keys())]
                            if len(ordered_cuotas) == 1:
                                _save_cuota_archivos(ordered_cuotas[0], files_for_row)
                            elif ordered_cuotas and not files_for_cuota and len(files_for_row) == len(ordered_cuotas):
                                for idx_file, cuota_meta in enumerate(ordered_cuotas):
                                    _save_cuota_archivos(cuota_meta, [files_for_row[idx_file]])
                            elif ordered_cuotas and len(files_for_row) > 0:
                                print(f"[save_polizas] Facturas ambiguas para fila {i}: se omitió asociación automática por cuota.")
                except Exception as _ex:
                    print(f"[save_polizas] Facturas vinculo error: {_ex}")

            except mysql.connector.Error as err:
                # Detecta SIGNAL SQLSTATE '45000' del SP (duplicado / cliente no existe)
                if getattr(err, 'errno', None) == 1062:
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
                    msg = str(getattr(err, 'msg', err))
                    if 'uk_polizas_cliente_recibo' in msg:
                        return {"ok": False, "errors": ["El recibo ya existe para este cliente."]}
                    return {"ok": False, "errors": [msg]}
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
