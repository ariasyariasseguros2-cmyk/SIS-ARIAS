"""Consulta de DNI/RUC: ConsultaPE (modo basico) y Factiliza (modo existente).

Colocar este contenido en el archivo que actualmente contiene
consultar_documento_route; no cambiar los imports de las rutas que ya lo llaman.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

from flask import current_app, jsonify, request, session
from controllers.maestros.ubigeos import resolve_ubigeo
from models.db import load_settings

LOG = logging.getLogger(__name__)
USER_AGENT = "SIS-ARIAS/1.0"



def consultar_fecha_rapida(url_dni, token):
    """
    Consulta la fecha independientemente de los nombres.
    Permite ejecutar ambas solicitudes en paralelo.
    """

    try:
        status, body = _fetch_consultape(
            url_dni + "/fecha-nacimiento",
            token
        )

        if status != 200:
            return "", f"error_http_{status}"

        if not isinstance(body, dict):
            return "", "respuesta_invalida"

        if body.get("success") is False:
            return "", "no_disponible_en_fuente"

        fecha = _fecha_nacimiento_consultape(body)

        if fecha:
            return fecha, "obtenida"

        return "", "sin_campo_fecha"

    except Exception:
        return "", "error_conexion"


def _normalize_tipo_documento(raw: str) -> str:
    value = str(raw or "").strip().upper()
    if value in ("1", "DNI") or "DNI" in value:
        return "DNI"
    if value in ("6", "RUC") or "RUC" in value:
        return "RUC"
    return value


def _clean_numero_documento(raw: str) -> str:
    return "".join(ch for ch in str(raw or "") if ch.isdigit())


def _pick_first_text(source: dict, keys: list[str]) -> str:
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_date_for_html(raw_date: str) -> str:
    value = str(raw_date or "").strip()
    if not value:
        return ""
    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        return value[:10]
    parts = value.replace("/", "-").split("-")
    if len(parts) == 3:
        first, second, third = parts
        if len(first) == 4:
            return f"{first.zfill(4)}-{second.zfill(2)}-{third.zfill(2)}"
        if len(third) == 4:
            return f"{third.zfill(4)}-{second.zfill(2)}-{first.zfill(2)}"
    return ""


def _split_nombre_persona(full_name: str) -> tuple[str, str, str]:
    # Fallback heredado: solo usarlo cuando no existen campos de apellidos separados.
    parts = str(full_name or "").strip().split()
    if len(parts) >= 3:
        return (" ".join(parts[2:]), parts[0], parts[1])
    if len(parts) == 2:
        return parts[1], parts[0], ""
    if len(parts) == 1:
        return parts[0], "", ""
    return "", "", ""


def _extract_payload(raw_data):
    if not isinstance(raw_data, dict):
        return {}
    for key in ("result", "data", "payload", "resultado"):
        nested = raw_data.get(key)
        if isinstance(nested, dict):
            return nested
        if isinstance(nested, list):
            return next((item for item in nested if isinstance(item, dict)), {})
    return raw_data


def _build_nombre(payload: dict, tipo_documento: str) -> str:
    if tipo_documento == "RUC":
        return _pick_first_text(payload, ["razon_social", "razonSocial", "nombre", "nombre_o_razon_social"])
    full = _pick_first_text(payload, ["nombre_completo", "nombreCompleto", "nombre", "cliente", "nombresCompletos"])
    if full:
        return full
    return " ".join(part for part in [
        _pick_first_text(payload, ["nombres", "prenombres"]),
        _pick_first_text(payload, ["apellido_paterno", "apellidoPaterno"]),
        _pick_first_text(payload, ["apellido_materno", "apellidoMaterno"]),
    ] if part)


def _infer_tipo_persona(tipo_documento: str, numero_documento: str) -> str:
    if tipo_documento == "RUC":
        return "JURIDICA" if numero_documento.startswith("20") else "NATURAL"
    return "NATURAL"


def _build_factiliza_urls(tipo_documento: str, settings: dict) -> list[str]:
    cfg = settings.get("factiliza") or {}
    if tipo_documento == "DNI":
        urls = [cfg.get("dni_url"), cfg.get("dni_direccion_url") or "https://api.json.pe/api/dni-direccion"]
        return list(dict.fromkeys(str(u).strip() for u in urls if u))
    url = str(cfg.get("ruc_url") or "").strip()
    return [url] if url else []


def _parse_http_body(raw_body: bytes):
    try:
        return json.loads(raw_body.decode("utf-8", errors="replace"))
    except (ValueError, UnicodeError):
        return {"error": "El proveedor devolvio una respuesta no JSON"}


def _fetch_consultape(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.getcode(), _parse_http_body(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, _parse_http_body(exc.read())


def _fetch_factiliza(url: str, token: str, tipo_documento: str, numero_documento: str):
    body_key = "dni" if tipo_documento == "DNI" else "ruc"
    body_bytes = json.dumps({body_key: numero_documento}).encode("utf-8")
    base_headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}
    header_candidates = [base_headers, {**base_headers, "Authorization": token}, {**base_headers, "token": token}]
    last_response = None
    for headers in header_candidates:
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.getcode(), _parse_http_body(resp.read())
        except urllib.error.HTTPError as exc:
            last_response = (exc.code, _parse_http_body(exc.read()))
            if exc.code in (401, 403):
                continue
            return last_response
    return last_response or (500, {"error": "No se pudo consultar Factiliza"})


def _merge_payloads(raw_responses: list[dict]) -> dict:
    merged = {}
    for raw_response in raw_responses:
        payload = _extract_payload(raw_response)
        for key, value in payload.items():
            current = merged.get(key)
            if current is None or (isinstance(current, str) and not current.strip()):
                merged[key] = value
    return merged


def _build_consultape_url(settings: dict, tipo_documento: str, numero_documento: str) -> str:
    cfg = settings.get("ConsultaPE") or {}
    base = str(cfg.get("base_url") or "https://api.consultape.pro").rstrip("/")
    # Evita URLs arbitrarias y exposición del token a hosts ajenos.
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != "https" or parsed.hostname != "api.consultape.pro" or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.path:
        raise ValueError("La URL base de ConsultaPE debe ser https://api.consultape.pro")
    endpoint = "dni" if tipo_documento == "DNI" else "ruc"
    return f"{base}/v1/{endpoint}/{numero_documento}"


def _normalize_basic_response(tipo_documento: str, numero_documento: str, raw_response: dict) -> dict:
    payload = _extract_payload(raw_response)
    if tipo_documento == "RUC":
        return {
            "tipo_documento": tipo_documento,
            "numero_documento": numero_documento,
            "nombres": _pick_first_text(payload, ["razon_social", "razonSocial", "nombre", "nombre_o_razon_social"]),
            "apellido_paterno": "", "apellido_materno": "",
            "fecha_nacimiento": "", "sexo": "", "estado_civil": "",
        }
    nombres = _pick_first_text(payload, ["nombres", "prenombres"])
    paterno = _pick_first_text(payload, ["apellido_paterno", "apellidoPaterno", "ap_pat"])
    materno = _pick_first_text(payload, ["apellido_materno", "apellidoMaterno", "ap_mat"])
    if not nombres and not paterno:
        full = _pick_first_text(payload, ["nombre_completo", "nombreCompleto", "nombre", "cliente"])
        nombres, paterno, materno = _split_nombre_persona(full)
    return {
        "tipo_documento": tipo_documento,
        "numero_documento": numero_documento,
        "nombres": nombres,
        "apellido_paterno": paterno,
        "apellido_materno": materno,
        "fecha_nacimiento": _normalize_date_for_html(_pick_first_text(payload, ["fecha_nacimiento", "fechaNacimiento", "fecha_nac", "fec_nacimiento"])),
        "sexo": _pick_first_text(payload, ["sexo", "genero"]),
        "estado_civil": _pick_first_text(payload, ["estado_civil", "estadoCivil", "est_civil"]),
    }



def _fecha_nacimiento_consultape(raw_response: dict) -> str:
    """Lee la fecha del resultado documentado sin inventar fechas."""
    payload = _extract_payload(raw_response)
    candidates = [payload]
    for key in ("persona", "datos", "identidad", "fecha_nacimiento", "fechaNacimiento"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for item in candidates:
        date_text = _pick_first_text(item, (
            "fecha_nacimiento", "fechaNacimiento", "fecha_de_nacimiento",
            "fec_nacimiento", "fecha_nac", "fecha", "nacimiento",
        ))
        if date_text:
            normalized = _normalize_date_for_html(date_text)
            if normalized:
                return normalized
    return ""


def _completar_nacimiento_consultape(url_dni: str, token: str, normalized: dict) -> str:
    """Obtener fecha por endpoint separado y registrar solo estado, sin datos personales."""
    if normalized.get("fecha_nacimiento"):
        return "obtenida_consulta_dni"
    try:
        status, body = _fetch_consultape(url_dni + "/fecha-nacimiento", token)
        if status != 200:
            current_app.logger.warning(
                "[clientes.documento_lookup] fecha-nacimiento HTTP=%s", status
            )
            return f"error_http_{status}"
        if not isinstance(body, dict):
            current_app.logger.warning("[clientes.documento_lookup] fecha-nacimiento respuesta invalida")
            return "respuesta_invalida"
        if body.get("success") is False:
            current_app.logger.info("[clientes.documento_lookup] fecha-nacimiento sin datos en fuente")
            return "no_disponible_en_fuente"
        fecha = _fecha_nacimiento_consultape(body)
        if fecha:
            normalized["fecha_nacimiento"] = fecha
            current_app.logger.info("[clientes.documento_lookup] fecha-nacimiento obtenida")
            return "obtenida"
        current_app.logger.warning("[clientes.documento_lookup] fecha-nacimiento sin campo reconocible")
        return "sin_campo_fecha"
    except (urllib.error.URLError, TimeoutError):
        current_app.logger.warning("[clientes.documento_lookup] fecha-nacimiento error de conexion")
        return "error_conexion"
    except Exception:
        current_app.logger.exception("[clientes.documento_lookup] error al procesar fecha-nacimiento")
        return "error_interno"


def _normalize_response(tipo_documento: str, numero_documento: str, raw_responses: list[dict]) -> dict:
    payload = _merge_payloads(raw_responses)
    direccion = _pick_first_text(payload, ["direccion", "direccionFiscal", "direccion_fiscal", "direccionCompleta", "direccion_completa", "domicilio", "domicilioFiscal", "domicilio_fiscal"])
    departamento = _pick_first_text(payload, ["departamento", "departamentoReniec", "departamento_reniec"])
    provincia = _pick_first_text(payload, ["provincia", "provinciaReniec", "provincia_reniec"])
    distrito = _pick_first_text(payload, ["distrito", "distritoReniec", "distrito_reniec"])
    ubigeo_code = _pick_first_text(payload, ["ubigeo_reniec", "ubigeo_sunat", "ubigeo", "codigoUbigeo", "codigo_ubigeo"])
    ubigeo_resuelto = resolve_ubigeo(
        ubigeo_code=ubigeo_code, departamento=departamento, provincia=provincia, distrito=distrito,
    )
    return {
        "tipo_documento": tipo_documento,
        "numero_documento": numero_documento,
        "razon_social": _build_nombre(payload, tipo_documento),
        "direccion": direccion,
        "ubigeo": ubigeo_resuelto.get("ubigeo", "") or ubigeo_code,
        "departamento": ubigeo_resuelto.get("departamento", "") or departamento,
        "provincia": ubigeo_resuelto.get("provincia", "") or provincia,
        "distrito": ubigeo_resuelto.get("distrito", "") or distrito,
        "tipo_persona": _infer_tipo_persona(tipo_documento, numero_documento),
    }


def _provider_error(status: int, response: dict, provider: str) -> tuple:
    status_map = {
        400: "Datos invalidos para la consulta",
        401: "Token invalido, revocado o vencido",
        403: "El plan no incluye esta consulta o el acceso esta restringido; verifica las IP permitidas",
        404: "Documento no encontrado",
        429: "Limite por minuto o cuota mensual superados",
    }
    message = _pick_first_text(response, ["message", "mensaje", "error", "detail"])
    if not message:
        message = status_map.get(status, f"No fue posible consultar {provider}")
    # No entregar detalles de librerias/URLs/credenciales al cliente.
    return jsonify({"ok": False, "error": message}), status if 400 <= status < 500 else 502


def consultar_documento_route():
    if "user" not in session:
        return jsonify({"ok": False, "error": "No autenticado"}), 401

    tipo_documento = _normalize_tipo_documento(request.args.get("tipo_documento"))
    numero_documento = _clean_numero_documento(request.args.get("numero_documento"))
    modo = str(request.args.get("modo") or "").strip().lower()
    if tipo_documento not in {"DNI", "RUC"}:
        return jsonify({"ok": False, "error": "Solo se admite consulta de DNI o RUC"}), 400
    expected_len = 8 if tipo_documento == "DNI" else 11
    if len(numero_documento) != expected_len:
        return jsonify({"ok": False, "error": f"El {tipo_documento} debe tener {expected_len} digitos"}), 400

    settings = load_settings() or {}
    if modo == "basico":
        cfg = settings.get("ConsultaPE") or {}
        token = os.getenv("CONSULTAPE_TOKEN") or str(cfg.get("token") or "").strip()
        if not token:
            return jsonify({"ok": False, "error": "Falta configurar el token de ConsultaPE en el servidor"}), 500
        try:
            url = _build_consultape_url(settings, tipo_documento, numero_documento)
            current_app.logger.info("[clientes.documento_lookup] ConsultaPE modo=basico tipo=%s", tipo_documento)
            status, raw = _fetch_consultape(url, token)
            if not isinstance(raw, dict):
                return jsonify({"ok": False, "error": "Respuesta invalida de ConsultaPE"}), 502
            if status >= 400:
                return _provider_error(status, raw, "ConsultaPE")
            if raw.get("success") is False:
                return jsonify({"ok": False, "error": _pick_first_text(raw, ["message", "mensaje", "error"]) or "La fuente no respondio o el documento no tiene resultados"}), 502
            normalized = _normalize_basic_response(tipo_documento, numero_documento, raw)
            if not normalized.get("nombres") and not normalized.get("apellido_paterno"):
                return jsonify({"ok": False, "error": "ConsultaPE respondio sin nombres o razon social utilizables"}), 404
            estado_fecha = "no_aplica_ruc"
            if tipo_documento == "DNI":
                estado_fecha = _completar_nacimiento_consultape(url, token, normalized)
            return jsonify({"ok": True, "data": normalized, "estado_fecha": estado_fecha}), 200
        except (urllib.error.URLError, TimeoutError):
            current_app.logger.exception("[clientes.documento_lookup] ConsultaPE no disponible")
            return jsonify({"ok": False, "error": "ConsultaPE no disponible temporalmente"}), 502
        except Exception:
            current_app.logger.exception("[clientes.documento_lookup] error modo=basico")
            return jsonify({"ok": False, "error": "Error interno al consultar ConsultaPE"}), 500

    # Se conserva la ruta Factiliza para los modos diferentes de 'basico'.
    factiliza_cfg = settings.get("factiliza") or {}
    token = str(factiliza_cfg.get("token") or "").strip()
    urls = _build_factiliza_urls(tipo_documento, settings)
    if not token or not urls:
        return jsonify({"ok": False, "error": "La configuracion de Factiliza no esta completa"}), 500
    current_app.logger.info("[clientes.documento_lookup] Factiliza tipo=%s", tipo_documento)
    try:
        successful_responses = []
        last_error = None
        for url in urls:
            status, raw = _fetch_factiliza(url, token, tipo_documento, numero_documento)
            if status < 400 and isinstance(raw, dict) and raw.get("success") is not False:
                successful_responses.append(raw)
            else:
                last_error = (status, raw)
        if not successful_responses:
            return _provider_error(last_error[0] if last_error else 502, last_error[1] if last_error and isinstance(last_error[1], dict) else {}, "Factiliza")
        normalized = _normalize_response(tipo_documento, numero_documento, successful_responses)
        if not any(normalized.get(k) for k in ("razon_social", "direccion", "departamento", "provincia", "distrito")):
            return jsonify({"ok": False, "error": "Factiliza respondio sin datos utilizables"}), 404
        return jsonify({"ok": True, "data": normalized}), 200
    except Exception:
        current_app.logger.exception("[clientes.documento_lookup] error Factiliza")
        return jsonify({"ok": False, "error": "Error interno al consultar Factiliza"}), 500
