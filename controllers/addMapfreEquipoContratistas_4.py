import re
from datetime import datetime, timedelta

from controllers.addMapfreEquipoContratistas_3 import (
    parse_mapfre_equipo_contratistas_3,
)


def parse_mapfre_equipo_contratistas_4(text: str):
    base = parse_mapfre_equipo_contratistas_3(text) or {}
    item = dict(base)

    text_norm = re.sub(r"\r\n", "\n", text)

    def _normalize_amount(val: str):
        if not val:
            return None
        s = (val or "").strip()
        s = s.replace("−", "-").replace("–", "-").replace("—", "-")
        s = re.sub(r"[^\d,.\-]", "", s)
        if not s:
            return None
        neg = False
        if s.startswith("-"):
            neg = True
            s = s[1:]
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        else:
            if s.count(",") == 1 and s.count(".") == 0:
                s = s.replace(",", ".")
            else:
                s = s.replace(",", "")
        try:
            num = float(s)
            if neg:
                num = -abs(num)
            return f"{num:.2f}"
        except Exception:
            return f"-{s}" if (neg and s) else s

    def _clean_name(name: str) -> str:
        name = (name or "").strip()
        name = re.sub(r"\s+", " ", name)
        name = re.sub(r"\s+(?:RUC\s*)?\d{11}\s*$", "", name, flags=re.IGNORECASE).strip()
        return name

    def _extract_name_from_section(section_title: str) -> str:
        m = re.search(rf"\b{section_title}\b", text_norm, re.IGNORECASE)
        if not m:
            return ""
        sub = text_norm[m.start():]
        lines = sub.splitlines()
        stop_labels = {
            "RUC",
            "DIRECCIÓN",
            "DIRECCION",
            "EMAIL",
            "E-MAIL",
            "TELÉFONO",
            "TELEFONO",
            "ACTIVIDAD ECONÓMICA",
            "ACTIVIDAD ECONOMICA",
        }

        label_variants = ["RAZÓN SOCIAL", "RAZON SOCIAL", "NOMBRE"]
        for i, line in enumerate(lines[:80]):
            up = line.strip().upper()
            for lab in label_variants:
                if up.startswith(lab):
                    rest = re.sub(rf"^{re.escape(lab)}\s*:?\.?\s*", "", line.strip(), flags=re.IGNORECASE).strip()
                    collected = []
                    if rest:
                        rest = re.split(r"\bRUC\b", rest, maxsplit=1, flags=re.IGNORECASE)[0].strip()
                        if rest:
                            collected.append(rest)
                    for nxt in lines[i + 1:i + 15]:
                        cand = nxt.strip()
                        if not cand:
                            continue
                        cand_up = cand.upper()
                        if cand_up in stop_labels or cand_up.startswith("RUC"):
                            break
                        if cand.replace(" ", "").isdigit():
                            continue
                        if re.match(r"^DATOS\s+DEL\s+", cand_up):
                            break
                        collected.append(cand)
                    name = _clean_name(" ".join(collected))
                    if name:
                        return name
        return ""

    asegurado = _extract_name_from_section("DATOS\\s+DEL\\s+ASEGURADO")
    contratante = _extract_name_from_section("DATOS\\s+DEL\\s+CONTRATANTE")

    if asegurado:
        item["asegurado"] = asegurado
        if not item.get("colectivo_asegurado") or item.get("colectivo_asegurado") == item.get("asegurado"):
            item["colectivo_asegurado"] = asegurado
    if contratante:
        item["colectivo_asegurado"] = contratante
        if not item.get("asegurado"):
            item["asegurado"] = contratante
        elif not asegurado:
            aseg_up = (item.get("asegurado") or "").upper()
            if item.get("asegurado") != contratante and ("CORRED" in aseg_up or "BROKER" in aseg_up):
                item["asegurado"] = contratante

    if not item.get("colectivo_asegurado") or not item.get("asegurado"):
        m_rs = re.search(
            r"Raz[oó]n\s+social\s*([\s\S]{3,240}?)(?:\n|\s)+RUC\b",
            text_norm,
            re.IGNORECASE,
        )
        if m_rs:
            razon = _clean_name(m_rs.group(1))
            if razon:
                item["colectivo_asegurado"] = item.get("colectivo_asegurado") or razon
                item["asegurado"] = item.get("asegurado") or razon

    if not item.get("comision_compania_importe"):
        m_com = re.search(
            r"Importe\s+comisi[oó]n\s*(?:US\$|USD|S/\.?|S/)?\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2}))",
            text_norm,
            re.IGNORECASE,
        )
        if m_com:
            val = _normalize_amount(m_com.group(1))
            if val:
                item["comision_compania_importe"] = val

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

