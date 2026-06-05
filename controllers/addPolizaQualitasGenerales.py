import re


def _clean_spaces(s: str | None) -> str:
    if not s:
        return ""
    try:
        s = s.replace("\u00A0", " ").replace("：", ":")
    except Exception:
        pass
    return re.sub(r"\s+", " ", str(s)).strip()


def _money(s: str | None) -> str | None:
    if not s:
        return None
    raw0 = _clean_spaces(s).replace("−", "-").replace("–", "-").replace("—", "-")
    raw = raw0
    neg = False
    mp = re.match(r"^\((.*)\)$", raw)
    if mp:
        neg = True
        raw = (mp.group(1) or "").strip()
    if re.match(r"^\s*-\s*", raw):
        neg = True
    raw = re.sub(r"[^\d,.\-]", "", raw)
    if not raw:
        return None
    if raw.startswith("-"):
        neg = True
    raw = raw.replace("-", "")
    try:
        if "," in raw and "." in raw:
            raw = raw.replace(",", "")
        elif raw.count(",") == 1 and raw.count(".") == 0:
            raw = raw.replace(",", ".")
        elif raw.count(",") > 1 and raw.count(".") == 0:
            parts = raw.split(",")
            raw = "".join(parts[:-1]) + "." + parts[-1]
        elif raw.count(".") > 1 and raw.count(",") == 0:
            parts = raw.split(".")
            raw = "".join(parts[:-1]) + "." + parts[-1]
        num = float(raw)
        if neg:
            num = -abs(num)
        return f"{num:.2f}"
    except Exception:
        return raw0


def _month_to_num(mon: str) -> str | None:
    if not mon:
        return None
    m = _clean_spaces(mon).upper().strip(".")
    m = re.sub(r"[^A-ZÁÉÍÓÚÑ]", "", m)
    mapping = {
        "ENE": "01",
        "ENERO": "01",
        "FEB": "02",
        "FEBRERO": "02",
        "MAR": "03",
        "MARZO": "03",
        "ABR": "04",
        "ABRIL": "04",
        "MAY": "05",
        "MAYO": "05",
        "JUN": "06",
        "JUNIO": "06",
        "JUL": "07",
        "JULIO": "07",
        "AGO": "08",
        "AGOSTO": "08",
        "SEP": "09",
        "SET": "09",
        "SETIEMBRE": "09",
        "SEPT": "09",
        "SEPTIEMBRE": "09",
        "OCT": "10",
        "OCTUBRE": "10",
        "NOV": "11",
        "NOVIEMBRE": "11",
        "DIC": "12",
        "DICIEMBRE": "12",
    }
    return mapping.get(m)


def _date_dd_mmm_yyyy_to_ddmmyyyy(s: str | None) -> str | None:
    if not s:
        return None
    raw = _clean_spaces(s).replace("-", "/")
    m = re.search(r"\b(\d{1,2})/([A-ZÁÉÍÓÚÑ]{3,10})/(\d{4})\b", raw, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(\d{1,2})\s*/\s*([A-ZÁÉÍÓÚÑ]{3,10})\s*/\s*(\d{4})\b", raw, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(\d{1,2})\s+de\s+([A-ZÁÉÍÓÚÑ]{3,20})\s+de\s+(\d{4})\b", raw, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]{3,20})\s+DE\s+(\d{4})\b", raw, re.IGNORECASE)
    if not m:
        m2 = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", raw)
        if m2:
            return f"{int(m2.group(1)):02d}/{int(m2.group(2)):02d}/{m2.group(3)}"
        return None
    dd = int(m.group(1))
    mon = _month_to_num(m.group(2))
    yyyy = m.group(3)
    if not mon:
        return None
    return f"{dd:02d}/{mon}/{yyyy}"


def _strip_accents_lower(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    return s.translate(str.maketrans("áéíóúñ", "aeioun"))


def _looks_like_person_name(s: str | None) -> bool:
    if not s:
        return False
    cand = _clean_spaces(s).upper()
    if len(cand) < 8:
        return False
    bad_tokens = {
        "INFORMACIÓN",
        "INFORMACION",
        "IMPORTANTE",
        "DOMICILIO",
        "CORREO",
        "TELÉFONO",
        "TELEFONO",
        "DISTRITO",
        "PROV",
        "PROV.",
        "DEPTO",
        "DEPART",
        "RELACIÓN",
        "RELACION",
        "CONTRATANTE",
        "ASEGURADO",
        "PÓLIZA",
        "POLIZA",
        "ENDOSO",
        "CERTIFICADO",
        "ESTIMADO",
    }
    if any(tok in cand for tok in bad_tokens):
        return False
    if not re.fullmatch(r"[A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{3,}){1,6}", cand):
        return False
    return True


def _find_marker_pos(text_low: str, marker: str) -> int:
    if not text_low:
        return -1
    m_low = marker.lower()
    pos = text_low.find(m_low)
    if pos != -1:
        return pos
    plain = _strip_accents_lower(text_low)
    pos2 = plain.find(_strip_accents_lower(marker))
    return pos2


def _extract_date_near_marker(text: str, marker: str, max_window: int = 260) -> str | None:
    pos = _find_marker_pos(_strip_accents_lower(text), marker)
    if pos == -1:
        return None
    window = text[pos: pos + max_window]
    dates = []
    for m in re.finditer(r"(\d{1,2}\s*/\s*[A-ZÁÉÍÓÚÑ]{3,10}\s*/\s*\d{4})", window, re.IGNORECASE):
        d = _date_dd_mmm_yyyy_to_ddmmyyyy(m.group(1))
        if d:
            dates.append(d)
    if not dates:
        return None
    return dates[0]


def _date_key_ddmmyyyy(d: str | None) -> int | None:
    if not d:
        return None
    try:
        dd, mm, yyyy = d.split("/")
        return int(yyyy) * 10000 + int(mm) * 100 + int(dd)
    except Exception:
        return None


def _extract_vigencia_dates(text: str) -> tuple[str | None, str | None]:
    desde = None
    hasta = None

    m_desde = re.search(
        r"Desde\s+las\s+[\d: ]+\s*(?:A|P)\.?M\.?\s*del\s*:?\s*([0-9]{1,2}/[A-ZÁÉÍÓÚÑ]{3,10}/[0-9]{4})",
        text,
        re.IGNORECASE,
    )
    if m_desde:
        desde = _date_dd_mmm_yyyy_to_ddmmyyyy(m_desde.group(1))

    m_hasta = re.search(
        r"Hasta\s+las\s+[\d: ]+\s*(?:A|P)\.?M\.?\s*del\s*:?\s*([0-9]{1,2}/[A-ZÁÉÍÓÚÑ]{3,10}/[0-9]{4})",
        text,
        re.IGNORECASE,
    )
    if m_hasta:
        hasta = _date_dd_mmm_yyyy_to_ddmmyyyy(m_hasta.group(1))

    if not desde:
        desde = _extract_date_near_marker(text, "Desde las", max_window=320)

    if not hasta:
        pos = _find_marker_pos(_strip_accents_lower(text), "Hasta las")
        if pos != -1:
            window = text[pos: pos + 420]
            cands = []
            for m in re.finditer(r"(\d{1,2}\s*/\s*[A-ZÁÉÍÓÚÑ]{3,10}\s*/\s*\d{4})", window, re.IGNORECASE):
                d = _date_dd_mmm_yyyy_to_ddmmyyyy(m.group(1))
                if d:
                    cands.append(d)
            if cands:
                hasta = max(cands, key=lambda x: _date_key_ddmmyyyy(x) or 0)
        if not hasta:
            hasta = _extract_date_near_marker(text, "Hasta las", max_window=420)

    if desde and hasta:
        k_desde = _date_key_ddmmyyyy(desde) or 0
        k_hasta = _date_key_ddmmyyyy(hasta) or 0
        if k_hasta < k_desde:
            desde, hasta = hasta, desde

    return desde, hasta


def _extract_consolidado_primas(text: str) -> dict:
    plain = _strip_accents_lower(text)
    mpos = re.search(r"consolidado\s+de\s+primas", plain, re.IGNORECASE)
    if not mpos:
        print("[qualitas_generales] consolidado_primas: NOT_FOUND")
        return {}
    pos = mpos.start()
    section = text[pos: pos + 5000]

    amounts_in_order = []
    for m in re.finditer(
        r"(?:(?:US\s*\$?)|US\$|USD|U\$|S/\.?|S\.)\s*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9,\.\s]{0,25}\s*\)?)",
        section,
        re.IGNORECASE | re.DOTALL,
    ):
        v = _money(m.group(1))
        if v:
            amounts_in_order.append(v)
    if amounts_in_order:
        print("[qualitas_generales] consolidado_amounts:", amounts_in_order)

    def _find_amount(label_re: str) -> str | None:
        m = re.search(
            label_re + r"[\s:：]*?(?:(?:US\s*\$?)|US\$|USD|U\$|S/\.?|S\.)?\s*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9,\.\s]{0,25}\s*\)?)",
            section,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return None
        raw_amount = m.group(1)
        val = _money(raw_amount)
        print(f"[qualitas_generales] consolidado_match label={label_re} raw={raw_amount!r} val={val}")
        return val

    prima_neta = _find_amount(r"Prima\s+Neta\*?")
    derecho_emision = _find_amount(r"Derecho\s+de\s+Emisi[oó]n")
    prima_comercial = _find_amount(r"Prima\s+Comercial")
    if not prima_comercial:
        prima_comercial = _find_amount(r"Sub\.?\s*Total")
    igv_18 = _find_amount(r"IGV\s*18%?")
    prima_total = _find_amount(r"Prima\s+Total")

    out = {}
    if len(amounts_in_order) >= 7:
        prima_neta = amounts_in_order[0]
        derecho_emision = amounts_in_order[1]
        prima_comercial = amounts_in_order[2]
        igv_18 = amounts_in_order[5]
        prima_total = amounts_in_order[6]

    if prima_comercial:
        out["prima_comercial"] = prima_comercial
    if prima_neta:
        out["prima_neta"] = prima_neta
    if prima_total:
        out["prima_total"] = prima_total
        out["prima_comercial_igv"] = prima_total
    elif prima_comercial and igv_18:
        try:
            out_total = f"{(float(prima_comercial) + float(igv_18)):.2f}"
            out["prima_total"] = out_total
            out["prima_comercial_igv"] = out_total
        except Exception:
            pass

    if not out.get("prima_neta") and out.get("prima_comercial"):
        try:
            out["prima_neta"] = f"{(float(out['prima_comercial']) / 1.03):.2f}"
        except Exception:
            pass

    print("[qualitas_generales] consolidado_primas:", out)
    return out


def parse_qualitas_generales(text: str) -> dict:
    t = (text or "").replace("\u00A0", " ").replace("：", ":")
    low = t.lower()

    item: dict = {}

    moneda = None
    if re.search(r"\bMONEDA\b[\s:：]*D[ÓO]LAR|DOLARES|DÓLARES", t, re.IGNORECASE):
        moneda = "US$"
    elif re.search(r"\bMONEDA\b[\s:：]*SOLES|SOL", t, re.IGNORECASE):
        moneda = "S/"
    item["moneda"] = moneda

    m_plan = re.search(r"\bPLAN\s*:\s*([A-ZÁÉÍÓÚÑ0-9 \-]{3,40})", t, re.IGNORECASE)
    if m_plan:
        item["ramos_producto"] = _clean_spaces(m_plan.group(1)).upper()

    renew_nro = None
    m_ren = re.search(r"\bRENUEVA\s*A\s*:\s*([0-9]{6,14})\b", t, re.IGNORECASE)
    if m_ren:
        renew_nro = m_ren.group(1)

    poliza = None
    m_pol = re.search(
        r"\bP[ÓO]LIZA\b[\s\S]{0,120}?\bENDOSO\b[\s\S]{0,120}?\bCERTIFICADO\b[\s\S]{0,120}?\b([0-9]{6,14})\b",
        t,
        re.IGNORECASE,
    )
    if m_pol:
        poliza = m_pol.group(1)
    if not poliza:
        m_pol2 = re.search(
            r"\bP[ÓO]LIZA\b[\s:：]*([0-9]{6,14})\b",
            t,
            re.IGNORECASE,
        )
        if m_pol2:
            poliza = m_pol2.group(1)
    if not poliza:
        pos = low.find("póliza")
        if pos == -1:
            pos = low.find("poliza")
        if pos != -1:
            window = t[max(0, pos - 60): pos + 400]
            nums = re.findall(r"\b[0-9]{6,14}\b", window)
            nums = [n for n in nums if n != renew_nro]
            if nums:
                poliza = nums[0]
    if poliza:
        item["numero_poliza"] = poliza

    asegurado = None
    m_aseg = re.search(
        r"INFORMACI[ÓO]N\s+DEL\s+ASEGURADO\s*\n\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ \.]{5,80})",
        t,
        re.IGNORECASE,
    )
    if m_aseg:
        cand = _clean_spaces(m_aseg.group(1)).upper()
        if _looks_like_person_name(cand):
            asegurado = cand

    if not asegurado:
        m_aseg2 = re.search(
            r"INFORMACI[ÓO]N\s+DEL\s+CONTRATANTE[\s\S]{0,300}?\n\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ \.]{5,80})",
            t,
            re.IGNORECASE,
        )
        if m_aseg2:
            cand = _clean_spaces(m_aseg2.group(1)).upper()
            if _looks_like_person_name(cand) and not re.search(r"\bDOMICILIO\b|\bCORREO\b|\bTEL[ÉE]FONO\b", cand, re.IGNORECASE):
                asegurado = cand

    if not asegurado:
        m_rep = re.search(
            r"\n\s*([A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{3,}){1,6})\s*\n\s*\1\s*(?:\n|$)",
            t,
            re.IGNORECASE,
        )
        if m_rep:
            cand = _clean_spaces(m_rep.group(1)).upper()
            if _looks_like_person_name(cand):
                asegurado = cand

    if not asegurado:
        for marker in ("INFORMACIÓN DEL CONTRATANTE", "INFORMACIÓN DEL ASEGURADO"):
            pos = _find_marker_pos(low, marker)
            if pos == -1:
                continue
            window = t[pos: pos + 900]
            for m in re.finditer(r"\b([A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{3,}){1,6})\b", window, re.IGNORECASE):
                cand = _clean_spaces(m.group(1)).upper()
                if _looks_like_person_name(cand):
                    asegurado = cand
                    break
            if asegurado:
                break

    if asegurado:
        item["colectivo_asegurado"] = asegurado
        item["asegurado"] = asegurado

    m_fp = re.search(r"Forma\s+de\s+Pago\s*:\s*([^\n]{3,80})", t, re.IGNORECASE)
    if m_fp:
        item["forma_pago"] = _clean_spaces(m_fp.group(1)).upper()

    desde, hasta = _extract_vigencia_dates(t)

    if desde:
        item["inicio_vigencia"] = desde
    if hasta:
        item["vencimiento"] = hasta

    m_fvp = re.search(
        r"Fecha\s+Vencimiento\s+del\s+pago\s*:\s*([0-9]{1,2}/[A-ZÁÉÍÓÚÑ]{3,10}/[0-9]{4})",
        t,
        re.IGNORECASE,
    )
    fv = None
    if m_fvp:
        fv = _date_dd_mmm_yyyy_to_ddmmyyyy(m_fvp.group(1))
    if not fv:
        fv = _extract_date_near_marker(t, "Fecha Vencimiento del pago")
    if fv:
        item["fecha_vencimiento"] = fv
        item["fecha_vecimiento"] = fv
        item["ultimo_dia_pago"] = fv

    emision = None
    m_emit = re.search(r"\bA\s+(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]{3,20})\s+DE\s+(\d{4})\b", t, re.IGNORECASE)
    if m_emit:
        emision = _date_dd_mmm_yyyy_to_ddmmyyyy(f"{m_emit.group(1)} de {m_emit.group(2)} de {m_emit.group(3)}")
    if emision:
        item["fecha_emision"] = emision

    cons = _extract_consolidado_primas(t)
    if cons:
        for k, v in cons.items():
            if v is not None and str(v).strip() != "":
                item[k] = v

    prima_comercial = None
    m_pc = re.search(r"\bPrima\s+Comercial\b[\s:：]*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9,\.]{0,20}\s*\)?)", t, re.IGNORECASE)
    if m_pc:
        prima_comercial = _money(m_pc.group(1))
    igv = None
    m_igv = re.search(r"\bIGV\b[\s\S]{0,30}?(\(?\s*(?:[-−–—]\s*)?[0-9][0-9,\.]{0,20}\s*\)?)", t, re.IGNORECASE)
    if m_igv:
        igv = _money(m_igv.group(1))
    total = None
    m_total = re.search(r"\bIMPORTE\s+TOTAL\b[\s:：]*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9,\.]{0,20}\s*\)?)", t, re.IGNORECASE)
    if not m_total:
        m_total = re.search(r"\bImporte\s+Total\b[\s:：]*(\(?\s*(?:[-−–—]\s*)?[0-9][0-9,\.]{0,20}\s*\)?)", t, re.IGNORECASE)
    if m_total:
        total = _money(m_total.group(1))

    if not item.get("prima_comercial") and prima_comercial:
        item["prima_comercial"] = prima_comercial
        try:
            val = float(prima_comercial)
            if not item.get("prima_neta"):
                item["prima_neta"] = f"{(val / 1.03):.2f}"
        except Exception:
            pass

    if not item.get("prima_total"):
        if total:
            item["prima_total"] = total
            item["prima_comercial_igv"] = total
        elif item.get("prima_comercial") and igv:
            try:
                item["prima_total"] = f"{(float(item['prima_comercial']) + float(igv)):.2f}"
                item["prima_comercial_igv"] = item["prima_total"]
            except Exception:
                pass

    if "seguro vehicular" in low or "vehicular" in low:
        item["ramo"] = "VEHICULAR"

    print(
        "[qualitas_generales] primas_final:",
        "prima_neta=", item.get("prima_neta"),
        "prima_comercial=", item.get("prima_comercial"),
        "prima_comercial_igv=", item.get("prima_comercial_igv"),
        "prima_total=", item.get("prima_total"),
    )
    return {k: v for k, v in item.items() if v is not None and str(v).strip() != ""}


def addPolizaQualitasGenerales(filepath: str) -> dict:
    try:
        import fitz
        with fitz.open(filepath) as doc:
            txt = []
            for i in range(doc.page_count):
                try:
                    txt.append(doc.load_page(i).get_text() or "")
                except Exception:
                    pass
        return parse_qualitas_generales("\n".join(txt))
    except Exception:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            out = []
            for page in reader.pages:
                try:
                    out.append(page.extract_text() or "")
                except Exception:
                    pass
            return parse_qualitas_generales("\n".join(out))
        except Exception:
            return {}

