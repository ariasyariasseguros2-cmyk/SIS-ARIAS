import json
import os
import time
import urllib.error
import urllib.request
from collections import deque
from datetime import datetime
from threading import Lock

_SETTINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'appsettings.json')
_EMAILJS_URL = 'https://api.emailjs.com/api/v1.0/email/send'

# ponytail: límite en memoria por proceso; si se corre con varios workers/gunicorn
# el límite real efectivo se multiplica por el número de workers. Pasar a Redis
# (o INCR con TTL) si eso llega a importar.
_sent_timestamps = deque()
_lock = Lock()


def _load_settings():
    try:
        with open(_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _resolve_nombre(usuario):
    """El session guarda el username (a veces solo un número); mostramos el nombre real."""
    usuario = (usuario or '').strip()
    if not usuario:
        return usuario
    try:
        from models.db import get_connection
        cnx = get_connection()
        cur = cnx.cursor()
        cur.execute(
            "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1",
            (usuario,),
        )
        row = cur.fetchone()
        cur.close()
        cnx.close()
        return row[0] if row and row[0] else usuario
    except Exception:
        return usuario


def _rate_limited(rate_cfg):
    limit = int(rate_cfg.get('RequestLimit', 20) or 20)
    window_s = int(rate_cfg.get('TimeWindowMinutes', 1) or 1) * 60
    now = time.time()
    with _lock:
        while _sent_timestamps and now - _sent_timestamps[0] > window_s:
            _sent_timestamps.popleft()
        if len(_sent_timestamps) >= limit:
            return True
        _sent_timestamps.append(now)
        return False


def notify_deletion(usuario: str, tipo: str, identificador: str, evento: str = 'eliminacion', motivo: str = ''):
    """Envía una alerta vía EmailJS cuando alguien elimina o anula una póliza, cuota o prima.

    evento: 'eliminacion' (borrado físico) usa EmailJs.template_id;
            'anulacion' (borrado lógico / anular) usa EmailJs.template_id_anulacion.
    Nunca lanza excepción: un fallo de envío no debe romper el flujo de borrado.
    """
    try:
        cfg = _load_settings()
        ej_cfg = cfg.get('EmailJs') or {}
        recipients = [r for r in (ej_cfg.get('alert_recipients') or []) if r]
        service_id = ej_cfg.get('service_id')
        template_id = (
            ej_cfg.get('template_id_anulacion') if evento == 'anulacion' else ej_cfg.get('template_id')
        )
        public_key = ej_cfg.get('public_key')
        private_key = os.environ.get('SIS_ARIAS_EMAILJS_PRIVATE_KEY') or ej_cfg.get('private_key')
        if not (service_id and template_id and public_key and recipients):
            faltantes = [
                n for n, v in (
                    ('service_id', service_id), ('template_id', template_id),
                    ('public_key', public_key), ('alert_recipients', recipients),
                ) if not v
            ]
            print(f'[notify_deletion] omitido, falta configurar en EmailJs: {", ".join(faltantes)}')
            return

        usuario = _resolve_nombre(usuario)
        accion = 'Anuló' if evento == 'anulacion' else 'Eliminó'
        motivo_txt = (motivo or '').strip() or 'No especificado'
        hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        mensaje = (
            f"Este usuario: {usuario or 'desconocido'}\n"
            f"{accion} {tipo}\n"
            f"{identificador or 'N/D'}\n"
            f"Motivo: {motivo_txt}\n"
            f"a las {hora}"
        )

        for to_email in recipients:
            if _rate_limited(cfg.get('RateLimit') or {}):
                print('[notify_deletion] rate limit alcanzado, correo omitido')
                return

            payload = {
                'service_id': service_id,
                'template_id': template_id,
                'user_id': public_key,
                'template_params': {
                    'to_email': to_email,
                    'usuario': usuario or 'desconocido',
                    'tipo': tipo,
                    'accion': accion,
                    'identificador': identificador or 'N/D',
                    'motivo': motivo_txt,
                    'hora': hora,
                    'message': mensaje,
                },
            }
            if private_key:
                payload['accessToken'] = private_key

            req = urllib.request.Request(
                _EMAILJS_URL,
                data=json.dumps(payload).encode('utf-8'),
                # ponytail: sin User-Agent de navegador, Cloudflare bloquea la firma
                # por defecto de urllib ("Python-urllib/x.x") con error 1010.
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                },
                method='POST',
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status >= 300:
                        print(f'[notify_deletion] EmailJS respondió {resp.status} para {to_email}: {resp.read().decode(errors="replace")}')
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors='replace')
                print(f'[notify_deletion] error enviando a {to_email}: HTTP {e.code} - {body}')
            except Exception as e:
                print(f'[notify_deletion] error enviando a {to_email}: {e}')
    except Exception as e:
        print(f'[notify_deletion] error inesperado: {e}')
