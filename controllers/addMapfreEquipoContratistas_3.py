import re
from datetime import datetime, timedelta


def parse_mapfre_equipo_contratistas_3(text: str):
    item = {}
    text_norm = re.sub(r"\r\n", "\n", text)

    date_pat = r"\d{2}/\d{2}/\d{4}"

    def _normalize_amount(val: str):
        if not val:
            return None
        s = val.strip()
        s = re.sub(r"[^\d,\.]", "", s)
        if not s:
            return None
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
        return s

    money = r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"

    m_pol = re.search(r"P[ÓO]LIZA\s*\n\s*(\d{10,})", text_norm, re.IGNORECASE)
    if not m_pol:
        m_pol = re.search(
            r"P[ÓO]LIZA\s*[:#\.]?\s*(\d{10,})", text_norm, re.IGNORECASE
        )
    if not m_pol:
        m_pol = re.search(
            r"P[ÓO]LIZA.*?\n.*?(\d{10,})",
            text_norm,
            re.IGNORECASE | re.DOTALL,
        )
    if not m_pol:
        m_pol = re.search(
            r"P[ÓO]LIZA\s+(\d{10,})", text_norm, re.IGNORECASE
        )
    if not m_pol:
        m_pol = re.search(
            r"P[ÓO]LIZA.*?(\d{10,})",
            text_norm,
            re.IGNORECASE | re.DOTALL,
        )
    if m_pol:
        item["numero_poliza"] = m_pol.group(1)

    m_vig = re.search(
        rf"({date_pat})\s+\d{{2}}:\d{{2}}\s*Hrs?\.?.*?({date_pat})",
        text_norm,
        re.IGNORECASE | re.DOTALL,
    )
    if not m_vig:
        m_vig = re.search(
            rf"VIGENCIA\s+DE\s+P[ÓO]LIZA\s*({date_pat})\s*-\s*({date_pat})",
            text_norm,
            re.IGNORECASE,
        )
    if not m_vig:
        m_vig = re.search(
            rf"VIGENCIA.*?({date_pat})\s*-\s*({date_pat})",
            text_norm,
            re.IGNORECASE | re.DOTALL,
        )
    if m_vig:
        item["inicio_vigencia"] = m_vig.group(1)
        item["fin_vigencia"] = m_vig.group(2)
        item["vencimiento"] = m_vig.group(2)
        item["fecha_vencimiento"] = m_vig.group(2)

    m_emision = re.search(
        rf"F\s*\.?\s*EMISI[ÓO]N\s*[:\.]?\s*({date_pat})",
        text_norm,
        re.IGNORECASE,
    )
    if not m_emision:
        m_emision = re.search(
            rf"F\s*\.?\s*EMISI[ÓO]N.*?({date_pat})",
            text_norm,
            re.IGNORECASE | re.DOTALL,
        )
    if m_emision:
        item["fecha_emision"] = m_emision.group(1)
        try:
            fe_obj = datetime.strptime(item["fecha_emision"], "%d/%m/%Y")
            udp_obj = fe_obj + timedelta(days=15)
            item["ultimo_dia_pago"] = udp_obj.strftime("%d/%m/%Y")
        except Exception:
            pass

    m_mon = re.search(
        r"MONEDA\s*[:\.]?\s*(S/|S/\.|SOLES|US\$|USD|DOLARES)",
        text_norm,
        re.IGNORECASE | re.DOTALL,
    )
    if m_mon:
        val = m_mon.group(1).upper()
        if "US" in val or "DOLAR" in val:
            item["moneda"] = "US$"
        else:
            item["moneda"] = "S/"
    else:
        if re.search(r"\bS/\.", text_norm) or "SOLES" in text_norm:
            item["moneda"] = "S/"
        elif "US$" in text_norm or "DOLARES" in text_norm:
            item["moneda"] = "US$"

    rucs = re.findall(r"RUC\s*:?\s*(\d{11})", text_norm)
    if not rucs:
        rucs = re.findall(r"\b20\d{9}\b", text_norm)
    for ruc in rucs:
        if ruc != "20418896915":
            item["ruc_contratante"] = ruc
            break

    m_block = re.search(
        r"DATOS\s+DEL\s+CONTRATANTE", text_norm, re.IGNORECASE
    )
    if m_block:
        start_idx = m_block.start()
        subtext = text_norm[start_idx:]
        lines = subtext.splitlines()
        found_name = False
        for i, line in enumerate(lines):
            if i > 25:
                break
            if "NOMBRE" in line.upper():
                same_line_content = re.sub(
                    r"^.*?NOMBRE\s*[:\.]?\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                ).strip()
                clean_same_line = re.sub(
                    r"\s+(?:RUC\s*)?\d{11}\s*$",
                    "",
                    same_line_content,
                    flags=re.IGNORECASE,
                ).strip()
                check_sl = (
                    clean_same_line.replace(" ", "")
                    .replace("-", "")
                    .replace(".", "")
                )
                if len(check_sl) > 2 and any(c.isalpha() for c in check_sl):
                    item["colectivo_asegurado"] = clean_same_line
                    item["asegurado"] = clean_same_line
                    found_name = True
                    break
                for j in range(i + 1, len(lines)):
                    if j > i + 12:
                        break
                    candidate = lines[j].strip()
                    if not candidate:
                        continue
                    cand_upper = candidate.upper()
                    invalid_keywords = [
                        "RUC",
                        "EMAIL",
                        "TELEFONO",
                        "ACTIVIDAD ECONOMICA",
                        "COD.",
                    ]
                    is_label = False
                    for kw in invalid_keywords:
                        if (
                            cand_upper == kw
                            or cand_upper.startswith(kw + ":")
                            or cand_upper.startswith(kw + " ")
                        ):
                            is_label = True
                            break
                    if is_label:
                        continue
                    if cand_upper in ["DIRECCION", "DIRECCIÓN"]:
                        continue
                    if "RUC" in cand_upper and len(cand_upper) < 20:
                        continue
                    clean_cand = re.sub(
                        r"\s+(?:RUC\s*)?\d{11}\s*$",
                        "",
                        candidate,
                        flags=re.IGNORECASE,
                    ).strip()
                    check_cand = (
                        clean_cand.replace(" ", "")
                        .replace("-", "")
                        .replace(".", "")
                    )
                    has_letters = any(c.isalpha() for c in check_cand)
                    if not has_letters:
                        continue
                    item["colectivo_asegurado"] = clean_cand
                    item["asegurado"] = clean_cand
                    found_name = True
                    break
                if found_name:
                    break

    if "colectivo_asegurado" not in item:
        m_sen = re.search(
            r"Señor\(a\)[^\n:]{0,60}:\s*(?:\n\s*)?([^\n]{3,120})",
            text_norm,
            re.IGNORECASE,
        )
        if m_sen:
            cand = (m_sen.group(1) or "").strip()
            cand = re.sub(r"\s+RUC.*$", "", cand, flags=re.IGNORECASE).strip()
            if cand:
                item["colectivo_asegurado"] = cand
                item["asegurado"] = cand

    m_block_primas = re.search(
        r"Prima\s+Comercial.*?Prima\s+Comercial\s*\+\s*I\.?G\.?V[^\n]*\n\s*([\d,]+\.\d{2})\s*\n\s*([\d,]+\.\d{2})",
        text_norm,
        re.IGNORECASE | re.DOTALL,
    )
    if m_block_primas:
        val_pc = _normalize_amount(m_block_primas.group(1))
        val_pigv = _normalize_amount(m_block_primas.group(2))
        if val_pc:
            item["prima_comercial"] = val_pc
        if val_pigv:
            item["prima_comercial_igv"] = val_pigv
            item["prima_total"] = val_pigv
            item["monto"] = val_pigv
        try:
            if val_pc:
                pc_float = float(val_pc)
                pn_float = pc_float / 1.03
                item["prima_neta"] = f"{pn_float:.2f}"
        except Exception:
            pass
    else:
        m_pc = re.search(
            r"Prima\s+Comercial(?!\s*\+)[\s\S]{0,120}?" + money,
            text_norm,
            re.IGNORECASE,
        )
        if m_pc:
            val_pc = _normalize_amount(m_pc.group(1))
            if val_pc:
                item["prima_comercial"] = val_pc
            try:
                if val_pc:
                    pc_float = float(val_pc)
                    pn_float = pc_float / 1.03
                    item["prima_neta"] = f"{pn_float:.2f}"
            except Exception:
                pass

        m_pigv = re.search(
            r"Prima\s+Comercial\s*\+\s*I\.?\s*G\.?\s*V\.?[\s\S]{0,60}?" + money,
            text_norm,
            re.IGNORECASE,
        )
        if m_pigv:
            val_pigv = _normalize_amount(m_pigv.group(1))
            if val_pigv:
                item["prima_comercial_igv"] = val_pigv
                item["prima_total"] = val_pigv
                item["monto"] = val_pigv

    if "prima_comercial" not in item or "prima_total" not in item:
        m_tbl = re.search(
            r"PRIMA\s+COMERCIAL[\s\S]{0,120}?TOTAL([\s\S]{0,1200})",
            text_norm,
            re.IGNORECASE,
        )
        if m_tbl:
            block = m_tbl.group(1)
            block = re.split(
                r"CRONOGRAMA\s+DE\s+PAGO",
                block,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            nums = re.findall(money, block)
            if nums:
                if "prima_comercial" not in item:
                    val_pc = _normalize_amount(nums[0])
                    if val_pc:
                        item["prima_comercial"] = val_pc
                if len(nums) >= 3:
                    igv_val = _normalize_amount(nums[1])
                    tot_val = _normalize_amount(nums[2])
                    if igv_val and "igv" not in item:
                        item["igv"] = igv_val
                    if tot_val and "prima_total" not in item:
                        item["prima_total"] = tot_val
                    if tot_val and "prima_comercial_igv" not in item:
                        item["prima_comercial_igv"] = tot_val
                    if tot_val and "monto" not in item:
                        item["monto"] = tot_val
                elif len(nums) == 2:
                    tot_val = _normalize_amount(nums[1])
                    if tot_val and "prima_total" not in item:
                        item["prima_total"] = tot_val
                    if tot_val and "prima_comercial_igv" not in item:
                        item["prima_comercial_igv"] = tot_val
                    if tot_val and "monto" not in item:
                        item["monto"] = tot_val

    val_pc_for_calc = item.get("prima_comercial")
    if val_pc_for_calc and "prima_neta" not in item:
        try:
            pc_float = float(val_pc_for_calc)
            pn_float = pc_float / 1.03
            item["prima_neta"] = f"{pn_float:.2f}"
        except Exception:
            pass

    m_com = re.search(
        r"IMPORTE DE LA COMISION\s+([\d,]+\.\d{2})",
        text_norm,
        re.IGNORECASE,
    )
    if m_com:
        item["comision_compania_importe"] = m_com.group(1).replace(",", "")

    m_recibo = re.search(
        r"NRO\.?\s*RECIBO.*?(\d{7,})",
        text_norm,
        re.IGNORECASE | re.DOTALL,
    )
    if m_recibo:
        item["recibo"] = m_recibo.group(1)

    if not item.get("fecha_vecimiento"):
        m_fv = re.search(
            r"CRONOGRAMA\s+DE\s+PAGO[\s\S]{0,1500}?(\d{2}/\d{2}/\d{4})",
            text_norm,
            re.IGNORECASE,
        )
        if m_fv:
            item["fecha_vecimiento"] = m_fv.group(1)

    #m_prod = re.search(r"PRODUCTO\s*[:\.]?\s*(.*)", text_norm, re.IGNORECASE)
    #if m_prod:
        #item["producto"] = m_prod.group(1).strip()
    #else:
        #item["producto"] = "EQUIPO DE CONTRATISTAS"

    item["ramo"] = "EQUIPO DE CONTRATISTAS"

    return item

