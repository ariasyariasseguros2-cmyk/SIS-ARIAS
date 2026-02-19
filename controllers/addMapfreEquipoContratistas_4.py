import re
from datetime import datetime, timedelta

from controllers.addMapfreEquipoContratistas_3 import (
    parse_mapfre_equipo_contratistas_3,
)


def parse_mapfre_equipo_contratistas_4(text: str):
    base = parse_mapfre_equipo_contratistas_3(text) or {}
    item = dict(base)

    text_norm = re.sub(r"\r\n", "\n", text)

    m_rs = re.search(
        r"Raz[oó]n\s+social\s+([^\n]+?)\s+RUC\b",
        text_norm,
        re.IGNORECASE,
    )
    if m_rs:
        razon = m_rs.group(1).strip()
        razon = re.sub(r"\s+", " ", razon)
        item["colectivo_asegurado"] = razon
        item["asegurado"] = razon

    m_fe = re.search(
        r"FECHA\s+DE\s+EMISI[ÓO]N\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        text_norm,
        re.IGNORECASE,
    )
    fecha_emision = None
    if m_fe:
        fecha_emision = m_fe.group(1)
    else:
        dates = re.findall(r"\d{2}/\d{2}/\d{4}", text_norm)
        if dates:
            inicio_str = item.get("inicio_vigencia")
            inicio_dt = None
            if inicio_str:
                try:
                    inicio_dt = datetime.strptime(inicio_str, "%d/%m/%Y")
                except Exception:
                    inicio_dt = None
            cand_dt = None
            cand_str = None
            for d in dates:
                try:
                    dt = datetime.strptime(d, "%d/%m/%Y")
                except Exception:
                    continue
                if inicio_dt and not dt < inicio_dt:
                    continue
                if cand_dt is None or dt < cand_dt:
                    cand_dt = dt
                    cand_str = d
            if cand_str:
                fecha_emision = cand_str

    if fecha_emision:
        item["fecha_emision"] = fecha_emision
        try:
            fe_obj = datetime.strptime(fecha_emision, "%d/%m/%Y")
            udp_obj = fe_obj + timedelta(days=15)
            item["ultimo_dia_pago"] = udp_obj.strftime("%d/%m/%Y")
        except Exception:
            pass

    return item

