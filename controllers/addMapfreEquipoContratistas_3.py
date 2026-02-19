import re
from datetime import datetime, timedelta


def parse_mapfre_equipo_contratistas_3(text: str):
    item = {}
    text_norm = re.sub(r"\r\n", "\n", text)

    date_pat = r"\d{2}/\d{2}/\d{4}"

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

    m_block_primas = re.search(
        r"Prima\s+Comercial.*?Prima\s+Comercial\s*\+\s*I\.?G\.?V[^\n]*\n\s*([\d,]+\.\d{2})\s*\n\s*([\d,]+\.\d{2})",
        text_norm,
        re.IGNORECASE | re.DOTALL,
    )
    if m_block_primas:
        val_pc = m_block_primas.group(1).replace(",", "")
        val_pigv = m_block_primas.group(2).replace(",", "")
        item["prima_comercial"] = val_pc
        item["prima_comercial_igv"] = val_pigv
        item["prima_total"] = val_pigv
        item["monto"] = val_pigv
        try:
            pc_float = float(val_pc)
            pn_float = pc_float / 1.03
            item["prima_neta"] = f"{pn_float:.2f}"
        except Exception:
            pass
    else:
        m_pc = re.search(
            r"Prima\s+Comercial\s+([\d,]+\.\d{2})",
            text_norm,
            re.IGNORECASE,
        )
        if m_pc:
            val_pc = m_pc.group(1).replace(",", "")
            item["prima_comercial"] = val_pc
            try:
                pc_float = float(val_pc)
                pn_float = pc_float / 1.03
                item["prima_neta"] = f"{pn_float:.2f}"
            except Exception:
                pass

        m_pigv = re.search(
            r"Prima\s+Comercial\s*\+\s*I\.?G\.?V\.?\s+([\d,]+\.\d{2})",
            text_norm,
            re.IGNORECASE,
        )
        if m_pigv:
            val_pigv = m_pigv.group(1).replace(",", "")
            item["prima_comercial_igv"] = val_pigv
            item["prima_total"] = val_pigv
            item["monto"] = val_pigv

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

    m_prod = re.search(r"PRODUCTO\s*[:\.]?\s*(.*)", text_norm, re.IGNORECASE)
    if m_prod:
        item["producto"] = m_prod.group(1).strip()
    else:
        item["producto"] = "EQUIPO DE CONTRATISTAS"

    item["ramo"] = "EQUIPO DE CONTRATISTAS"

    return item

