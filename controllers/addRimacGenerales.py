import re
from typing import Dict, Optional


def _extract_poliza(text: str) -> Optional[str]:
    pats = [r"pol[ií]za\s*([0-9]{3,6})\s*-\s*([0-9]{5,12})", r"p[oó]liza\s*([0-9]{3,6})\s*-\s*([0-9]{5,12})"]
    for p in pats:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return f"{m.group(1)} - {m.group(2)}"
    return None

def _extract_recibo_documentos_generados(text: str) -> Optional[str]:
    m = re.search(r"documento(?:s)?\s+generad(?:o|os)", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        window = text[m.end(): m.end() + 1200]
        nums = re.findall(r"\b(\d{6,15})\b", window)
        if nums:
            return nums[0]
    m2 = re.search(r"documentos?\s+generados?\s*[:\-]?\s*(\d{6,15})", text, flags=re.IGNORECASE)
    if m2:
        return m2.group(1)
    m3 = re.search(r"cronograma", text, flags=re.IGNORECASE)
    if m3:
        window = text[m3.end(): m3.end() + 2000]
        nums = re.findall(r"\b(\d{6,15})\b", window)
        if nums:
            return nums[0]
    return None

def _normalize_amount(s: str | None) -> Optional[str]:
    if not s:
        return None
    val = (s or "").strip()
    val = re.sub(r"[^\d\.,]", "", val)
    if not val:
        return None
    if "," in val and "." in val:
        if val.rfind(",") > val.rfind("."):
            val = val.replace(".", "").replace(",", ".")
        else:
            val = val.replace(",", "")
    elif "," in val and "." not in val:
        val = val.replace(",", ".")
    try:
        return f"{float(val):.2f}"
    except Exception:
        return val

def _extract_moneda(text: str) -> Optional[str]:
    cerca_neta = re.search(r"prima\s+neta\*?.{0,60}(US\$|USD|\$|S\/\.?|S\/|S\.)", text, flags=re.IGNORECASE | re.DOTALL)
    if cerca_neta:
        cur = cerca_neta.group(1).upper()
        if "US" in cur or "$" in cur:
            return "US$"
        return "S/."
    cerca_total = re.search(r"prima\s+total.{0,60}(US\$|USD|\$|S\/\.?|S\/|S\.)", text, flags=re.IGNORECASE | re.DOTALL)
    if cerca_total:
        cur = cerca_total.group(1).upper()
        if "US" in cur or "$" in cur:
            return "US$"
        return "S/."
    if re.search(r"US\$|USD|\$", text, flags=re.IGNORECASE):
        return "US$"
    if re.search(r"S\/\.?|S\.", text, flags=re.IGNORECASE):
        return "S/."
    return None

def _extract_primas(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    money = r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"

    t = text or ""

    m_neta = re.search(r"prima\s+neta\*?[^0-9]{0,60}" + money, t, flags=re.IGNORECASE | re.DOTALL)
    if m_neta:
        out["prima_neta"] = _normalize_amount(m_neta.group(1)) or ""

    m_cons = re.search(r"consolidado\s+de\s+primas", t, flags=re.IGNORECASE)
    if m_cons:
        window = t[m_cons.end() : m_cons.end() + 3500]
        m_pc = re.search(r"prima\s+comercial\s*[:：]?\s*" + money, window, flags=re.IGNORECASE | re.DOTALL)
        if m_pc:
            out["prima_comercial"] = _normalize_amount(m_pc.group(1)) or ""

        m_igv = re.search(r"I\.?G\.?V\.?\s*[:：]?\s*" + money, window, flags=re.IGNORECASE | re.DOTALL)
        igv_val = _normalize_amount(m_igv.group(1)) if m_igv else None
        if igv_val:
            out["igv"] = igv_val

        m_total = re.search(
            r"prima\s+comercial\s*\+\s*I\.?G\.?V\.?[\s\S]{0,60}?" + money,
            window,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not m_total:
            m_total = re.search(
                r"prima\s+comercial\s*\+\s*igv[\s\S]{0,60}?" + money,
                window,
                flags=re.IGNORECASE | re.DOTALL,
            )
        if m_total:
            val = _normalize_amount(m_total.group(1)) or ""
            if val:
                out["prima_total"] = val
                out["prima_comercial_igv"] = val

    if "prima_comercial" not in out:
        m_conf = re.search(r"primas?\s+por\s+conformaci[oó]n", t, flags=re.IGNORECASE)
        if m_conf:
            window = t[m_conf.end() : m_conf.end() + 2500]
            nums = re.findall(money, window)
            vals = []
            for n in nums:
                nn = _normalize_amount(n)
                if nn:
                    vals.append(nn)
            try:
                floats = [float(v) for v in vals]
            except Exception:
                floats = []
            if floats:
                pc = f"{min(floats):.2f}"
                out["prima_comercial"] = pc
                if len(floats) >= 2:
                    tot = f"{max(floats):.2f}"
                    out.setdefault("prima_total", tot)
                    out.setdefault("prima_comercial_igv", tot)

    pos_pc = re.search(r"prima\s+comercial", t, flags=re.IGNORECASE)
    pos_tot = re.search(r"prima\s+total", t, flags=re.IGNORECASE)
    if pos_pc and "prima_comercial" not in out:
        start = pos_pc.end()
        end = pos_tot.start() if pos_tot and pos_tot.start() > start else start + 600
        window = t[start:end]
        nums = re.findall(money, window)
        if nums:
            try:
                cand_vals = [float((_normalize_amount(n) or "0").replace(",", ".")) for n in nums]
                val = min(cand_vals) if len(cand_vals) >= 2 else cand_vals[-1]
                out["prima_comercial"] = f"{val:.2f}"
            except Exception:
                out["prima_comercial"] = _normalize_amount(nums[-1]) or ""

    if "prima_total" not in out:
        m_total = re.search(r"prima\s+total[^0-9]{0,60}" + money, t, flags=re.IGNORECASE | re.DOTALL)
        if m_total:
            val = _normalize_amount(m_total.group(1)) or ""
            if val:
                out["prima_comercial_igv"] = val
                out["prima_total"] = val

    if "prima_total" not in out:
        m_total_alt = re.search(r"prima\s+comercial\s*\+\s*I\.?G\.?V\.?[^0-9]{0,60}" + money, t, flags=re.IGNORECASE | re.DOTALL)
        if m_total_alt:
            val = _normalize_amount(m_total_alt.group(1)) or ""
            if val:
                out["prima_total"] = val
                out["prima_comercial_igv"] = val

    try:
        pc = float(str(out.get("prima_comercial") or "").strip() or "0")
        igv = float(str(out.get("igv") or "").strip() or "0")
        tot = float(str(out.get("prima_total") or "").strip() or "0")
        if pc > 0 and igv > 0:
            calc = pc + igv
            if tot <= pc + 0.01 or abs(calc - tot) > 0.02:
                out["prima_total"] = f"{calc:.2f}"
                out["prima_comercial_igv"] = f"{calc:.2f}"
    except Exception:
        pass

    if out.get("prima_comercial") and not out.get("prima_neta"):
        try:
            pc = float(out["prima_comercial"])
            out["prima_neta"] = f"{(pc / 1.03):.2f}"
        except Exception:
            pass
    elif "prima_comercial" not in out and "prima_neta" in out:
        try:
            pn = float(out["prima_neta"])
            out["prima_comercial"] = f"{pn * 1.03:.2f}"
        except Exception:
            pass

    return {k: v for k, v in out.items() if v}

def _extract_vigencia(text: str) -> Optional[Dict[str, str]]:
    m = re.search(
        r"vigencia\s*[:：]?\s*(?:del\s*)?(\d{1,2}/\d{1,2}/\d{4})\s*(?:al|-\s*)\s*(\d{1,2}/\d{1,2}/\d{4})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        return {"inicio_vigencia": m.group(1), "vencimiento": m.group(2)}
    pos = re.search(r"vigencia", text, flags=re.IGNORECASE)
    if pos:
        window = text[pos.end() : pos.end() + 200]
        dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", window)
        if len(dates) >= 2:
            return {"inicio_vigencia": dates[0], "vencimiento": dates[1]}
    return None

def _extract_fecha_emision(text: str) -> Optional[str]:
    m = re.search(
        r"fecha\s+emisi[oó]n(?:\s*[:：]\s*){0,5}[\s\S]{0,120}?(\d{1,2}/\d{1,2}/\d{4})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1)
    pos = re.search(r"fecha\s+emisi[oó]n", text, flags=re.IGNORECASE)
    if pos:
        window = text[pos.end() : pos.end() + 300]
        d = re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", window)
        if d:
            return d.group(0)
    return None

def _extract_primera_fecha_vencimiento(text: str) -> Optional[str]:
    m = re.search(r"fecha\s+de?\s*vencim(?:iento)?", text, flags=re.IGNORECASE)
    if m:
        window = text[m.end(): m.end() + 1200]
        dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", window)
        if dates:
            return dates[0]
    m2 = re.search(r"documentos?\s+generados?", text, flags=re.IGNORECASE)
    if m2:
        window = text[m2.end(): m2.end() + 1200]
        dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", window)
        if dates:
            return dates[0]
    return None

def _extract_contratante(text: str) -> Optional[str]:
    # 1) Patrón principal: entre "Contratante :" y "Profesión" (tolerante a saltos y espacios)
    m_global = re.search(r"contratante\s*[:：]\s*(.+?)\bprofesi[oó]n\b", text, flags=re.IGNORECASE | re.DOTALL)
    if m_global:
        block = m_global.group(1)
        for piece in block.splitlines():
            s = piece.strip()
            if s and s not in ("/",) and not s.startswith("S/"):
                return re.sub(r"\s+", " ", s).strip(" :\t\r\n")

    # 2) Si no se halló, acotar al bloque "Condiciones Particulares" y repetir
    seg = text
    mcp = re.search(r"condiciones?\s+particulares", text, flags=re.IGNORECASE)
    if mcp:
        seg = text[mcp.start(): mcp.start() + 2000]

    val = None
    m_between = re.search(r"contratante\s*[:：]\s*(.+?)\bprofesi[oó]n\b", seg, flags=re.IGNORECASE | re.DOTALL)
    if m_between:
        cand = m_between.group(1)
        first_line = ""
        for piece in cand.splitlines():
            s = piece.strip()
            if s:
                first_line = s
                break
        if first_line and first_line not in ("/",) and not first_line.startswith("S/"):
            val = re.sub(r"\s+", " ", first_line).strip(" :\t\r\n")

    if not val:
        m1 = re.search(r"contratante\s*[:：]?\s*([^\n\r]+)", seg, flags=re.IGNORECASE)
        if m1:
            val = m1.group(1)
        else:
            m2 = re.search(r"contratante\s*[:：]?\s*([\s\S]{1,120})", seg, flags=re.IGNORECASE)
            val = m2.group(1).splitlines()[0] if m2 else None
    if not val:
        mp = re.search(r"pol[ií]za\s*[0-9]{3,6}\s*-\s*[0-9]{5,12}", text, flags=re.IGNORECASE)
        if mp:
            tail = text[mp.end():]
            for line in tail.splitlines():
                s = line.strip()
                if not s:
                    continue
                if re.fullmatch(r"contratante\.?", s, flags=re.IGNORECASE):
                    break
                if re.fullmatch(r"\d{4,}", s):
                    continue
                if s == "/" or s.startswith("S/"):
                    continue
                if re.search(r"\b(contratante|d\.?n\.?i\.?|r\.?u\.?c\.?|asegurad[oa]|profesi[oó]n)\b", s, flags=re.IGNORECASE):
                    continue
                if re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+(?:\s+[A-Za-zÁÉÍÓÚÑáéíóúñ]+){1,}", s):
                    val = s
                    break
    if not val:
        lines = [ln.strip() for ln in text.splitlines()]
        for i, ln in enumerate(lines):
            if re.fullmatch(r"contratante\.?", ln, flags=re.IGNORECASE):
                j = i - 1
                while j >= 0 and not lines[j]:
                    j -= 1
                if j >= 0:
                    cand = lines[j]
                    if cand and not re.fullmatch(r"\d{4,}", cand) and not re.search(r"\b(d\.?n\.?i\.?|r\.?u\.?c\.?|asegurad[oa]|profesi[oó]n)\b", cand, flags=re.IGNORECASE):
                        val = cand
                        break
    if val:
        val = re.split(r"\b(profesi[oó]n|d\.?n\.?i\.?|r\.?u\.?c\.?|asegurad[oa])\b", val, flags=re.IGNORECASE)[0]
        val = re.sub(r"\s+", " ", val).strip(" :\t\r\n")
        if val:
            return val
    return None


def parse_rimac_generales(text: str) -> Dict[str, str]: 
    low = text.lower()
    pol = _extract_poliza(text) or ""
    ramo = "VEHICULAR" if "vehicul" in low else ("SALUD" if "salud" in low else "")
    recibo = _extract_recibo_documentos_generados(text) or ""
    contratante = _extract_contratante(text) or ""
    if contratante.strip() in ("/", "S/"):
        contratante = ""

    item = {
        "numero_poliza": pol,
        "recibo": recibo,
        "ramo": ramo,
        "cia": "Rimac",
    }

    try:
        primas = _extract_primas(text)
        if primas:
            item.update(primas)
    except Exception:
        pass

    try:
        mon = _extract_moneda(text)
        if mon:
            item["moneda"] = mon
    except Exception:
        pass

    try:
        vig = _extract_vigencia(text)
        if vig:
            item.update(vig)
    except Exception:
        pass

    try:
        fe = _extract_fecha_emision(text)
        if fe:
            item["fecha_emision"] = fe
    except Exception:
        pass

    try:
        fv = _extract_primera_fecha_vencimiento(text)
        if fv:
            item["fecha_vencimiento"] = fv
    except Exception:
        pass

    if contratante:
        item["contratante"] = contratante
        item["colectivo_asegurado"] = contratante

    try:
        print("[rimac] numero_poliza:", pol)
        print("[rimac] recibo:", recibo)
        print("[rimac] contratante:", contratante if contratante else "(vacio)")
        if item.get("moneda"):
            print("[rimac] moneda:", item.get("moneda"))
        if item.get("prima_neta"):
            print("[rimac] prima_neta:", item.get("prima_neta"))
        if item.get("prima_comercial"):
            print("[rimac] prima_comercial:", item.get("prima_comercial"))
        if item.get("prima_comercial_igv"):
            print("[rimac] prima_total(+IGV):", item.get("prima_comercial_igv"))
        if item.get("inicio_vigencia") or item.get("vencimiento"):
            print("[rimac] vigencia:", item.get("inicio_vigencia"), "-", item.get("vencimiento"))
        if item.get("fecha_emision"):
            print("[rimac] fecha_emision:", item.get("fecha_emision"))
        if item.get("fecha_vencimiento"):
            print("[rimac] fecha_vencimiento:", item.get("fecha_vencimiento"))
    except Exception:
        pass

    return {k: v for k, v in item.items() if v}
