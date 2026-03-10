(function () {
  if (window.currentPage !== 'anadir-poliza') return;

  const issuerEl = document.getElementById('issuer');
  const tbody = document.querySelector('#extractTable tbody');
  if (!tbody) return;

  const isPositiva = () => {
    const val = (issuerEl?.value || '').toLowerCase();
    const txt = issuerEl?.options?.[issuerEl.selectedIndex]?.text?.toLowerCase() || '';
    return val.includes('positiva') || txt.includes('positiva') || val.includes('lpv');
  };

  function extractRazonSocial(s) {
    const lines = (s || '').split(/\r?\n/).map(t => t.trim()).filter(Boolean);
    const stripTrailingInitial = v => (v || '').replace(/\s+[A-ZÁÉÍÓÚÑ]$/, '').trim();
    for (let i = 0; i < lines.length; i++) {
      const isNORS = /nombre\s+o\s+raz[oó]n\s+social\b/i.test(lines[i]);
      const isRSOnly = /raz[oó]n\s+social\b/i.test(lines[i]) && !isNORS;
      const isNYA = /nombres?\s+y\s+apellidos\b/i.test(lines[i]);
      if (isRSOnly || isNORS || isNYA) {
        const after = lines[i].replace(/(raz[oó]n\s+social|nombre\s+o\s+raz[oó]n\s+social|nombres?\s+y\s+apellidos)\s*:\s*/i, '').trim();
        if (after) {
          if (isNYA || isNORS) {
            const full = (after.endsWith(',') && i + 1 < lines.length) ? (after + ' ' + (lines[i + 1] || '')) : after;
            const seg = full.replace(/\s+/g, ' ').trim();
            const commaIdx = seg.indexOf(',');
            if (commaIdx !== -1) {
              const left = seg.slice(0, commaIdx).trim();
              const right = seg.slice(commaIdx + 1).trim();
              const t1 = left.match(/[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?/g) || [];
              const t2 = right.match(/[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?/g) || [];
              const clean1 = t1.filter(w => w.length > 1);
              const clean2 = t2.filter(w => w.length > 1);
              const leftTwo = clean1.slice(-2).join(' ');
              const rightTwo = clean2.slice(0, 2).join(' ');
              return stripTrailingInitial(`${leftTwo}, ${rightTwo}`.substring(0, 200).trim());
            }
            return stripTrailingInitial(seg.substring(0, 200).trim());
          } else {
            // Razón Social (empresa) — mantener texto, evitando arrastrar párrafos largos
            const stopIdx = after.indexOf('. ');
            const slice = stopIdx > 0 ? after.slice(0, stopIdx) : after;
            return stripTrailingInitial(slice.substring(0, 200).trim());
          }
        }
        for (let j = i + 1; j < lines.length; j++) {
          const cand = lines[j];
          if (cand && !/^(tipo de documento|ruc|nro\.?|número|departamento|distrito|provincia|direcci[oó]n)/i.test(cand)) {
            if (isNYA || isNORS) {
              const prev = lines[i].replace(/(nombres?\s+y\s+apellidos|nombre\s+o\s+raz[oó]n\s+social)\s*:\s*/i, '').trim();
              const full = (prev.endsWith(',') ? (prev + ' ' + cand) : (prev ? prev : cand));
              const seg = full.replace(/\s+/g, ' ').trim();
              const commaIdx = seg.indexOf(',');
              if (commaIdx !== -1) {
                const left = seg.slice(0, commaIdx).trim();
                const right = seg.slice(commaIdx + 1).trim();
                const t1 = left.match(/[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?/g) || [];
                const t2 = right.match(/[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?/g) || [];
                const clean1 = t1.filter(w => w.length > 1);
                const clean2 = t2.filter(w => w.length > 1);
                const leftTwo = clean1.slice(-2).join(' ');
                const rightTwo = clean2.slice(0, 2).join(' ');
                return stripTrailingInitial(`${leftTwo}, ${rightTwo}`.substring(0, 200).trim());
              }
              return stripTrailingInitial(seg.substring(0, 200).trim());
            } else {
              const stopIdx2 = cand.indexOf('. ');
              const slice2 = stopIdx2 > 0 ? cand.slice(0, stopIdx2) : cand;
              return stripTrailingInitial(slice2.substring(0, 200).trim());
            }
          }
        }
      }
      if (/señores\b/i.test(lines[i])) {
        // Tomar la siguiente línea como nombre, limpiando coma final
        const next = lines[i + 1] ? lines[i + 1].replace(/,+\s*$/, '').trim() : '';
        if (next) return next;
        // O bien la parte después de ":" en la misma línea
        const after = lines[i].split(':')[1];
        if (after && after.trim()) return after.replace(/,+\s*$/, '').trim();
      }
    }
    const inline = s.replace(/[\r\n]+/g, ' ');
    const m = inline.match(/(?:raz[oó]n\s+social|nombre\s+o\s+raz[oó]n\s+social|nombres?\s+y\s+apellidos)\s*:\s*([A-ZÁÉÍÓÚÑ0-9\.\-, &'\/]+)/i);
    if (m) {
      const v = m[1];
      if (/nombres?\s+y\s+apellidos\s*:/i.test(inline)) {
        const commaIdx = v.indexOf(',');
        if (commaIdx !== -1) {
          const left = v.slice(0, commaIdx).trim();
          const right = v.slice(commaIdx + 1).trim();
          const t1 = left.match(/[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?/g) || [];
          const t2 = right.match(/[A-ZÁÉÍÓÚÑ]+(?:'[A-ZÁÉÍÓÚÑ]+)?/g) || [];
          const leftTwo = t1.slice(-2).join(' ');
          const rightTwo = t2.slice(0, 2).join(' ');
          return `${leftTwo}, ${rightTwo}`.substring(0, 200).trim();
        }
      }
      const stopIdx = v.indexOf('. ');
      const slice = stopIdx > 0 ? v.slice(0, stopIdx) : v;
      return slice.substring(0, 200).trim();
    }
    const m2 = inline.match(/señores\s*[:,]?\s*([A-ZÁÉÍÓÚÑ0-9\.\- ,&]+?)(?:,|$)/i);
    return m2 ? m2[1].trim() : null;
  }

  function extractPrimas(s) {
    const txt = (s || '').replace(/\u00A0/g, ' ');
    const norm = v => {
      if (!v) return '';
      const raw = v.replace(/[^\d,.\-]/g, '').trim();
      if (/,/.test(raw) && /\./.test(raw)) return raw.replace(/,/g, '');
      if (/,/.test(raw) && !/\./.test(raw)) return raw.replace(/\./g, '').replace(/,/g, '.');
      return raw;
    };
    const block = txt.match(/Prima\s+Comercial[\s\S]{0,120}?([0-9][0-9\.,]*)[\s\S]{0,200}?Prima\s+Comercial\s*\+\s*IGV[\s\S]{0,120}?([0-9][0-9\.,]*)/i);
    if (block) {
      return { prima_comercial: norm(block[1]), prima_comercial_igv: norm(block[2]) };
    }
    const m1 = txt.match(/Prima\s+Comercial[\s:]*[\r\n]*[A-Z$S\/\.\s]*([0-9][0-9\.,]*)/i);
    const m2 = txt.match(/Prima\s+Comercial\s*\+\s*IGV[\s:]*[\r\n]*[A-Z$S\/\.\s]*([0-9][0-9\.,]*)/i);
    return { prima_comercial: norm(m1 && m1[1]), prima_comercial_igv: norm(m2 && m2[1]) };
  }

  function extractProformaNumero(s) {
    const txt = (s || '').replace(/\u00A0/g, ' ');
    const head = txt.match(/cup[oó]n[\s|]+n[uú]mero[\s|]+vencimiento[\s|]+monto/i);
    if (head) {
      const win = txt.slice(head.index + head[0].length, head.index + head[0].length + 2200);
      const row = win.match(/^\s*\d{1,3}\s*(?:\||\s+)\s*(\d{6,20})\s*(?:\||\s+)\s*\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b/m);
      if (row) return row[1];
      const lines = (win || '').split(/\r?\n/);
      for (const ln of lines) {
        const m = (ln || '').trim().match(/^\d{1,3}\s+(\d{6,20})\b/);
        if (m) return m[1];
      }
    }
    const n = txt.match(/N[uú]mero\s+de\s+Proforma\s*[:：]?\s*(?:\r?\n\s*)?([0-9A-Z\-]{5,30})\b/i);
    if (n) return n[1];
    const p = txt.match(/Proforma\s*N(?:ro\.?|[°º])\s*[:：]?\s*(?:\r?\n\s*)?([0-9]{6,20})\b/i);
    return p ? p[1] : null;
  }

  function normalizeDateDDMMYYYY(s) {
    const raw = (s || '').trim();
    const parts = raw.split(/[\/\-]/).map(p => p.trim()).filter(Boolean);
    if (parts.length !== 3) return raw;
    let [dd, mm, yy] = parts;
    if (yy.length === 2) yy = `20${yy}`;
    const ddi = Number(dd);
    const mmi = Number(mm);
    const yyi = Number(yy);
    if (!Number.isFinite(ddi) || !Number.isFinite(mmi) || !Number.isFinite(yyi)) return `${dd}/${mm}/${yy}`;
    return `${String(ddi).padStart(2, '0')}/${String(mmi).padStart(2, '0')}/${String(yyi).padStart(4, '0')}`;
  }

  function extractVigencias(s) {
    const txt = (s || '').replace(/\u00A0/g, ' ');
    const m0i = txt.match(/vigencia\s*[-–—]?\s*inicio\s*[:：]?\s*(?:\r?\n\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/i);
    const m0t = txt.match(/\bt(?:e|é)rmino\b\s*[:：]?\s*(?:\r?\n\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/i);
    if (m0i || m0t) {
      const out = {};
      if (m0i) out.inicio_vigencia = normalizeDateDDMMYYYY(m0i[1]);
      if (m0t) out.vencimiento = normalizeDateDDMMYYYY(m0t[1]);
      return out;
    }
    const m1 = txt.match(/vigencia\s+(?:inicia|empieza|comienza)\s*(?:el\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})[\s\S]{0,200}?\b(?:y\s+)?(?:vence|venc(?:e|imiento)|finaliza|termina)\s*(?:el\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/i);
    if (m1) return { inicio_vigencia: normalizeDateDDMMYYYY(m1[1]), vencimiento: normalizeDateDDMMYYYY(m1[2]) };
    const m2 = txt.match(/\bvigencia\s*[:：]?\s*(?:del\s*)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s*(?:al|a\s*al|-\s*)\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b/i);
    if (m2) return { inicio_vigencia: normalizeDateDDMMYYYY(m2[1]), vencimiento: normalizeDateDDMMYYYY(m2[2]) };
    const m3 = txt.match(/\bdesde\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})[\s\S]{0,120}?\bhasta\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b/i);
    if (m3) return { inicio_vigencia: normalizeDateDDMMYYYY(m3[1]), vencimiento: normalizeDateDDMMYYYY(m3[2]) };
    return null;
  }

  tbody.addEventListener('paste', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const field = td.dataset.field;
    const text = (e.clipboardData || window.clipboardData)?.getData('text') || '';
    const issuerOk = isPositiva();
    const issuerIsAuto = !((issuerEl?.value || '').toString().trim());

    if ((issuerOk || issuerIsAuto) && (/vigencia/i.test(text) || /\bt(?:e|é)rmino\b/i.test(text))) {
      const vig = extractVigencias(text);
      if (vig && (vig.inicio_vigencia || vig.vencimiento)) {
        e.preventDefault();
        const tr = td.closest('tr');
        const ivCell = tr?.querySelector('td.editable[data-field="inicio_vigencia"]');
        const veCell = tr?.querySelector('td.editable[data-field="vencimiento"]');
        if (vig.inicio_vigencia && ivCell) {
          ivCell.textContent = vig.inicio_vigencia;
          ivCell.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (vig.vencimiento && veCell) {
          veCell.textContent = vig.vencimiento;
          veCell.dispatchEvent(new Event('input', { bubbles: true }));
        }
        return;
      }
    }

    if (field === 'recibo' && (issuerOk || issuerIsAuto) && (/proforma\s*n(?:ro\.?|[°º])\b/i.test(text) || (/\bcup[oó]n\b/i.test(text) && /\bn[uú]mero\b/i.test(text) && /\bvencimiento\b/i.test(text) && /\bmonto\b/i.test(text)))) {
      const nro = extractProformaNumero(text);
      if (nro) {
        e.preventDefault();
        td.textContent = nro;
        td.dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }
    }

    if (!issuerOk) return;

    if (/raz[oó]n\s+social/i.test(text) && (field === 'colectivo_asegurado' || field === 'asegurado')) {
      e.preventDefault();
      const val = extractRazonSocial(text) || text.replace(/raz[oó]n\s+social\s*:\s*/i, '').trim();
      td.textContent = val;
      td.dispatchEvent(new Event('input', { bubbles: true }));
      return;
    }

    // (Removido) manejo especial de pegado de vigencias

    if (/prima\s+comercial/i.test(text)) {
      e.preventDefault();
      const vals = extractPrimas(text);
      const tr = td.closest('tr');
      const pcCell = tr?.querySelector('td.editable[data-field="prima_comercial"]');
      const pigvCell = tr?.querySelector('td.editable[data-field="prima_comercial_igv"]');
      if (vals.prima_comercial && pcCell) {
        pcCell.textContent = vals.prima_comercial;
        pcCell.dispatchEvent(new Event('input', { bubbles: true }));
      }
      if (vals.prima_comercial_igv && pigvCell) {
        pigvCell.textContent = vals.prima_comercial_igv;
        pigvCell.dispatchEvent(new Event('input', { bubbles: true }));
      }
      if (!vals.prima_comercial && !vals.prima_comercial_igv) {
        document.execCommand('insertText', false, text);
      }
      return;
    }

    if (field === 'prima_comercial' || field === 'prima_comercial_igv') {
      const vals = extractPrimas(text);
      if (vals.prima_comercial || vals.prima_comercial_igv) {
        e.preventDefault();
        const tr = td.closest('tr');
        const pcCell = tr?.querySelector('td.editable[data-field="prima_comercial"]');
        const pigvCell = tr?.querySelector('td.editable[data-field="prima_comercial_igv"]');
        if (pcCell && vals.prima_comercial) {
          pcCell.textContent = vals.prima_comercial;
          pcCell.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (pigvCell && vals.prima_comercial_igv) {
          pigvCell.textContent = vals.prima_comercial_igv;
          pigvCell.dispatchEvent(new Event('input', { bubbles: true }));
        }
        return;
      }
    }
  });
})();
