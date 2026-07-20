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


def _build_factiliza_url(tipo_documento: str, numero_documento: str, settings: dict) -> str:
    factiliza_cfg = settings.get("factiliza") or {}
    template = factiliza_cfg.get("dni_url") if tipo_documento == "DNI" else factiliza_cfg.get("ruc_url")
    if not template:
        return ""

    encoded_value = urllib.parse.quote(numero_documento)
    if tipo_documento == "DNI":
        return str(template).replace("{dni}", encoded_value)
    return str(template).replace("{ruc}", encoded_value)


def _parse_http_body(raw_body: bytes):
    text = raw_body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}


def _fetch_factiliza(url: str, token: str):
    header_candidates = [
        {"Authorization": f"Bearer {token}", "Accept": "application/json"},
        {"Authorization": token, "Accept": "application/json"},
        {"token": token, "Accept": "application/json"},
    ]

    last_response = None
    for headers in header_candidates:
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.getcode(), _parse_http_body(resp.read())
        except urllib.error.HTTPError as exc:
            last_response = (exc.code, _parse_http_body(exc.read()))
            if exc.code in (401, 403):
                continue
            return last_response

    return last_response or (500, {"error": "No se pudo consultar Factiliza"})


def _normalize_response(tipo_documento: str, numero_documento: str, raw_response: dict) -> dict:
    payload = _extract_payload(raw_response)

    razon_social = _build_nombre(payload, tipo_documento)
    direccion = _pick_first_text(
        payload,
        ["direccion", "direccionFiscal", "direccion_fiscal"],
    )
    departamento = _pick_first_text(payload, ["departamento"])
    provincia = _pick_first_text(payload, ["provincia"])
    distrito = _pick_first_text(payload, ["distrito"])
    ubigeo_code = _pick_first_text(payload, ["ubigeo", "codigoUbigeo", "codigo_ubigeo"])

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
    url = _build_factiliza_url(tipo_documento, numero_documento, settings)

    if not token or not url:
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
        status_code, raw_response = _fetch_factiliza(url, token)
        if status_code >= 400:
            message = _pick_first_text(raw_response if isinstance(raw_response, dict) else {}, [
                "error", "message", "mensaje", "detail",
            ]) or "No se encontraron datos para el documento consultado"
            return jsonify({"ok": False, "error": message}), status_code

        normalized = _normalize_response(tipo_documento, numero_documento, raw_response or {})
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
