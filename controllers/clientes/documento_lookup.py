import json
import urllib.error
import urllib.parse
import urllib.request

from flask import current_app, jsonify, request, session

from controllers.maestros.ubigeos import resolve_ubigeo
from models.db import load_settings


def _normalize_tipo_documento(raw: str) -> str:
    value = str(raw or "").strip().upper()
    if "RUC" in value:
        return "RUC"
    if "DNI" in value:
        return "DNI"
    return value


def _clean_numero_documento(raw: str) -> str:
    return "".join(ch for ch in str(raw or "") if ch.isdigit())


def _pick_first_text(source: dict, keys: list[str]) -> str:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _extract_payload(raw_data):
    if not isinstance(raw_data, dict):
        return {}

    for key in ("data", "payload", "resultado", "result"):
        nested = raw_data.get(key)
        if isinstance(nested, dict):
            return nested

    return raw_data


def _build_nombre(payload: dict, tipo_documento: str) -> str:
    if tipo_documento == "RUC":
        return _pick_first_text(
            payload,
            ["razonSocial", "razon_social", "nombre", "nombre_o_razon_social"],
        )

    full_name = _pick_first_text(
        payload,
        ["nombre", "nombreCompleto", "nombre_completo", "cliente", "nombresCompletos"],
    )
    if full_name:
        return full_name

    parts = [
        _pick_first_text(payload, ["nombres", "prenombres"]),
        _pick_first_text(payload, ["apellidoPaterno", "apellido_paterno"]),
        _pick_first_text(payload, ["apellidoMaterno", "apellido_materno"]),
    ]
    return " ".join(part for part in parts if part).strip()


def _infer_tipo_persona(tipo_documento: str, numero_documento: str) -> str:
    if tipo_documento == "RUC":
        return "JURIDICA" if numero_documento.startswith("20") else "NATURAL"
    return "NATURAL"


def _build_factiliza_urls(tipo_documento: str, settings: dict) -> list[str]:
    factiliza_cfg = settings.get("factiliza") or {}
    if tipo_documento == "DNI":
        urls = [
            factiliza_cfg.get("dni_url"),
            factiliza_cfg.get("dni_direccion_url") or "https://api.json.pe/api/dni-direccion",
        ]
        unique_urls = []
        for raw_url in urls:
            url = str(raw_url or "").strip()
            if url and url not in unique_urls:
                unique_urls.append(url)
        return unique_urls

    url = str(factiliza_cfg.get("ruc_url") or "").strip()
    return [url] if url else []


def _parse_http_body(raw_body: bytes):
    text = raw_body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}


def _fetch_factiliza(url: str, token: str, tipo_documento: str, numero_documento: str):
    body_key = "dni" if tipo_documento == "DNI" else "ruc"
    body_bytes = json.dumps({body_key: numero_documento}).encode("utf-8")

    base_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    header_candidates = [
        base_headers,
        {**base_headers, "Authorization": token},
        {**base_headers, "token": token},
    ]

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

    return last_response or (500, {"error": "No se pudo consultar la API de documentos"})


def _merge_payloads(raw_responses: list[dict]) -> dict:
    merged = {}
    for raw_response in raw_responses:
        payload = _extract_payload(raw_response)
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            current = merged.get(key)
            if current is None or (isinstance(current, str) and not current.strip()):
                merged[key] = value
    return merged


def _normalize_response(tipo_documento: str, numero_documento: str, raw_responses: list[dict]) -> dict:
    payload = _merge_payloads(raw_responses)

    razon_social = _build_nombre(payload, tipo_documento)
    direccion = _pick_first_text(
        payload,
        ["direccion", "direccionFiscal", "direccion_fiscal", "direccionCompleta", "direccion_completa", "domicilio", "domicilioFiscal", "domicilio_fiscal"],
    )
    departamento = _pick_first_text(payload, ["departamento", "departamentoReniec", "departamento_reniec"])
    provincia = _pick_first_text(payload, ["provincia", "provinciaReniec", "provincia_reniec"])
    distrito = _pick_first_text(payload, ["distrito", "distritoReniec", "distrito_reniec"])
    ubigeo_code = _pick_first_text(payload, ["ubigeo_reniec", "ubigeo_sunat", "ubigeo", "codigoUbigeo", "codigo_ubigeo"])

    ubigeo_resuelto = resolve_ubigeo(
        ubigeo_code=ubigeo_code,
        departamento=departamento,
        provincia=provincia,
        distrito=distrito,
    )

    return {
        "tipo_documento": tipo_documento,
        "numero_documento": numero_documento,
        "razon_social": razon_social,
        "direccion": direccion,
        "ubigeo": ubigeo_resuelto.get("ubigeo", "") or ubigeo_code,
        "departamento": ubigeo_resuelto.get("departamento", "") or departamento,
        "provincia": ubigeo_resuelto.get("provincia", "") or provincia,
        "distrito": ubigeo_resuelto.get("distrito", "") or distrito,
        "tipo_persona": _infer_tipo_persona(tipo_documento, numero_documento),
    }


def consultar_documento_route():
    if "user" not in session:
        return jsonify({"ok": False, "error": "No autenticado"}), 401

    tipo_documento = _normalize_tipo_documento(request.args.get("tipo_documento"))
    numero_documento = _clean_numero_documento(request.args.get("numero_documento"))

    if tipo_documento not in {"DNI", "RUC"}:
        return jsonify({"ok": False, "error": "Solo se admite consulta de DNI o RUC"}), 400

    expected_len = 8 if tipo_documento == "DNI" else 11
    if len(numero_documento) != expected_len:
        return jsonify({
            "ok": False,
            "error": f"El {tipo_documento} debe tener {expected_len} digitos",
        }), 400

    settings = load_settings() or {}
    factiliza_cfg = settings.get("factiliza") or {}
    token = str(factiliza_cfg.get("token") or "").strip()
    urls = _build_factiliza_urls(tipo_documento, settings)

    if not token or not urls:
        return jsonify({
            "ok": False,
            "error": "La configuracion de Factiliza no esta completa en appsettings.json",
        }), 500

    current_app.logger.info(
        "[clientes.documento_lookup] tipo=%s numero=%s",
        tipo_documento,
        f"{numero_documento[:2]}***{numero_documento[-2:]}",
    )

    try:
        successful_responses = []
        last_error = None

        for url in urls:
            status_code, raw_response = _fetch_factiliza(url, token, tipo_documento, numero_documento)
            if status_code < 400:
                successful_responses.append(raw_response or {})
                continue
            last_error = (status_code, raw_response)

        if not successful_responses:
            error_status = last_error[0] if last_error else 500
            raw_error = last_error[1] if last_error else {}
            message = _pick_first_text(raw_error if isinstance(raw_error, dict) else {}, [
                "error", "message", "mensaje", "detail",
            ]) or "No se encontraron datos para el documento consultado"
            return jsonify({"ok": False, "error": message}), error_status

        normalized = _normalize_response(tipo_documento, numero_documento, successful_responses)
        if not any([
            normalized.get("razon_social"),
            normalized.get("direccion"),
            normalized.get("departamento"),
            normalized.get("provincia"),
            normalized.get("distrito"),
        ]):
            return jsonify({
                "ok": False,
                "error": "Factiliza respondio sin datos utilizables para este documento",
            }), 404

        return jsonify({"ok": True, "data": normalized}), 200
    except Exception as exc:
        current_app.logger.exception("[clientes.documento_lookup] error")
        return jsonify({
            "ok": False,
            "error": f"Error consultando Factiliza: {str(exc)}",
        }), 500
