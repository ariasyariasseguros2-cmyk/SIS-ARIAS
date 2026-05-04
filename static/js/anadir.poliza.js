(function () {
  // Elementos principales
  const fileEl = document.getElementById('pdfFile');
  const issuerEl = document.getElementById('issuer');
  const btnUpload = document.getElementById('btnUpload');
  const btnSave = document.getElementById('btnSave');
  const tbody = document.querySelector('#extractTable tbody');
  const hint = document.getElementById('extractHint');
  const subAgenteTopEl = document.getElementById('subAgenteTop');
  const ejecutivoTopEl = document.getElementById('ejecutivoTop');
  const estadoTopEl = document.getElementById('estadoTop');
  const tipoPagoTopEl = document.getElementById('tipoPagoTop');
  const tipoDocTopEl = document.getElementById('tipoDocTop'); // Referencia al input de Tipo Doc
  const nroOperacionTopEl = document.getElementById('nroOperacionTop'); // NUEVO: Nro Operación global
  const endosatarioTopEl = document.getElementById('endosatarioTop'); // NUEVO
  const tipoVigenciaTopEl = document.getElementById('tipoVigenciaTop'); // NUEVO
  const aseguradaTopEl = document.getElementById('aseguradaTop'); // Campo superior de asegurada (texto)
  // const motivoTopEl = document.getElementById('motivoTop'); // Campo superior de motivo (texto)
  const anexosFilesEl = document.getElementById('anexosFiles'); // NUEVO: Input de anexos
  const anexosListEl = document.getElementById('anexosList'); // NUEVO: Lista de anexos
  const facturasFilesEl = document.getElementById('facturasFiles');
  const facturasListEl = document.getElementById('facturasList');
  // Campos de comisiones (superior)
  const pctComCompaniaEl   = document.getElementById('pctComCompania');
  const impComCompaniaEl   = document.getElementById('impComCompania');
  const pctComSubAgenteEl  = document.getElementById('pctComSubAgente');
  const impComSubAgenteEl  = document.getElementById('impComSubAgente');
  // Botones adicionales
  const btnClear = document.getElementById('btnClear');
  const btnAgregarPoliza = document.getElementById('btnAgregarPoliza');

  let subAgenteEl = subAgenteTopEl || document.getElementById('subAgente');
  let extractedItems = [];
  let allAnexos = []; // NUEVO: Acumulador de archivos anexos
  let allFacturas = [];
  let rowFacturasMap = new Map();
  let cuotaFacturaFileMap = new Map();
  let autoSaveTimer = null;
  const AUTO_SAVE_ENABLED = false;
  let isSaving = false;
  let lastUploadedFilename = null;
  let productsCache = null;
  let tipoVigenciaManualOverride = false;
  try { if (btnSave) btnSave.setAttribute('type', 'button'); } catch (e) {}

  function setIssuerFromProvider(provider) {
    if (!issuerEl || !provider) return;
    const prov = String(provider || '').toLowerCase();
    const opts = Array.from(issuerEl.options || []);
    let candidates = [];

    if (prov === 'pacifico' || prov === 'pacifico_salud') {
      candidates = ['pacifico'];
    } else if (prov === 'sanitas') {
      candidates = ['sanitas'];
    } else if (prov === 'positiva' || prov === 'lpv-vida-ley' || prov === 'lpv-pension' || prov === 'lpv-salud') {
      candidates = ['lpv-salud', 'lpv-pension', 'lpv-vida-ley', 'positiva'];
    } else if (prov === 'protecta' || prov === 'proctecta') {
      candidates = ['proctecta'];
    } else if (prov === 'mapfre' || prov === 'mapfre-vida-ley' || prov === 'mapfre-vehicular' || prov === 'mapfre-equipo-contratistas') {
      candidates = ['mapfre-vida-ley', 'mapfre'];
    } else if (prov === 'crecer' || prov === 'vida-ley-crecer') {
      candidates = ['crecer'];
    }

    for (const slug of candidates) {
      const opt = opts.find(o => (o.value || '').toLowerCase() === slug);
      if (opt) {
        issuerEl.value = opt.value;
        break;
      }
    }
  }

  // Ventana modal de carga (Bootstrap) y alternativa con SweetAlert2
  const loadingModalEl = document.getElementById('loadingModal');
  const loadingModalMsgEl = document.getElementById('loadingModalMsg');
  const loadingModalElapsedEl = document.getElementById('loadingModalElapsed');
  let loadingModal, loadingInterval = null;
  if (loadingModalEl && window.bootstrap) {
    loadingModal = new bootstrap.Modal(loadingModalEl, { backdrop: 'static', keyboard: false });
  }
  function showLoading(msg) {
    if (!loadingModal) return;
    if (msg && loadingModalMsgEl) loadingModalMsgEl.textContent = msg;
    loadingModal.show();
    const start = performance.now();
    clearInterval(loadingInterval);
    loadingInterval = setInterval(() => {
      const secs = ((performance.now() - start) / 1000).toFixed(1);
      if (loadingModalElapsedEl) loadingModalElapsedEl.textContent = `${secs}s`;
    }, 100);
  }
  function hideLoading() {
    if (!loadingModal) return;
    clearInterval(loadingInterval);
    loadingInterval = null;
    loadingModal.hide();
  }

  // SweetAlert2 como preferencia
  let swalInterval = null;
  function openLoadingSwal(msg) {
    if (window.Swal) {
      Swal.fire({
        title: msg || 'Procesando PDF…',
        html: `
          <div class="d-flex align-items-center gap-3">
            <span class="spinner-border text-primary" role="status" aria-hidden="true"></span>
            <div>Tiempo transcurrido: <b id="swalElapsed">0.0s</b></div>
          </div>
        `,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
          const start = performance.now();
          Swal.showLoading();
          clearInterval(swalInterval);
          swalInterval = setInterval(() => {
            const secs = ((performance.now() - start) / 1000).toFixed(1);
            const el = Swal.getHtmlContainer()?.querySelector('#swalElapsed');
            if (el) el.textContent = `${secs}s`;
          }, 100);
        },
        willClose: () => {
          clearInterval(swalInterval);
          swalInterval = null;
        }
      });
    } else {
      // Fallback al modal Bootstrap si no hay Swal
      showLoading(msg || 'Procesando PDF…');
    }
  }
  function closeLoadingSwal() {
    if (window.Swal) {
      Swal.close();
    } else {
      hideLoading();
    }
  }

  // render() y normalizeItem
  function ensureSubAgente() {
    subAgenteEl = document.getElementById('subAgente');
    if (subAgenteEl) return;

    const host = Array.from(document.querySelectorAll('.card .card-body'))
      .find(el => el.textContent.toLowerCase().includes('cliente seleccionado'));
    if (!host) return;

  }

  ensureSubAgente();

  function populateSubAgenteOptions() {
    const el = subAgenteTopEl || document.getElementById('subAgente');
    if (!el) return;
    const base = Array.from(el.options).map(o => o.value);
    const incoming = (window.availableSubagentes || []).filter(x => !!x && x.trim() !== '');
    incoming.forEach(val => {
      if (!base.includes(val)) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = val;
        el.appendChild(opt);
      }
    });
  }
  populateSubAgenteOptions();

  // Preseleccionar si viene del servidor
  if (subAgenteEl && window.selectedCliente) {
    const nombreSubagente = (window.selectedCliente.subagente || '').trim();
    const normalize = (s) => (s || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().trim();
    if (nombreSubagente) {
      const opts = Array.from(subAgenteEl.options || []);
      let opt = opts.find(o => {
        const txt = (o.textContent || '').trim();
        const val = (o.value || '').trim();
        return txt === nombreSubagente || val === nombreSubagente ||
               normalize(txt) === normalize(nombreSubagente) ||
               normalize(val) === normalize(nombreSubagente);
      });
      if (!opt) {
        opt = document.createElement('option');
        opt.value = nombreSubagente;
        opt.textContent = nombreSubagente;
        subAgenteEl.appendChild(opt);
      }
      subAgenteEl.value = opt.value;
    }
  }

  // Fallback: establecer Sub Agente por defecto
  (function () {
    const el = subAgenteTopEl || document.getElementById('subAgente');
    if (!el) return;
    if (el.value && el.selectedIndex > 0) return;
    const def = 'ARIAS Y ARIAS';
    const normalize = (s) => (s || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().trim();
    const opts = Array.from(el.options || []);
    let opt = opts.find(o => {
      const txt = (o.textContent || '').trim();
      const val = (o.value || '').trim();
      return normalize(txt) === normalize(def) || normalize(val) === normalize(def);
    });
    if (!opt) {
      opt = document.createElement('option');
      opt.value = def;
      opt.textContent = def;
      el.appendChild(opt);
    }
    el.value = opt.value;
  })();

  // Preseleccionar Ejecutivo si viene del servidor
  if (ejecutivoTopEl && window.selectedCliente) {
    const nombreEjecutivo = (window.selectedCliente.ejecutivo || '').trim();
    const normalize = (s) => (s || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().trim();
    if (nombreEjecutivo) {
      const opts = Array.from(ejecutivoTopEl.options || []);
      let opt = opts.find(o => {
        const txt = (o.textContent || '').trim();
        const val = (o.value || '').trim();
        return txt === nombreEjecutivo || val === nombreEjecutivo ||
               normalize(txt) === normalize(nombreEjecutivo) ||
               normalize(val) === normalize(nombreEjecutivo);
      });
      if (!opt) {
        opt = document.createElement('option');
        opt.value = nombreEjecutivo;
        opt.textContent = nombreEjecutivo;
        ejecutivoTopEl.appendChild(opt);
      }
      ejecutivoTopEl.value = opt.value;
    }
  }

  // Helper: construir opciones del select de Ramo
  function buildRamoOptions(selected) {
    const abbrs = (window.ramosAbbrs || []).filter(x => !!x && x.trim() !== '');
    const opts = [`<option value="">Selecciona...</option>`];
    abbrs.forEach(val => {
      const sel = (selected || '').trim() === val ? ' selected' : '';
      opts.push(`<option value="${val}"${sel}>${val}</option>`);
    });
    return opts.join('');
  }
  function buildRamoSelect(selected) {
    const t = (selected || '').toString();
    return `<select class="form-select ramo-select" title="${t.toUpperCase()}">${buildRamoOptions(selected)}</select>`;
  }
  function populateRamoProductoTopOptions() { /* Campo de texto: sin opciones */ }
  populateRamoProductoTopOptions();

  // Helpers de primas
  function parseNumber(val) {
    const raw = (val || '').toString().trim();
    if (!raw) return NaN;
    const cleaned = raw.replace(/[^\d.,-]/g, '');
    const lastDot = cleaned.lastIndexOf('.');
    const lastComma = cleaned.lastIndexOf(',');
    const sep = Math.max(lastDot, lastComma);
    let intPart;
    let decPart;
    if (sep === -1) {
      intPart = cleaned.replace(/[^\d-]/g, '');
      decPart = '';
    } else {
      intPart = cleaned.slice(0, sep).replace(/[^\d-]/g, '');
      decPart = cleaned.slice(sep + 1).replace(/[^\d]/g, '');
    }
    const combined = decPart ? `${intPart}.${decPart}` : intPart;
    const num = parseFloat(combined);
    return Number.isFinite(num) ? num : NaN;
  }
  function mapCurrencySymbol(val) {
    const raw = (val || '').toString().trim();
    if (!raw) return '';
    const up = raw.toUpperCase();
    if (up.includes('SOL') || up === 'PEN' || up.startsWith('S/')) return 'S/';
    if (up.includes('DOLAR') || up.includes('DÓLAR') || up.includes('DÓLARES') || up.includes('USD') || up.includes('US$') || up === '$') return 'US$';
    return raw;
  }
  function computePrimaNetaFromComercial(val) {
    const num = parseNumber(val);
    if (!Number.isFinite(num)) return '';
    return (num / 1.03).toFixed(2);
  }
  function computePrimaComercialFromNeta(val) {
    const num = parseNumber(val);
    if (!Number.isFinite(num)) return '';
    return (num * 1.03).toFixed(2);
  }
  function computePrimaIGVFromComercial(val) {
    const num = parseNumber(val);
    if (!Number.isFinite(num)) return '';
    return (num * 1.18).toFixed(2);
  }
  function computePrimaComercialFromTotal(val) {
    const num = parseNumber(val);
    if (!Number.isFinite(num)) return '';
    return (num / 1.18).toFixed(2);
  }

  // Números y comisiones
  function computeCommissionAmount(netaStr, pctStr) {
    const neta = parseNumber(netaStr);
    const pctVal = parseNumber(pctStr);
    if (!Number.isFinite(neta) || !Number.isFinite(pctVal)) return '';
    const ratio = pctVal <= 1 ? pctVal : (pctVal / 100);
    return (neta * ratio).toFixed(2);
  }
  // NUEVO: cálculo de Importe Comisión Sub Agente desde Importe Cía y % Sub Agente
  function computeSubAgentCommissionAmount(compImportStr, subPctStr) {
    const comp = parseNumber(compImportStr);
    const pctVal = parseNumber(subPctStr);
    if (!Number.isFinite(comp) || !Number.isFinite(pctVal)) return '';
    const ratio = pctVal <= 1 ? pctVal : (pctVal / 100);
    // Lógica solicitada: dividir entre * 1 antes de aplicar el porcentaje
    const base = comp * 1;
    return (base * ratio).toFixed(2);
  }
  function sumCommission(items) {
    let total = 0;
    (items || []).forEach(it => {
      const v = parseNumber(it.comision_compania_importe);
      if (Number.isFinite(v)) total += v;
    });
    return Number.isFinite(total) ? total.toFixed(2) : '';
  }

  function formatMoney(val) {
    const num = parseNumber(val);
    if (!Number.isFinite(num)) return (val || '');
    return num.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  // Normalización de ítems
  // Helper: sumar días a fecha dd/mm/yyyy
  function addDaysToDateStr(dateStr, days) {
    const raw = (dateStr || '').toString().trim();
    if (!raw) return '';
    const m = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (!m) return '';
    const d = parseInt(m[1], 10);
    const mo = parseInt(m[2], 10) - 1;
    const y = parseInt(m[3], 10);
    const dt = new Date(y, mo, d);
    if (isNaN(dt.getTime())) return '';
    dt.setDate(dt.getDate() + (Number.isFinite(days) ? days : Number(days) || 0));
    const dd = String(dt.getDate()).padStart(2, '0');
    const mm = String(dt.getMonth() + 1).padStart(2, '0');
    const yyyy = dt.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
  }

  function parseDMYDateStrict(value) {
    const raw = (value || '').toString().trim();
    const m = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (!m) return null;
    const day = Number(m[1]);
    const month = Number(m[2]);
    const year = Number(m[3]);
    const dt = new Date(year, month - 1, day);
    if (dt.getFullYear() !== year || (dt.getMonth() + 1) !== month || dt.getDate() !== day) return null;
    return dt;
  }

  function addMonthsClamped(baseDate, monthsToAdd) {
    if (!(baseDate instanceof Date) || Number.isNaN(baseDate.getTime())) return null;
    const y = baseDate.getFullYear();
    const m = baseDate.getMonth();
    const d = baseDate.getDate();
    const targetMonthIdx = m + monthsToAdd;
    const targetYear = y + Math.floor(targetMonthIdx / 12);
    const normMonth = ((targetMonthIdx % 12) + 12) % 12;
    const maxDay = new Date(targetYear, normMonth + 1, 0).getDate();
    const finalDay = Math.min(d, maxDay);
    return new Date(targetYear, normMonth, finalDay);
  }

  function isSameDate(a, b) {
    return !!a && !!b
      && a.getFullYear() === b.getFullYear()
      && a.getMonth() === b.getMonth()
      && a.getDate() === b.getDate();
  }

  function normalizeTipoVigenciaValue(value) {
    const raw = (value || '').toString().trim();
    if (!raw) return '';
    const upper = raw
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, ' ')
      .toUpperCase();
    if (upper === 'MENSUAL' || upper === 'DECLARACION MENSUAL') return 'DECLARACION MENSUAL';
    if (upper === 'TRIMESTRAL' || upper === 'PERIODICA') return 'PERIODICA';
    if (upper === 'ANUAL') return 'ANUAL';
    if (['NO RENOVABLE', 'EVENTUAL', 'FLOTANTE'].includes(upper)) return upper;
    return upper;
  }

  function detectTipoVigenciaByDates(inicioVigencia, finVigencia) {
    const start = parseDMYDateStrict(inicioVigencia);
    const end = parseDMYDateStrict(finVigencia);
    if (!start || !end) return '';
    const map = [
      { months: 1, tipo: 'DECLARACION MENSUAL' },
      { months: 3, tipo: 'PERIODICA' },
      { months: 12, tipo: 'ANUAL' }
    ];
    for (const candidate of map) {
      const until = addMonthsClamped(start, candidate.months);
      if (!until) continue;
      const untilMinusOne = new Date(until.getTime());
      untilMinusOne.setDate(untilMinusOne.getDate() - 1);
      if (isSameDate(end, until) || isSameDate(end, untilMinusOne)) {
        return candidate.tipo;
      }
    }
    return '';
  }

  function inferTipoVigenciaFromItems(items) {
    const tipos = new Set();
    (items || []).forEach((it) => {
      const tipo = detectTipoVigenciaByDates(it?.inicio_vigencia, it?.vencimiento);
      if (tipo) tipos.add(tipo);
    });
    if (!tipos.size) return '';
    if (tipos.size > 1) return '__MIXED__';
    return Array.from(tipos)[0] || '';
  }

  function syncTipoVigenciaTopFromDates(items) {
    if (!tipoVigenciaTopEl) return '';
    const current = normalizeTipoVigenciaValue(tipoVigenciaTopEl.value);
    if (tipoVigenciaManualOverride && current) {
      tipoVigenciaTopEl.value = current;
      return current;
    }
    const inferred = inferTipoVigenciaFromItems(items);
    if (!inferred || inferred === '__MIXED__') return inferred;
    tipoVigenciaTopEl.value = inferred;
    return inferred;
  }

  function resolveTipoVigenciaForSave(items) {
    if (tipoVigenciaManualOverride) {
      return normalizeTipoVigenciaValue(tipoVigenciaTopEl?.value || '');
    }
    const inferred = inferTipoVigenciaFromItems(items);
    if (inferred && inferred !== '__MIXED__' && tipoVigenciaTopEl) {
      tipoVigenciaTopEl.value = inferred;
    }
    return inferred;
  }

  if (tipoVigenciaTopEl) {
    tipoVigenciaTopEl.addEventListener('change', () => {
      const normalized = normalizeTipoVigenciaValue(tipoVigenciaTopEl.value);
      if (normalized) {
        tipoVigenciaManualOverride = true;
        tipoVigenciaTopEl.value = normalized;
      } else {
        tipoVigenciaManualOverride = false;
      }
    });
  }

  function normalizeItem(src) {
    const it = { ...src };
    const totalNum = parseNumber(it.prima_total);
    const comercialNum0 = parseNumber(it.prima_comercial);
    const netaNum0 = parseNumber(it.prima_neta);
    if (Number.isFinite(totalNum) && totalNum >= 100 && ((Number.isFinite(comercialNum0) && comercialNum0 < 10) || (Number.isFinite(netaNum0) && netaNum0 < 10))) {
      const comercialFromTotal = totalNum / 1.18;
      it.prima_comercial = comercialFromTotal.toFixed(2);
      it.prima_neta = computePrimaNetaFromComercial(it.prima_comercial);
      it.prima_comercial_igv = totalNum.toFixed(2);
      return it;
    }
    let comercial = (it.prima_comercial || '').toString().trim();
    let neta = (it.prima_neta || '').toString().trim();

    if (!comercial && neta) {
      comercial = computePrimaComercialFromNeta(neta);
      it.prima_comercial = comercial;
    }
    if (comercial) {
      it.prima_neta = computePrimaNetaFromComercial(comercial);
      if (!it.prima_comercial_igv) {
        it.prima_comercial_igv = computePrimaIGVFromComercial(comercial);
      }
    } else {
      if (!it.prima_comercial_igv) {
        it.prima_comercial_igv = '';
      }
    }

    // No rellenar factura ni fecha_pago automáticamente desde el PDF de póliza
    // Mantener ambos vacíos hasta que el usuario adjunte una cuota o los edite manualmente.

    // Regla de fechas (fallback):
    // - Si NO viene ultimo_dia_pago, usar Emisión + 15
    // - Si NO viene fecha_vencimiento, usar ultimo_dia_pago o Emisión + 15
    // if (it.fecha_emision) {
    //   const calcPago = addDaysToDateStr(it.fecha_emision, 15);
    //   if (!it.ultimo_dia_pago && calcPago) {
    //     it.ultimo_dia_pago = calcPago;
    //   }
    //   if (!it.fecha_vencimiento) {
    //     it.fecha_vencimiento = it.ultimo_dia_pago || calcPago || '';
    //   }
    // }

    // Mantener "Fin Vigencia" (vencimiento) tal cual PDF para la columna "Fin Vigencia"
    if (!it.cuotas) it.cuotas = [];
    return it;
  }

  // Encabezado de la tabla
  function ensureHeader() {
    const thead = document.querySelector('#extractTable thead');
    if (!thead) return;
    const headers = Array.from(thead.querySelectorAll('th')).map(th => th.textContent.trim().toLowerCase()); 
    const hasRamo = headers.includes('ramo');
    const hasProducto = headers.includes('producto');
    const hasCia = headers.includes('cía') || headers.includes('cia') || headers.includes('aseguradora');
    const hasPrimaNeta = headers.includes('prima neta');
    const hasAcciones = headers.includes('acciones');
    const expectedCount = 22; // + Factura y Fecha Pago
    if (!hasRamo || !hasProducto || !hasCia || !hasPrimaNeta || !hasAcciones || headers.length !== expectedCount) {
      thead.innerHTML = `
        <tr>
          <th>Póliza</th>
          <th>Proforma/Recibo</th>
          <th>Fecha Emisión</th>
          <th>Fecha Vencimiento</th>
          <th>Documento</th>
          <th>Colectivo Asegurado</th>
          <th>Cía</th>
          <th class="ramo-col">Ramo</th>
          <th>Producto</th>
          <th>Moneda</th>
          <th>Inicio Vigencia</th>
          <th>Fin Vigencia</th>
          <th>Prima Neta</th>
          <th>Prima Comercial</th>
          <th>Prima + IGV</th>
          <th>% Comisión Cía</th>
          <th>Imp. Comisión Cía</th>
          <th>% Comisión Sub Agente</th>
          <th>Imp. Comisión Sub Agente</th>
          <th>Factura</th>
          <th>Fecha Pago</th>
          <th class="actions-col">Acciones</th>
        </tr>
      `;
    }
  }
  ensureHeader();

  // Cachear aseguradoras cuando no exista el select global
  let issuerOptionsCache = null;
  async function ensureIssuerOptionsLoaded() {
    if (issuerOptionsCache && issuerOptionsCache.length) return issuerOptionsCache;
    if (issuerEl && issuerEl.options && issuerEl.options.length) {
      const opts = [];
      for (let i = 0; i < issuerEl.options.length; i++) {
        const o = issuerEl.options[i];
        const val = (o.value || '').trim();
        const txt = (o.text || '').trim();
        const isAutoDetect = (!val) && txt.toLowerCase().includes('auto') && txt.toLowerCase().includes('detectar');
        if (isAutoDetect || !txt) continue;
        const useVal = val || txt.toLowerCase();
        opts.push({ value: useVal, text: txt });
      }
      issuerOptionsCache = opts;
      return issuerOptionsCache;
    }
    try {
      const res = await fetch('/api/aseguradoras', { credentials: 'same-origin' });
      const body = await res.json();
      const rows = body?.rows || [];
      issuerOptionsCache = rows
        .map(a => {
          const text = (a.nombre_corto || a.nombre || '').trim();
          const val = (a.slug || '').trim() || text.toLowerCase();
          return { value: val, text };
        })
        .filter(x => !!x.text);
    } catch (err) {
      console.warn('Error cargando aseguradoras:', err);
      issuerOptionsCache = [];
    }
    return issuerOptionsCache;
  }

  // Opciones de aseguradora desde el select global
  function getIssuerOptions() {
    if (issuerOptionsCache && issuerOptionsCache.length) return issuerOptionsCache.slice();
    if (!issuerEl) return [];
    const opts = [];
    for (let i = 0; i < issuerEl.options.length; i++) {
      const o = issuerEl.options[i];
      const val = (o.value || '').trim();
      const txt = (o.text || '').trim();
      const isAutoDetect = (!val) && txt.toLowerCase().includes('auto') && txt.toLowerCase().includes('detectar');
      if (isAutoDetect) continue; // omitir "Auto (Detectar)"
      const useVal = val || txt.toLowerCase();
      if (!txt) continue;
      opts.push({ value: useVal, text: txt });
    }
    issuerOptionsCache = opts.slice();
    return issuerOptionsCache.slice();
  }

  function buildIssuerSelect(selectedVal) {
    const opts = getIssuerOptions();
    const optionsHtml = ['<option value="">Selecciona...</option>'].concat(
      opts.map(o => `<option value="${o.value}" ${o.value === (selectedVal || '').trim() ? 'selected' : ''}>${o.text}</option>`)
    ).join('');
    return `<select class="form-select form-select-sm issuer-row">${optionsHtml}</select>`;
  }

  function findIssuerValueByText(label) {
    const opts = getIssuerOptions();
    const t = (label || '').toString().trim().toLowerCase();
    if (!t) return '';
    const eq = opts.find(o => (o.text || '').toString().trim().toLowerCase() === t);
    if (eq) return eq.value;
    const inc = opts.find(o => {
      const tt = (o.text || '').toString().trim().toLowerCase();
      return tt.includes(t) || t.includes(tt);
    });
    if (inc) return inc.value;
    return t;
  }

  function __pickLPVVariant(txt) {
    const t = (txt || '').toString().toLowerCase();
    if (t.includes('eps') || t.includes('entidad prestadora') || t.includes('salud') || t.includes('lpeps')) return 'lpv-eps';
    if (t.includes('vida') && t.includes('ley')) return 'lpv-vida-ley';
    if (t.includes('vida')) return 'lpv-vida';
    if (t.includes('pension') || t.includes('pensión')) return 'lpv-pension';
    return 'positiva';
  }
  function __pickCrecerVariant(txt) {
    const t = (txt || '').toString().toLowerCase();
    return 'crecer';
  }
  function __preferIssuer(val, label) {
    const opts = getIssuerOptions();
    const v = (val || '').trim();
    if (v && opts.some(o => o.value === v)) return v;
    const l = (label || '').trim();
    if (l) {
      const byText = opts.find(o => (o.text || '').toLowerCase() === l.toLowerCase());
      if (byText) return byText.value;
      const inc = opts.find(o => (o.text || '').toLowerCase().includes(l.toLowerCase()));
      if (inc) return inc.value;
    }
    return v || '';
  }
  function __normIssuerText(text) {
    const s = (text || '').toString().toLowerCase();
    try {
      return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    } catch (e) {
      return s;
    }
  }
  function __hasToken(normText, token) {
    const t = __normIssuerText(normText);
    const re = new RegExp(`(^|[^a-z0-9])${token}([^a-z0-9]|$)`);
    return re.test(t);
  }
  function __detectIssuerSlug(text) {
    const t = (text || '').toString().toLowerCase();
    if (!t) return '';
    if (__hasToken(t, 'rimac')) return 'rimac';
    if (t.includes('hdi')) return 'hdi';
    if (t.includes('ohio')) return 'ohio';
    if (t.includes('qualitas') || t.includes('quálitas')) return 'qualitas';
    if (t.includes('avla')) return 'avla';
    if (t.includes('grandia') && t.includes('eps')) return 'grandia-eps';
    if (t.includes('crecer')) return __pickCrecerVariant(t);
    // Priorizar sanitas por encima del caso genérico "EPS"
    if (t.includes('sanitas')) return 'sanitas';
    // Positiva/LPV (incluye EPS genérico solo si no se detectó "sanitas")
    if (t.includes('positiva') || t.includes('lpv') || t.includes('vida ley') || t.includes('vida') || t.includes('pension') || t.includes('pensión') || t.includes('eps') || t.includes('entidad prestadora') || t.includes('salud') || t.includes('lpeps')) return __pickLPVVariant(t);
    if (t.includes('mapfre')) return 'mapfre';
    if (t.includes('pacifico') || t.includes('pacífico')) return 'pacifico';
    if (t.includes('protecta') || t.includes('proctecta')) return 'proctecta';
    return '';
  }
  function __inferIssuerForItem(item) {
    const hay = [
      item.cia, item.aseguradora, item.asegurado, item.asegurada, item.colectivo_asegurado,
      item.producto, item.ramos_producto, item.ramo
    ].filter(Boolean).join(' | ');
    const slug = __detectIssuerSlug(hay);
    if (slug) return __preferIssuer(slug, slug);
    const t = hay.toLowerCase();
    const opts = getIssuerOptions();
    const inc = opts.find(o => (o.text || '').toLowerCase() && t.includes((o.text || '').toLowerCase()));
    return inc ? inc.value : '';
  }

  // NUEVO: helper para generar botones de acción por fila
  function buildActions(index) {
    const item = extractedItems[index] || {};
    const cuotas = item.cuotas || [];
    const hasMultipleCuotas = cuotas.length > 1;
    
    let cuotasHtml = '';
    if (cuotas.length > 0) {
      cuotasHtml = cuotas.map((c, ci) => `
        <div class="cuota-row border rounded p-2 mb-2" data-cuota-index="${ci}">
          <div class="pane-fields mb-2">
            <div class="field">
              <label class="form-label small mb-1">CUPON</label>
              <input type="text" class="form-control form-control-sm cuota-cupon" data-index="${index}" data-cuota-index="${ci}" value="${c.cupon || ''}" placeholder="115441271">
            </div>
            <div class="field">
              <label class="form-label small mb-1">VENCIMIENTO</label>
              <input type="text" class="form-control form-control-sm cuota-vencimiento" data-index="${index}" data-cuota-index="${ci}" value="${c.fecha_vencimiento || ''}" placeholder="dd/mm/aaaa">
            </div>
            <div class="field">
              <label class="form-label small mb-1">IMPORTE</label>
              <input type="text" class="form-control form-control-sm cuota-importe" data-index="${index}" data-cuota-index="${ci}" value="${c.importe || ''}" placeholder="0.00">
            </div>
          </div>
          <div class="pane-fields mb-2">
            <div class="field">
              <label class="form-label small mb-1">FACTURA</label>
              <input type="text" class="form-control form-control-sm cuota-factura" data-index="${index}" data-cuota-index="${ci}" value="${c.factura || ''}" placeholder="F123-00000000">
            </div>
            <div class="field">
              <label class="form-label small mb-1">FECHA PAGO</label>
              <input type="text" class="form-control form-control-sm cuota-fecha" data-index="${index}" data-cuota-index="${ci}" value="${c.fecha_pago || ''}" placeholder="dd/mm/aaaa">
            </div>
            <div class="field">
              <label class="form-label small mb-1">ARCHIVO</label>
              ${(() => {
                const k = `${index}:${ci}`;
                const f = cuotaFacturaFileMap.get(k);
                const has = !!f;
                const nm = f ? (f.name || '') : '';
                return `
                  <div class="cuota-file-drop ${has ? 'has-file' : ''}" data-index="${index}" data-cuota-index="${ci}">
                    <div class="cuota-file-name text-truncate" title="${nm}">${nm || 'Adjuntar factura'}</div>
                    <div class="cuota-file-actions">
                      <button type="button" class="btn btn-sm btn-outline-secondary cuota-file-view" data-index="${index}" data-cuota-index="${ci}" ${has ? '' : 'disabled'}>
                        <i class="bi bi-eye"></i>
                      </button>
                      <button type="button" class="btn btn-sm btn-outline-danger cuota-file-remove" data-index="${index}" data-cuota-index="${ci}" ${has ? '' : 'disabled'}>
                        <i class="bi bi-x-lg"></i>
                      </button>
                    </div>
                  </div>
                  <input type="file" class="d-none cuota-file-input" data-index="${index}" data-cuota-index="${ci}" accept=".pdf,image/*">
                `;
              })()}
            </div>
          </div>
          <div class="d-flex justify-content-end">
            <button type="button" class="btn btn-sm btn-outline-danger action-remove-cuota" data-index="${index}" data-cuota-index="${ci}">Eliminar</button>
          </div>
        </div>
      `).join('');
    }

    return `
      <div class="actions-pane" data-index="${index}">
        <div class="drop-facturas mb-2" data-index="${index}">Haz clic para seleccionar o arrastra la factura aquí</div>
        <input type="file" class="d-none input-facturas" data-index="${index}" accept=".pdf,image/*" multiple>
        <div class="d-flex align-items-center justify-content-between mb-2">
          <div class="small text-muted">Archivos adjuntos</div>
          <span class="badge text-bg-secondary facturas-count">0</span>
        </div>
        <div class="list-facturas"></div>
        ${hasMultipleCuotas ? `
          <div class="pane-cuotas-hint mb-2">Cuotas múltiples: completa Factura y Fecha Pago en cada cuota.</div>
        ` : `
          <div class="pane-fields pane-fields-2 mb-2">
            <div class="field">
              <label class="form-label small mb-1">FACTURA</label>
              <input type="text" class="form-control form-control-sm pane-factura" data-index="${index}" value="${item.factura || ''}" placeholder="F003-00000000">
            </div>
            <div class="field">
              <label class="form-label small mb-1">FECHA PAGO</label>
              <input type="text" class="form-control form-control-sm pane-fecha" data-index="${index}" value="${item.fecha_pago || ''}" placeholder="dd/mm/aaaa">
            </div>
          </div>
        `}
        
        <div class="cuotas-list" data-index="${index}">
          ${cuotasHtml}
        </div>

        <div class="top-row mt-2 d-flex justify-content-between align-items-center">
          <button type="button" class="btn btn-sm btn-outline-primary action-add-cuota" data-index="${index}">+ Agregar Cuota</button>
          <button type="button" class="btn btn-sm btn-outline-danger action-remove" data-index="${index}">Eliminar Fila</button>
        </div>
      </div>
    `;
  }

  // Renderizado
  function render(items) {
    ensureHeader();
    console.log('[render] fechas', items.map(it => ({
      //ultimo_dia_pago: it.ultimo_dia_pago,
      fecha_vencimiento: it.fecha_vencimiento,
      vencimiento: it.vencimiento
    })));
    const formaPagoTop = (tipoPagoTopEl?.value || '').trim();
    const estadoTop = (estadoTopEl?.value || '').trim();
    // const ramoProductoTop = (ramoProductoTopEl?.value || '').trim(); // ELIMINADO
    const aseguradaTop = (aseguradaTopEl?.value || '').trim();
    const motivoTop = ''; // (motivoTopEl?.value || '').trim();
    const nroOpTop = (nroOperacionTopEl?.value || '').trim(); // NUEVO: Nro Operación
    const issuerText = issuerEl?.options?.[issuerEl.selectedIndex]?.text || (issuerEl?.value || '');

    // NUEVO: asegurar que 'ramo' sea vacío si no coincide con las abreviaciones disponibles
    const abbrs = (window.ramosAbbrs || []).map(s => (s || '').trim());
    items.forEach(it => {
      const r = (it.ramo || '').trim();
      if (r && !abbrs.includes(r)) {
        it.ramo = '';
      }
    });

    items.forEach(it => {
      if (formaPagoTop) it.forma_pago = formaPagoTop;
      if (estadoTop) it.estado = estadoTop;
      // if (ramoProductoTop && (!it.ramos_producto || it.ramos_producto.trim() === '')) {
      //   it.ramos_producto = ramoProductoTop;
      // }
      if (aseguradaTop && (!it.asegurada || it.asegurada.trim() === '')) {
        it.asegurada = aseguradaTop;
      }
      if (motivoTop && (!it.motivo || it.motivo.trim() === '')) {
        it.motivo = motivoTop;
      }
      if (nroOpTop && (!it.nro || it.nro.trim() === '')) {
        it.nro = nroOpTop;
      }
      // no forzamos cia desde un select global eliminado

      // NUEVO: asegurar 'asegurado' desde 'colectivo_asegurado'
      if (it.colectivo_asegurado && !it.asegurado) {
        it.asegurado = it.colectivo_asegurado;
      }

      // REMOVIDO: 'vencimiento' ↔ 'fecha_vencimiento'
      // (no se rellenan mutuamente)
    });

    syncTipoVigenciaTopFromDates(items);

    tbody.innerHTML = '';
    items.forEach((it, idx) => {
      const totalVal = it.prima_comercial_igv || it.prima_total || it.monto || '';
      if ((!it.prima_comercial || it.prima_comercial === '') && totalVal) {
        const comercial = computePrimaComercialFromTotal(totalVal);
        if (comercial) {
          it.prima_comercial = comercial;
          it.prima_neta = computePrimaNetaFromComercial(comercial);
        }
      }
      if (it.moneda) {
        it.moneda = mapCurrencySymbol(it.moneda);
      } else {
        it.moneda = 'S/';
      }

      // Sync factura/fecha_pago from first cuota if available
      if (it.cuotas && it.cuotas.length > 0) {
        it.factura = it.cuotas[0].factura || '';
        it.fecha_pago = it.cuotas[0].fecha_pago || '';
      }

      const tr = document.createElement('tr');
      let inferredVal = it.cia_value || findIssuerValueByText(it.cia || '');
      if (!inferredVal) {
        const guessed = __inferIssuerForItem(it);
        if (guessed) {
          it.cia_value = guessed;
          const optG = getIssuerOptions().find(o => o.value === guessed);
          it.cia = optG ? optG.text : (it.cia || '');
          inferredVal = guessed;
        }
      }
      const issuerDefaultVal = inferredVal || '';
      const issuerSelHtml = buildIssuerSelect(issuerDefaultVal);
      const monedaVal = (it.moneda || 'S/').trim();
      const monedaSelHtml = `
        <select class="form-select form-select-sm moneda-select" data-index="${idx}">
          <option value="S/" ${monedaVal === 'S/' ? 'selected' : ''}>S/</option>
          <option value="US$" ${monedaVal === 'US$' ? 'selected' : ''}>US$</option>
        </select>
      `;
      tr.innerHTML = `
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="numero_poliza">
          ${it.numero_poliza || ''}
        </td>
        <td contenteditable="true" class="editable d-flex align-items-center gap-2" data-index="${idx}" data-field="recibo">
          <span class="flex-grow-1">${it.recibo || ''}</span>
          <button type="button" class="btn btn-sm btn-outline-secondary act-find-pdf" data-index="${idx}" title="Buscar en PDF"><i class="bi bi-search"></i></button>
        </td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="fecha_emision">${it.fecha_emision || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="fecha_vencimiento">${it.fecha_vencimiento || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="numero_documento_extracted">${it.numero_documento_extracted || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="colectivo_asegurado">${it.colectivo_asegurado || ''}</td>
        <td data-index="${idx}" data-field="cia">${issuerSelHtml}</td>
        <td class="ramo-col" data-index="${idx}" data-field="ramo">${buildRamoSelect(it.ramo || '')}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="ramos_producto">${it.ramos_producto || ''}</td>
        <td data-index="${idx}" data-field="moneda">${monedaSelHtml}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="inicio_vigencia">${it.inicio_vigencia || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="vencimiento">${it.vencimiento || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_neta">${formatMoney(it.prima_neta || '')}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_comercial">${formatMoney(it.prima_comercial || '')}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="prima_comercial_igv">${formatMoney(it.prima_comercial_igv || it.prima_total || it.monto || '')}</td>
        <td data-index="${idx}" data-field="comision_compania_pct">
          <input type="number" step="0.01" class="form-control form-control-sm pct-comp" value="${it.comision_compania_pct || ''}">
        </td>
        <td data-index="${idx}" data-field="comision_compania_importe">
          <input type="number" step="0.01" class="form-control form-control-sm imp-comp" value="${it.comision_compania_importe || ''}" readonly>
        </td>
        <td data-index="${idx}" data-field="comision_subagente_pct">
          <input type="number" step="0.01" min="0" max="100" class="form-control form-control-sm pct-sub" value="${it.comision_subagente_pct || ''}">
        </td>
        <td data-index="${idx}" data-field="comision_subagente_importe">
          <input type="number" step="0.01" class="form-control form-control-sm imp-sub" value="${it.comision_subagente_importe || ''}" readonly>
        </td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="factura">${it.factura || ''}</td>
        <td contenteditable="true" class="editable" data-index="${idx}" data-field="fecha_pago">${it.fecha_pago || ''}</td>
        <td class="actions-col">
          ${buildActions(idx)}
        </td>
      `;
      // Persist default Cía en el modelo si no está
      if (!it.cia_value && issuerDefaultVal) {
        it.cia_value = issuerDefaultVal;
        const opt = getIssuerOptions().find(o => o.value === issuerDefaultVal);
        it.cia = opt ? opt.text : (it.cia || '');
      }
      tbody.appendChild(tr);
      const badge = tr.querySelector('.facturas-count');
      if (badge) {
        const cnt = (rowFacturasMap.get(idx) || []).length;
        badge.textContent = String(cnt);
      }
      const listEl = tr.querySelector('.list-facturas');
      if (listEl) {
        const arr = rowFacturasMap.get(idx) || [];
        listEl.innerHTML = arr.length ? ('<ul class="list-unstyled mb-0">' + arr.map((f, i) => {
          const name = f.name || 'archivo.pdf';
          return `<li class="d-flex align-items-center justify-content-between mb-1">
            <span class="text-truncate" style="max-width:220px;" title="${name}">${name}</span>
            <span class="d-flex gap-2">
              <button type="button" class="btn btn-sm btn-outline-secondary p-0 px-2 act-view-file" data-index="${idx}" data-file="${i}"><i class="bi bi-eye"></i></button>
              <button type="button" class="btn btn-sm btn-link text-danger p-0 border-0 act-remove-file" data-index="${idx}" data-file="${i}"><i class="bi bi-x-circle"></i></button>
            </span>
          </li>`;
        }).join('') + '</ul>') : '<span class="text-muted small">Sin archivos de cuota.</span>';
      }
      const pf = tr.querySelector('.pane-factura');
      if (pf) pf.value = it.factura || '';
      const pfp = tr.querySelector('.pane-fecha');
      if (pfp) pfp.value = it.fecha_pago || '';
      // Campo de fecha vencimiento se gestiona desde la tabla (no en el panel de cuota)
    });

    // Vincular cambio de Cía por fila
    Array.from(tbody.querySelectorAll('tr')).forEach((tr, idx) => {
      const sel = tr.querySelector('.issuer-row');
      if (!sel) return;
      sel.addEventListener('change', async (e) => {
        const val = (e.target.value || '').trim();
        const opts = getIssuerOptions();
        const found = opts.find(o => o.value === val);
        const label = found ? found.text : '';
        if (extractedItems[idx]) {
          extractedItems[idx].cia_value = val;
          extractedItems[idx].cia = label || val;
          try { await fetchCommissionPct(idx); } catch (e) {}
        }
      });
    });
    // Vincular cambio de Moneda por fila
    Array.from(tbody.querySelectorAll('tr')).forEach((tr, idx) => {
      const selMon = tr.querySelector('.moneda-select');
      if (!selMon) return;
      selMon.addEventListener('change', (e) => {
        const val = (e.target.value || '').trim();
        if (extractedItems[idx]) {
          extractedItems[idx].moneda = val;
        }
        scheduleAutoSave();
      });
    });

    if (btnSave) {
      const hasTipoDoc = ((tipoDocTopEl?.value || '').toString().trim() !== '');
      const hasTipoPago = ((tipoPagoTopEl?.value || '').toString().trim() !== '');
      btnSave.disabled = items.length === 0 || !hasTipoDoc || !hasTipoPago;
    }
    if (hint) hint.textContent = items.length ? `Se extrajeron ${items.length} ítem(s). Revisa y guarda.` : 'Sube un PDF para ver información.';
    const total = sumCommission(items);
    if (impComCompaniaEl) impComCompaniaEl.value = items.length ? total : '';
  }

  // NUEVO: Función para buscar % comisión en BD
  async function fetchCommissionPct(index) {
    const item = extractedItems[index];
    if (!item) return;

    // Determinar Cía por fila (ya no dependemos de un select global)
    const cia = (item.cia_value || '').trim() || findIssuerValueByText(item.cia || '');
    const ramo = item.ramo || '';
    const producto = item.ramos_producto || '';

    // Si no hay cia o no hay ni ramo ni producto, no podemos buscar
    if (!cia || (!ramo && !producto)) return;

    try {
      // Construir query params
      const qs = new URLSearchParams({ cia, ramo, producto }).toString();
      const res = await fetch(`/api/comisiones/lookup?${qs}`);
      const data = await res.json();

      if (data.ok && data.pct !== null) {
        const pctVal = parseFloat(data.pct);
        if (!Number.isFinite(pctVal)) return;

        // Actualizar modelo
        item.comision_compania_pct = pctVal;
        
        // Recalcular importe cía
        const neta = item.prima_neta || '';
        item.comision_compania_importe = computeCommissionAmount(neta, pctVal);

        // Recalcular importe subagente (si hay %)
        const subPct = item.comision_subagente_pct || '';
        if (subPct) {
          item.comision_subagente_importe = computeSubAgentCommissionAmount(item.comision_compania_importe, subPct);
        }

        // Actualizar DOM
        const tr = tbody.children[index];
        if (tr) {
          const pctInput = tr.querySelector('.pct-comp');
          if (pctInput) pctInput.value = pctVal;

          const impInput = tr.querySelector('.imp-comp');
          if (impInput) impInput.value = item.comision_compania_importe || '';

          const impSubInput = tr.querySelector('.imp-sub');
          if (impSubInput) impSubInput.value = item.comision_subagente_importe || '';
        }

        // Actualizar total global
        if (impComCompaniaEl) impComCompaniaEl.value = sumCommission(extractedItems);
      }
    } catch (err) {
      console.error('Error fetching commission pct:', err);
    }
  }

  // Cambios en select de Ramo por fila
  tbody.addEventListener('change', (e) => {
    const sel = e.target.closest('.ramo-select');
    if (!sel) return;
    const td = sel.closest('td');
    const idx = Number(td?.dataset?.index);
    if (!Number.isFinite(idx)) return;
    extractedItems[idx].ramo = sel.value || '';
    // Al cambiar ramo, poblar select de productos relacionados (si los hay)
    populateProductsForRamo(idx, sel.value || '').then(()=>{}).catch(()=>{});
    // NUEVO: buscar comisión
    fetchCommissionPct(idx);
    scheduleAutoSave();
  });

  // Delegación: cambio de producto seleccionado
  tbody.addEventListener('change', (e) => {
    const prodSel = e.target.closest('.producto-select');
    if (!prodSel) return;
    const idx = Number(prodSel.dataset.index);
    if (!Number.isFinite(idx)) return;
    const val = prodSel.value || '';
    // Si el option value es un id numeric y se quiere mostrar nombre, preferimos mostrar texto
    const text = prodSel.options[prodSel.selectedIndex]?.text || val;
    extractedItems[idx].ramos_producto = text;
    if (!extractedItems[idx].cia_value) {
      const g = __inferIssuerForItem(extractedItems[idx]);
      if (g) {
        extractedItems[idx].cia_value = g;
        const optG = getIssuerOptions().find(o => o.value === g);
        extractedItems[idx].cia = optG ? optG.text : (extractedItems[idx].cia || '');
        const tr = tbody.children[idx];
        if (tr) {
          const ciaSel = tr.querySelector('.issuer-row');
          if (ciaSel) ciaSel.value = g;
        }
      }
    }
    scheduleAutoSave();
  });

  // Helper para celdas
  function getTd(index, field) {
    return tbody.querySelector(`td[data-index="${index}"][data-field="${field}"]`);
  }

  // Actualiza dependientes sin modificar la celda activa
  function updateDependents(index, sourceField, activeTd) {
    const item = extractedItems[index] || {};
    const comercial = (item.prima_comercial || '').toString().trim();
    const neta = (item.prima_neta || '').toString().trim();

    if (sourceField === 'prima_comercial') {
      if (comercial) {
        const netaCalc = computePrimaNetaFromComercial(comercial);
        const igvCalc = computePrimaIGVFromComercial(comercial);
        item.prima_neta = netaCalc;
        item.prima_comercial_igv = igvCalc;
        const netaTd = getTd(index, 'prima_neta');
        const igvTd = getTd(index, 'prima_comercial_igv');
        if (netaTd && netaTd !== activeTd) netaTd.textContent = netaCalc;
        if (igvTd && igvTd !== activeTd) igvTd.textContent = igvCalc;
      } else {
        item.prima_neta = '';
        item.prima_comercial_igv = '';
        const netaTd = getTd(index, 'prima_neta');
        const igvTd = getTd(index, 'prima_comercial_igv');
        if (netaTd && netaTd !== activeTd) netaTd.textContent = '';
        if (igvTd && igvTd !== activeTd) igvTd.textContent = '';
      }
    } else if (sourceField === 'prima_neta') {
      if (neta) {
        const comercialCalc = computePrimaComercialFromNeta(neta);
        const igvCalc = computePrimaIGVFromComercial(comercialCalc);
        item.prima_comercial = comercialCalc;
        item.prima_comercial_igv = igvCalc;
        const comercialTd = getTd(index, 'prima_comercial');
        const igvTd = getTd(index, 'prima_comercial_igv');
        if (comercialTd && comercialTd !== activeTd) comercialTd.textContent = comercialCalc;
        if (igvTd && igvTd !== activeTd) igvTd.textContent = igvCalc;
      } else {
        item.prima_comercial = '';
        item.prima_comercial_igv = '';
        const comercialTd = getTd(index, 'prima_comercial');
        const igvTd = getTd(index, 'prima_comercial_igv');
        if (comercialTd && comercialTd !== activeTd) comercialTd.textContent = '';
        if (igvTd && igvTd !== activeTd) igvTd.textContent = '';
      }
    }

    // Recalcular comisión de compañía y subagente
    const pct = item.comision_compania_pct || (pctComCompaniaEl?.value || '');
    item.comision_compania_importe = pct ? computeCommissionAmount(item.prima_neta || '', pct) : '';
    const impTdInput = tbody.querySelector(`td[data-index="${index}"][data-field="comision_compania_importe"] .imp-comp`);
    if (impTdInput) impTdInput.value = item.comision_compania_importe || '';

    const subPct = item.comision_subagente_pct || (pctComSubAgenteEl?.value || '');
    item.comision_subagente_importe = subPct ? computeSubAgentCommissionAmount(item.comision_compania_importe || '', subPct) : '';
    const impSubTdInput = tbody.querySelector(`td[data-index="${index}"][data-field="comision_subagente_importe"] .imp-sub`);
    if (impSubTdInput) impSubTdInput.value = item.comision_subagente_importe || '';

    // Actualiza total superior
    if (impComCompaniaEl) impComCompaniaEl.value = sumCommission(extractedItems);
  }

  // Edición de celdas contenteditable
  function isDateField(field) {
    return field === 'inicio_vigencia' ||
           field === 'vencimiento' ||
           field === 'fecha_emision' ||
           field === 'fecha_vencimiento' ||
           field === 'fecha_pago';
  }
  function isRimacSelected() {
    const val = (issuerEl?.value || '').toLowerCase();
    const txt = issuerEl?.options?.[issuerEl.selectedIndex]?.text?.toLowerCase?.() || '';
    return val.includes('rimac') || txt.includes('rimac');
  }
  function maskDate(value) {
    const digits = (value || '').toString().replace(/[^\d]/g, '').slice(0, 8);
    const a = digits.slice(0, 2);
    const b = digits.slice(2, 4);
    const c = digits.slice(4, 8);
    if (digits.length <= 2) return a;
    if (digits.length <= 4) return `${a}/${b}`;
    return `${a}/${b}/${c}`;
  }
  function isPositivaSelected() {
    const val = (issuerEl?.value || '').toLowerCase();
    const txt = issuerEl?.options?.[issuerEl.selectedIndex]?.text?.toLowerCase?.() || '';
    return val.includes('positiva') || txt.includes('positiva') || val.includes('lpv');
  }
  function sanitizeDateInCell(td) {
    const masked = maskDate(td.textContent || '');
    if (td.textContent !== masked) td.textContent = masked;
    return masked;
  }
  function getDigitsFromCell(td) {
    return (td.textContent || '').replace(/[^\d]/g, '');
  }
  function setCaretToEnd(el) {
    try {
      const sel = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(el);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
    } catch (e) {}
  }
  function setDateByDigits(td, digits) {
    const limited = digits.slice(0, 8);
    const a = limited.slice(0, 2);
    const b = limited.slice(2, 4);
    const c = limited.slice(4, 8);
    const masked = limited.length <= 2 ? a : (limited.length <= 4 ? `${a}/${b}` : `${a}/${b}/${c}`);
    td.textContent = masked;
    setCaretToEnd(td);
    return masked;
  }

  // Campos numéricos contenteditable
  function isNumericField(field) {
    return field === 'prima_neta' ||
           field === 'prima_comercial' ||
           field === 'prima_comercial_igv';
  }
  function sanitizeNumericText(text) {
    const s = (text || '').toString();
    let out = '';
    let hasSep = false;
    let hasSign = false;
    for (let i = 0; i < s.length; i++) {
      const ch = s[i];
      if (ch >= '0' && ch <= '9') { out += ch; continue; }
      if ((ch === '.' || ch === ',') && !hasSep) { out += ch; hasSep = true; continue; }
      if (ch === '-' && !hasSign && out.length === 0) { out += ch; hasSign = true; continue; }
      // ignorar todo lo demás
    }
    return out;
  }
  function insertTextAtCursor(text) {
    try {
      document.execCommand('insertText', false, text);
    } catch (e) {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);
      range.deleteContents();
      range.insertNode(document.createTextNode(text));
    }
  }

  // Filtro de teclado: fechas solo números y '/'
  tbody.addEventListener('keydown', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const field = td.dataset.field;
    if (!isDateField(field)) return;

    // Control fino: escribir dígitos paso a paso DD/MM/AAAA, sin correr
    const nav = ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Tab','Home','End'];
    if (nav.includes(e.key) || e.ctrlKey || e.metaKey) return;

    if (e.key === 'Backspace' || e.key === 'Delete') {
      e.preventDefault();
      const idx = Number(td.dataset.index);
      const digits = getDigitsFromCell(td);
      const newDigits = digits.slice(0, Math.max(0, digits.length - 1));
      const masked = setDateByDigits(td, newDigits);
      if (Number.isFinite(idx)) extractedItems[idx][field] = masked;
      return;
    }

    if (/\d/.test(e.key)) {
      e.preventDefault();
      const idx = Number(td.dataset.index);
      const digits = getDigitsFromCell(td);
      if (digits.length >= 8) return; // máx 8 dígitos
      const newDigits = digits + e.key;
      const masked = setDateByDigits(td, newDigits);
      if (Number.isFinite(idx)) extractedItems[idx][field] = masked;
      return;
    }

    // Bloquear cualquier otra tecla, incluso '/'
    e.preventDefault();
  });

  // Filtro de pegado: fechas al patrón DD/MM/AAAA
  tbody.addEventListener('paste', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const field = td.dataset.field;
    if (!isDateField(field)) return;
    const text = (e.clipboardData || window.clipboardData)?.getData('text') || '';
    e.preventDefault();
    const masked = maskDate(text);
    document.execCommand('insertText', false, masked);
  });

  // Filtro de teclado: numéricos solo dígitos, separador decimal y signo inicial
  tbody.addEventListener('keydown', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const field = td.dataset.field;
    if (!isNumericField(field)) return;
    const nav = ['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Tab','Home','End'];
    if (nav.includes(e.key) || e.ctrlKey || e.metaKey) return;
    if (e.key === 'Enter') { e.preventDefault(); td.blur(); return; }
    if (e.key === 'Backspace' || e.key === 'Delete') return;
    if (/\d/.test(e.key)) return;
    if (e.key === '.' || e.key === ',') {
      const cur = td.textContent || '';
      if (cur.includes('.') || cur.includes(',')) { e.preventDefault(); return; }
      return;
    }
    if (e.key === '-') {
      const cur = td.textContent || '';
      if (cur.length === 0 && !cur.startsWith('-')) return;
    }
    e.preventDefault();
  });

  // Filtro de pegado: numéricos
  tbody.addEventListener('paste', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const field = td.dataset.field;
    if (!isNumericField(field)) return;
    const text = (e.clipboardData || window.clipboardData)?.getData('text') || '';
    e.preventDefault();
    const cleaned = sanitizeNumericText(text);
    insertTextAtCursor(cleaned);
  });

  // Filtro de pegado: texto plano para el resto de campos (evita estilos blancos pegados desde el header)
  tbody.addEventListener('paste', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const field = td.dataset.field;
    if (isDateField(field) || isNumericField(field)) return;
    const text = (e.clipboardData || window.clipboardData)?.getData('text/plain') || '';
    e.preventDefault();
    insertTextAtCursor(text);
    // Asegurar que no queden spans/formatos
    setTimeout(() => { td.textContent = (td.textContent || '').trim(); }, 0);
  });

  tbody.addEventListener('input', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const idx = Number(td.dataset.index);
    const field = td.dataset.field;
    if (!Number.isFinite(idx) || !field) return;

    if (isDateField(field)) {
      const masked = sanitizeDateInCell(td);
      extractedItems[idx][field] = masked;
    } else if (isNumericField(field)) {
      const cur = td.textContent || '';
      const cleaned = sanitizeNumericText(cur);
      if (cur !== cleaned) td.textContent = cleaned;
      extractedItems[idx][field] = cleaned;
    } else {
      extractedItems[idx][field] = (td.textContent || '').trim();
    }
    if (field === 'prima_comercial' || field === 'prima_neta') {
      updateDependents(idx, field, td);
    }
    if (field === 'inicio_vigencia' || field === 'vencimiento') {
      syncTipoVigenciaTopFromDates(extractedItems);
    }
  });

  // Formateo en blur y guardado
  tbody.addEventListener('focusout', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    const idx = Number(td.dataset.index);
    const field = td.dataset.field;
    if (!Number.isFinite(idx) || !field) return;

    if (field === 'prima_comercial' || field === 'prima_neta' || field === 'prima_comercial_igv') {
      const num = parseNumber(td.textContent);
      const formatted = Number.isFinite(num) ? num.toFixed(2) : '';
      td.textContent = formatted;
      extractedItems[idx][field] = formatted;
    } else {
      extractedItems[idx][field] = td.textContent.trim();
    }

    // NUEVO: Auto-relleno de 'ramos_producto'
    // Si se edita Producto en una fila, y las demás filas tienen ese campo vacío, replicarlo.
    if (field === 'ramos_producto') {
      const val = extractedItems[idx][field];
      // Buscar comisión para la fila actual
      fetchCommissionPct(idx);

      if (val) {
        let changed = false;
        extractedItems.forEach((it, i) => {
          if (i !== idx && (!it.ramos_producto || it.ramos_producto.trim() === '')) {
            it.ramos_producto = val;
            // Actualizar celda visualmente
            const cell = getTd(i, 'ramos_producto');
            if (cell) cell.textContent = val;
            changed = true;
            // Buscar comisión para las filas autocompletadas
            fetchCommissionPct(i);
          }
        });
        if (changed) scheduleAutoSave();
      }
    }

    if (field === 'prima_comercial' || field === 'prima_neta') {
      updateDependents(idx, field, td);
    }
    if (field === 'inicio_vigencia' || field === 'vencimiento') {
      syncTipoVigenciaTopFromDates(extractedItems);
    }
    scheduleAutoSave();
  });

  // Evitar salto de línea en Enter
  tbody.addEventListener('keydown', (e) => {
    const td = e.target.closest('td.editable');
    if (!td) return;
    if (e.key === 'Enter') {
      e.preventDefault();
      td.blur();
    }
  });

  // Cambio en % Comisión Cía por fila
  tbody.addEventListener('input', (e) => {
    const input = e.target.closest('input.pct-comp');
    if (!input) return;
    const td = input.closest('td');
    const idx = Number(td?.dataset?.index);
    if (!Number.isFinite(idx)) return;

    const pct = input.value || '';
    extractedItems[idx].comision_compania_pct = pct;
    const neta = extractedItems[idx].prima_neta || '';
    extractedItems[idx].comision_compania_importe = pct ? computeCommissionAmount(neta, pct) : '';
    const impEl = input.closest('tr')?.querySelector('.imp-comp');
    if (impEl) impEl.value = extractedItems[idx].comision_compania_importe || '';

    const subPct = extractedItems[idx].comision_subagente_pct || '';
    const impSubEl = input.closest('tr')?.querySelector('.imp-sub');
    extractedItems[idx].comision_subagente_importe = subPct ? computeSubAgentCommissionAmount(extractedItems[idx].comision_compania_importe || '', subPct) : '';
    if (impSubEl) impSubEl.value = extractedItems[idx].comision_subagente_importe || '';

    if (impComCompaniaEl) impComCompaniaEl.value = sumCommission(extractedItems);
    scheduleAutoSave();
  });

  // Cambio en % Comisión Sub Agente por fila
  tbody.addEventListener('input', (e) => {
    const input = e.target.closest('input.pct-sub');
    if (!input) return;
    const td = input.closest('td');
    const idx = Number(td?.dataset?.index);
    if (!Number.isFinite(idx)) return;

    const subPct = input.value || '';
    extractedItems[idx].comision_subagente_pct = subPct;
    const compImport = extractedItems[idx].comision_compania_importe || '';
    extractedItems[idx].comision_subagente_importe = subPct ? computeSubAgentCommissionAmount(compImport, subPct) : '';
    const impSubEl = input.closest('tr')?.querySelector('.imp-sub');
    if (impSubEl) impSubEl.value = extractedItems[idx].comision_subagente_importe || '';

    scheduleAutoSave();
  });

  // Acciones por fila (Eliminar/Duplicar/Cuotas)
  tbody.addEventListener('click', (e) => {
    const btnRemove = e.target.closest('.action-remove');
    const btnDup = e.target.closest('.action-duplicate');
    const btnAttach = e.target.closest('.action-attach-factura');
    const btnAddCuota = e.target.closest('.action-add-cuota');
    const btnRemoveCuota = e.target.closest('.action-remove-cuota');
    
    if (!btnRemove && !btnDup && !btnAttach && !btnAddCuota && !btnRemoveCuota) return;

    const btn = (btnRemove || btnDup || btnAttach || btnAddCuota || btnRemoveCuota);
    const idx = Number(btn?.dataset?.index);
    if (!Number.isFinite(idx)) return;

    if (btnAddCuota) {
      if (!extractedItems[idx].cuotas) extractedItems[idx].cuotas = [];
       extractedItems[idx].cuotas.push({ cupon: '', factura: '', fecha_pago: '', importe: '', fecha_vencimiento: '', moneda: 'S/' });
      refreshCuotasUI(idx);
      scheduleAutoSave();
      return;
    }

    if (btnRemoveCuota) {
      const cuotaIdx = Number(btn.dataset.cuotaIndex);
      if (Number.isFinite(cuotaIdx) && extractedItems[idx].cuotas) {
        extractedItems[idx].cuotas.splice(cuotaIdx, 1);
        const rebuilt = new Map();
        Array.from(cuotaFacturaFileMap.entries()).forEach(([k, f]) => {
          const [riRaw, ciRaw] = String(k).split(':');
          const ri = Number(riRaw);
          const ci = Number(ciRaw);
          if (!Number.isFinite(ri) || !Number.isFinite(ci)) return;
          if (ri !== idx) {
            rebuilt.set(k, f);
            return;
          }
          if (ci < cuotaIdx) {
            rebuilt.set(k, f);
            return;
          }
          if (ci === cuotaIdx) {
            try {
              const arr = rowFacturasMap.get(idx) || [];
              const newArr = arr.filter(x => keyForFile(x) !== keyForFile(f));
              rowFacturasMap.set(idx, newArr);
            } catch (_) {}
            return;
          }
          rebuilt.set(`${idx}:${ci - 1}`, f);
        });
        cuotaFacturaFileMap = rebuilt;
        refreshCuotasUI(idx);
        updateRowFilesUI(idx);
        scheduleAutoSave();
      }
      return;
    }

    if (btnAttach) {
      const tr = tbody.querySelectorAll('tr')[idx];
      const input = tr?.querySelector('.input-facturas');
      input?.click();
      return;
    }

    if (btnRemove) {
      extractedItems.splice(idx, 1);
      const newMap = new Map();
      Array.from(rowFacturasMap.entries()).forEach(([k, v]) => {
        if (k < idx) newMap.set(k, v);
        else if (k > idx) newMap.set(k - 1, v);
      });
      rowFacturasMap = newMap;
      const newCuotaMap = new Map();
      Array.from(cuotaFacturaFileMap.entries()).forEach(([k, f]) => {
        const [riRaw, ciRaw] = String(k).split(':');
        const ri = Number(riRaw);
        const ci = Number(ciRaw);
        if (!Number.isFinite(ri) || !Number.isFinite(ci)) return;
        if (ri < idx) newCuotaMap.set(k, f);
        else if (ri > idx) newCuotaMap.set(`${ri - 1}:${ci}`, f);
      });
      cuotaFacturaFileMap = newCuotaMap;
      render(extractedItems);
      if (impComCompaniaEl) impComCompaniaEl.value = sumCommission(extractedItems);
      const newIndex = Math.max(0, Math.min(idx, extractedItems.length - 1));
      setTimeout(() => {
        const firstCell = tbody.querySelector(`td[data-index="${newIndex}"][data-field="recibo"]`);
        firstCell?.focus();
      }, 0);
      scheduleAutoSave();
      return;
    }

    if (btnDup) {
      const copy = { ...(extractedItems[idx] || {}) };
      extractedItems.splice(idx + 1, 0, copy);
      const files = rowFacturasMap.get(idx);
      if (files && files.length) {
        const shifted = new Map();
        Array.from(rowFacturasMap.entries()).forEach(([k, v]) => {
          if (k <= idx) shifted.set(k, v);
          else shifted.set(k + 1, v);
        });
        rowFacturasMap = shifted;
        rowFacturasMap.set(idx + 1, files.slice());
      }
      const shiftedCuota = new Map();
      Array.from(cuotaFacturaFileMap.entries()).forEach(([k, f]) => {
        const [riRaw, ciRaw] = String(k).split(':');
        const ri = Number(riRaw);
        const ci = Number(ciRaw);
        if (!Number.isFinite(ri) || !Number.isFinite(ci)) return;
        if (ri <= idx) shiftedCuota.set(k, f);
        else shiftedCuota.set(`${ri + 1}:${ci}`, f);
      });
      Array.from(cuotaFacturaFileMap.entries()).forEach(([k, f]) => {
        const [riRaw, ciRaw] = String(k).split(':');
        const ri = Number(riRaw);
        const ci = Number(ciRaw);
        if (ri === idx && Number.isFinite(ci)) {
          shiftedCuota.set(`${idx + 1}:${ci}`, f);
        }
      });
      cuotaFacturaFileMap = shiftedCuota;
      render(extractedItems);
      if (impComCompaniaEl) impComCompaniaEl.value = sumCommission(extractedItems);
      setTimeout(() => {
        const firstCell = tbody.querySelector(`td[data-index="${idx + 1}"][data-field="recibo"]`);
        firstCell?.focus();
      }, 0);
      scheduleAutoSave();
      return;
    }
  });

  tbody.addEventListener('input', (e) => {
    const cc = e.target.closest('.cuota-cupon');
    const cv = e.target.closest('.cuota-vencimiento');
    const ci = e.target.closest('.cuota-importe');
    const cf = e.target.closest('.cuota-factura');
    const cp = e.target.closest('.cuota-fecha');
    
    if (!cc && !cv && !ci && !cf && !cp) return;
    
    const src = (cc || cv || ci || cf || cp);
    const idx = Number(src.dataset.index);
    const cuotaIdx = Number(src.dataset.cuotaIndex);
    if (!Number.isFinite(idx) || !Number.isFinite(cuotaIdx)) return;
    if (!extractedItems[idx] || !extractedItems[idx].cuotas[cuotaIdx]) return;
    
    if (cc) {
      extractedItems[idx].cuotas[cuotaIdx].cupon = cc.value;
    }
    if (cv) {
      extractedItems[idx].cuotas[cuotaIdx].fecha_vencimiento = cv.value;
    }
    if (ci) {
      extractedItems[idx].cuotas[cuotaIdx].importe = ci.value;
    }
    if (cf) {
      extractedItems[idx].cuotas[cuotaIdx].factura = cf.value;
    }
    if (cp) {
      extractedItems[idx].cuotas[cuotaIdx].fecha_pago = cp.value;
    }
    syncFirstCuotaToRow(idx);
    scheduleAutoSave();
  });

  function refreshCuotasUI(index) {
    const tr = tbody.querySelectorAll('tr')[index];
    if (!tr) return;
    const actionsCol = tr.querySelector('.actions-col');
    if (actionsCol) {
      actionsCol.innerHTML = buildActions(index);
    }
    updateRowFilesUI(index);
  }

  function updateRowFilesUI(index) {
    const tr = tbody.querySelectorAll('tr')[index];
    if (!tr) return;
    const badge = tr.querySelector('.facturas-count');
    const listEl = tr.querySelector('.list-facturas');
    const arr = rowFacturasMap.get(index) || [];
    if (badge) badge.textContent = String(arr.length);
    if (listEl) {
      listEl.innerHTML = arr.length ? ('<ul class="list-unstyled mb-0">' + arr.map((f, i) => {
        const name = f.name || 'archivo.pdf';
        return `<li class="d-flex align-items-center justify-content-between mb-1">
          <span class="text-truncate" style="max-width:220px;" title="${name}">${name}</span>
          <span class="d-flex gap-2">
            <button type="button" class="btn btn-sm btn-outline-secondary p-0 px-2 act-view-file" data-index="${index}" data-file="${i}"><i class="bi bi-eye"></i></button>
            <button type="button" class="btn btn-sm btn-link text-danger p-0 border-0 act-remove-file" data-index="${index}" data-file="${i}"><i class="bi bi-x-circle"></i></button>
          </span>
        </li>`;
      }).join('') + '</ul>') : '<span class="text-muted small">Sin archivos de cuota.</span>';
    }
    const item = extractedItems[index] || {};
    const pf = tr.querySelector('.pane-factura');
    if (pf) pf.value = item.factura || '';
    const pfp = tr.querySelector('.pane-fecha');
    if (pfp) pfp.value = item.fecha_pago || '';
    // Campo de fecha vencimiento se gestiona desde la tabla (no en el panel de cuota)
  }

  tbody.addEventListener('change', async (e) => {
    const input = e.target.closest('.input-facturas');
    if (!input) return;
    const idx = Number(input.dataset.index);
    if (!Number.isFinite(idx)) return;
    const files = Array.from(input.files || []);
    if (files.length) {
      const arr = rowFacturasMap.get(idx) || [];
      for (const f of files) {
        if (!arr.some(x => x.name === f.name && x.size === f.size)) {
          arr.push(f);
          if (/\.pdf$/i.test(f.name)) {
            const meta = await extractFacturaMetaFromFile(f);
            facturaMetaMap.set(keyForFile(f), meta);
            if (meta && Array.isArray(meta.cuotas) && meta.cuotas.length > 0) {
              mergeExtractedCuotas(idx, meta);
            } else if (meta && meta.factura) {
              if (extractedItems[idx]) {
                extractedItems[idx].factura = meta.factura || '';
                extractedItems[idx].fecha_pago = meta.fecha_pago || '';
                if (meta.fecha_vencimiento && !extractedItems[idx].fecha_vencimiento) {
                  extractedItems[idx].fecha_vencimiento = meta.fecha_vencimiento;
                }
                const tdFac = getTd(idx, 'factura');
                if (tdFac) tdFac.textContent = extractedItems[idx].factura || '';
                const tdFec = getTd(idx, 'fecha_pago');
                if (tdFec) tdFec.textContent = extractedItems[idx].fecha_pago || '';
                const tdV = getTd(idx, 'fecha_vencimiento');
                if (tdV && extractedItems[idx].fecha_vencimiento) tdV.textContent = extractedItems[idx].fecha_vencimiento;
                updateRowFilesUI(idx);
              }
            }
          }
        }
      }
      rowFacturasMap.set(idx, arr);
      updateRowFilesUI(idx);
      input.value = '';
    }
  });

  function syncFirstCuotaToRow(index) {
    if (!Number.isFinite(index) || !extractedItems[index]) return;
    const qs = extractedItems[index].cuotas || [];
    if (!qs.length) return;
    extractedItems[index].factura = qs[0]?.factura || '';
    extractedItems[index].fecha_pago = qs[0]?.fecha_pago || '';
    const tdFac = getTd(index, 'factura');
    if (tdFac) tdFac.textContent = extractedItems[index].factura || '';
    const tdFec = getTd(index, 'fecha_pago');
    if (tdFec) tdFec.textContent = extractedItems[index].fecha_pago || '';
  }

  async function attachCuotaFile(index, cuotaIdx, file) {
    if (!Number.isFinite(index) || !Number.isFinite(cuotaIdx) || !file) return;
    if (!extractedItems[index] || !extractedItems[index].cuotas || !extractedItems[index].cuotas[cuotaIdx]) return;

    const cuotaKey = `${index}:${cuotaIdx}`;
    const prev = cuotaFacturaFileMap.get(cuotaKey);
    if (prev) {
      try {
        const arrPrev = rowFacturasMap.get(index) || [];
        const cleaned = arrPrev.filter(x => keyForFile(x) !== keyForFile(prev));
        rowFacturasMap.set(index, cleaned);
      } catch (_) {}
    }

    cuotaFacturaFileMap.set(cuotaKey, file);

    const arr = rowFacturasMap.get(index) || [];
    if (!arr.some(x => keyForFile(x) === keyForFile(file))) {
      arr.push(file);
    }
    rowFacturasMap.set(index, arr);

    if (/\.pdf$/i.test(file.name)) {
      const meta = await extractFacturaMetaFromFile(file);
      facturaMetaMap.set(keyForFile(file), meta);
      const cuota = extractedItems[index].cuotas[cuotaIdx];
      if (cuota) {
        if (!cuota.factura && meta.factura) cuota.factura = meta.factura;
        if (!cuota.fecha_pago && meta.fecha_pago) cuota.fecha_pago = meta.fecha_pago;
        if (!cuota.fecha_vencimiento && meta.fecha_vencimiento) cuota.fecha_vencimiento = meta.fecha_vencimiento;
      }
      syncFirstCuotaToRow(index);
    }

    refreshCuotasUI(index);
    updateRowFilesUI(index);
    scheduleAutoSave();
  }

  tbody.addEventListener('change', async (e) => {
    const input = e.target.closest('.cuota-file-input');
    if (!input) return;
    const idx = Number(input.dataset.index);
    const cuotaIdx = Number(input.dataset.cuotaIndex);
    if (!Number.isFinite(idx) || !Number.isFinite(cuotaIdx)) return;
    const file = (input.files && input.files[0]) ? input.files[0] : null;
    input.value = '';
    if (!file) return;
    await attachCuotaFile(idx, cuotaIdx, file);
  });

  tbody.addEventListener('click', (e) => {
    const btnView = e.target.closest('.cuota-file-view');
    const btnRem = e.target.closest('.cuota-file-remove');
    if (btnView || btnRem) {
      const idx = Number((btnView || btnRem).dataset.index);
      const cuotaIdx = Number((btnView || btnRem).dataset.cuotaIndex);
      if (!Number.isFinite(idx) || !Number.isFinite(cuotaIdx)) return;
      const k = `${idx}:${cuotaIdx}`;
      const file = cuotaFacturaFileMap.get(k);
      if (!file) return;
      if (btnView) {
        try {
          const url = URL.createObjectURL(file);
          const titleEl = document.getElementById('pdfModalLabel');
          if (titleEl) titleEl.textContent = `Factura: ${file.name}`;
          if (typeof window.openPdfInModal === 'function') {
            window.openPdfInModal(url);
          } else {
            window.open(url, '_blank', 'noopener');
          }
          setTimeout(() => { try { URL.revokeObjectURL(url); } catch (_) {} }, 10000);
        } catch (_) {}
        return;
      }
      if (btnRem) {
        cuotaFacturaFileMap.delete(k);
        try {
          const arr = rowFacturasMap.get(idx) || [];
          const newArr = arr.filter(x => keyForFile(x) !== keyForFile(file));
          rowFacturasMap.set(idx, newArr);
        } catch (_) {}
        try {
          if (extractedItems[idx]?.cuotas?.[cuotaIdx]) {
            extractedItems[idx].cuotas[cuotaIdx].factura = '';
            extractedItems[idx].cuotas[cuotaIdx].fecha_pago = '';
          }
        } catch (_) {}
        syncFirstCuotaToRow(idx);
        refreshCuotasUI(idx);
        updateRowFilesUI(idx);
        scheduleAutoSave();
        return;
      }
    }

    const dz = e.target.closest('.cuota-file-drop');
    if (!dz) return;
    const idx = Number(dz.dataset.index);
    const cuotaIdx = Number(dz.dataset.cuotaIndex);
    if (!Number.isFinite(idx) || !Number.isFinite(cuotaIdx)) return;
    const tr = tbody.querySelectorAll('tr')[idx];
    const input = tr?.querySelector(`.cuota-file-input[data-index="${idx}"][data-cuota-index="${cuotaIdx}"]`);
    input?.click();
  });

  tbody.addEventListener('dragover', (e) => {
    const dz = e.target.closest('.cuota-file-drop');
    if (!dz) return;
    e.preventDefault();
    dz.classList.add('dragover');
  });
  tbody.addEventListener('dragleave', (e) => {
    const dz = e.target.closest('.cuota-file-drop');
    if (!dz) return;
    dz.classList.remove('dragover');
  });
  tbody.addEventListener('drop', async (e) => {
    const dz = e.target.closest('.cuota-file-drop');
    if (!dz) return;
    e.preventDefault();
    dz.classList.remove('dragover');
    const idx = Number(dz.dataset.index);
    const cuotaIdx = Number(dz.dataset.cuotaIndex);
    if (!Number.isFinite(idx) || !Number.isFinite(cuotaIdx)) return;
    const file = Array.from(e.dataTransfer?.files || []).find(f => /\.pdf$/i.test(f.name) || /^image\//i.test(f.type));
    if (!file) return;
    await attachCuotaFile(idx, cuotaIdx, file);
  });

  tbody.addEventListener('dragover', (e) => {
    const dz = e.target.closest('.drop-facturas');
    if (!dz) return;
    e.preventDefault();
    dz.classList.add('dragover');
  });
  tbody.addEventListener('dragleave', (e) => {
    const dz = e.target.closest('.drop-facturas');
    if (!dz) return;
    dz.classList.remove('dragover');
  });
  tbody.addEventListener('drop', async (e) => {
    const dz = e.target.closest('.drop-facturas');
    if (!dz) return;
    e.preventDefault();
    dz.classList.remove('dragover');
    const idx = Number(dz.dataset.index);
    if (!Number.isFinite(idx)) return;
    const files = Array.from(e.dataTransfer?.files || []).filter(f => /\.pdf$/i.test(f.name) || /^image\//i.test(f.type));
    if (!files.length) return;
    const arr = rowFacturasMap.get(idx) || [];
    for (const f of files) {
      if (!arr.some(x => x.name === f.name && x.size === f.size)) {
        arr.push(f);
        if (/\.pdf$/i.test(f.name)) {
          const meta = await extractFacturaMetaFromFile(f);
          facturaMetaMap.set(keyForFile(f), meta);
          if (meta && Array.isArray(meta.cuotas) && meta.cuotas.length > 0) {
            mergeExtractedCuotas(idx, meta);
          } else if (meta && meta.factura) {
            if (extractedItems[idx]) {
              extractedItems[idx].factura = meta.factura || '';
              extractedItems[idx].fecha_pago = meta.fecha_pago || '';
              if (meta.fecha_vencimiento && !extractedItems[idx].fecha_vencimiento) {
                extractedItems[idx].fecha_vencimiento = meta.fecha_vencimiento;
              }
              const tdFac = getTd(idx, 'factura');
              if (tdFac) tdFac.textContent = extractedItems[idx].factura || '';
              const tdFec = getTd(idx, 'fecha_pago');
              if (tdFec) tdFec.textContent = extractedItems[idx].fecha_pago || '';
              const tdV = getTd(idx, 'fecha_vencimiento');
              if (tdV && extractedItems[idx].fecha_vencimiento) tdV.textContent = extractedItems[idx].fecha_vencimiento;
              updateRowFilesUI(idx);
            }
          }
        }
      }
    }
    rowFacturasMap.set(idx, arr);
    updateRowFilesUI(idx);
  });

  // Click en la zona de drop abre el selector de archivos
  tbody.addEventListener('click', (e) => {
    const dz = e.target.closest('.drop-facturas');
    if (!dz) return;
    const idx = Number(dz.dataset.index);
    if (!Number.isFinite(idx)) return;
    const tr = tbody.querySelectorAll('tr')[idx];
    const input = tr?.querySelector('.input-facturas');
    input?.click();
  });

  tbody.addEventListener('click', (e) => {
    const btnView = e.target.closest('.act-view-file');
    const btnRem = e.target.closest('.act-remove-file');
    if (!btnView && !btnRem) return;
    const idx = Number((btnView || btnRem).dataset.index);
    const i = Number((btnView || btnRem).dataset.file);
    const arr = rowFacturasMap.get(idx) || [];
    const file = arr[i];
    if (!file) return;
    if (btnView) {
      try {
        const url = URL.createObjectURL(file);
        const titleEl = document.getElementById('pdfModalLabel');
        if (titleEl) titleEl.textContent = `Factura: ${file.name}`;
        if (typeof window.openPdfInModal === 'function') {
          window.openPdfInModal(url);
        } else {
          window.open(url, '_blank', 'noopener');
        }
        setTimeout(() => { try { URL.revokeObjectURL(url); } catch (_) {} }, 10000);
      } catch (_) {}
      return;
    }
    if (btnRem) {
      try {
        const kf = keyForFile(file);
        let hitKey = '';
        Array.from(cuotaFacturaFileMap.entries()).some(([k, f]) => {
          if (f && keyForFile(f) === kf) {
            hitKey = k;
            return true;
          }
          return false;
        });
        if (hitKey) {
          cuotaFacturaFileMap.delete(hitKey);
          const parts = String(hitKey).split(':');
          const cuotaIdx = Number(parts[1]);
          if (Number.isFinite(cuotaIdx) && extractedItems[idx]?.cuotas?.[cuotaIdx]) {
            extractedItems[idx].cuotas[cuotaIdx].factura = '';
            extractedItems[idx].cuotas[cuotaIdx].fecha_pago = '';
          }
        }
      } catch (_) {}
      arr.splice(i, 1);
      rowFacturasMap.set(idx, arr);
      syncFirstCuotaToRow(idx);
      // Si ya no quedan archivos de cuota, resetear Factura y Fecha de Pago
      if (arr.length === 0) {
        if (extractedItems[idx]) {
          extractedItems[idx].factura = '';
          extractedItems[idx].fecha_pago = '';
        }
        const tr = tbody.querySelectorAll('tr')[idx];
        if (tr) {
          const pf = tr.querySelector('.pane-factura');
          if (pf) pf.value = '';
          const pfp = tr.querySelector('.pane-fecha');
          if (pfp) pfp.value = '';
        }
        const tdFac = getTd(idx, 'factura');
        if (tdFac) tdFac.textContent = '';
        const tdFec = getTd(idx, 'fecha_pago');
        if (tdFec) tdFec.textContent = '';
      }
      updateRowFilesUI(idx);
      scheduleAutoSave();
      return;
    }
  });

  tbody.addEventListener('input', (e) => {
    const pf = e.target.closest('.pane-factura');
    const pfp = e.target.closest('.pane-fecha');
    const pfv = null;
    if (!pf && !pfp) return;
    const idx = Number((pf || pfp).dataset.index);
    if (!Number.isFinite(idx)) return;
    if (!extractedItems[idx]) return;
    if (pf) {
      extractedItems[idx].factura = pf.value;
      const td = getTd(idx, 'factura');
      if (td) td.textContent = pf.value || '';
    }
    if (pfp) {
      extractedItems[idx].fecha_pago = pfp.value;
      const td = getTd(idx, 'fecha_pago');
      if (td) td.textContent = pfp.value || '';
    }
    scheduleAutoSave();
  });

  // Limpiar tabla
  btnClear?.addEventListener('click', (e) => {
    e.preventDefault();
    resetAddPolizaView();
  });

  tbody.addEventListener('click', async (e) => {
    const btn = e.target.closest('.act-find-pdf');
    if (!btn) return;
    const idx = Number(btn.dataset.index);
    if (!Number.isFinite(idx)) return;
    const td = tbody.querySelector(`td[data-index="${idx}"][data-field="recibo"]`);
    const query = (td?.textContent || '').trim();
    if (!query) return;
    let url = '';
    let label = 'PDF';
    if (lastUploadedFilename) {
      const safe = encodeURIComponent(lastUploadedFilename);
      let page = '';
      try {
        const qs = new URLSearchParams({ filename: lastUploadedFilename, q: query }).toString();
        const r = await fetch(`/api/pdf/search?${qs}`);
        const j = await r.json().catch(() => ({}));
        if (j && j.ok && j.page) page = String(j.page);
      } catch (_) {}
      url = `/uploads/${safe}${page ? `#page=${page}&search=${encodeURIComponent(query)}` : `#search=${encodeURIComponent(query)}`}`;
      label = `PDF: ${lastUploadedFilename}`;
    } else if (fileEl?.files?.[0]) {
      const blobUrl = URL.createObjectURL(fileEl.files[0]);
      url = `${blobUrl}#search=${encodeURIComponent(query)}`;
      label = `PDF local: ${fileEl.files[0].name}`;
    } else {
      showInfoDialog('Sin PDF', 'Aún no hay PDF para buscar. Sube uno primero.');
      return;
    }
    const titleEl = document.getElementById('pdfModalLabel');
    if (titleEl) titleEl.textContent = label;
    if (typeof window.openPdfInModal === 'function') {
      window.openPdfInModal(url);
    } else {
      window.open(url, '_blank', 'noopener');
    }
  });

  // Agregar póliza
  btnAgregarPoliza?.addEventListener('click', () => {
    const formaPago = tipoPagoTopEl?.value || '';
    const estado    = estadoTopEl?.value || 'PENDIENTE';
    // const ramoTop   = (ramoProductoTopEl?.value || '').trim(); // REMOVED
    const pctCC     = (pctComCompaniaEl?.value || '').trim();
    const pctSA     = (pctComSubAgenteEl?.value || '').trim() || '100';
    const nroOpTop  = (nroOperacionTopEl?.value || '').trim(); // NUEVO

    const blank = normalizeItem({
      numero_poliza: '',
      recibo: '',
      nro: nroOpTop, // prellenar con global
      colectivo_asegurado: '',
      inicio_vigencia: '',
      vencimiento: '',
      moneda: '',
      fecha_emision: '',
      //ultimo_dia_pago: '',
      fecha_vencimiento: '',   // agregado: permite editar/ver la columna
      factura: '',
      fecha_pago: '',
      prima_neta: '',
      prima_comercial: '',
      prima_comercial_igv: '',
      // Campo 'ramo' debe ser independiente: lo dejamos vacío
      ramo: '',
      // Prellenamos 'ramos_producto' con el del cliente si existe
      ramos_producto: (window.selectedCliente && window.selectedCliente.ramos_producto) || '',
      forma_pago: formaPago,
      estado: estado,
      comision_compania_pct: pctCC,
      comision_compania_importe: '',
      comision_subagente_pct: pctSA,
      comision_subagente_importe: ''
    });
  
    if (blank.comision_compania_pct && blank.prima_neta) {
      blank.comision_compania_importe = computeCommissionAmount(blank.prima_neta, blank.comision_compania_pct);
    }
    if (blank.comision_subagente_pct && blank.comision_compania_importe) {
      blank.comision_subagente_importe = computeSubAgentCommissionAmount(blank.comision_compania_importe, blank.comision_subagente_pct);
    }

    extractedItems.push(blank);
    render(extractedItems);

    if (impComCompaniaEl) impComCompaniaEl.value = sumCommission(extractedItems);

    const newIndex = extractedItems.length - 1;
    setTimeout(() => {
      const firstCell = tbody.querySelector(`td[data-index="${newIndex}"][data-field="recibo"]`);
      firstCell?.focus();
    }, 0);

    scheduleAutoSave();
  });

  // Upload handler
  btnUpload?.addEventListener('click', () => {
    const file = fileEl?.files?.[0];
    if (!file) { alert('Selecciona un PDF.'); return; }

    openLoadingSwal('Procesando PDF…');
    const startTs = performance.now();
    btnUpload.disabled = true;
    if (issuerEl) issuerEl.disabled = true;
    fileEl.disabled = true;
    btnUpload.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Extrayendo…`;

    const fd = new FormData();
    fd.append('file', file);
    if (issuerEl && issuerEl.value) {
      fd.append('issuer', issuerEl.value);
    }
    fd.append('debug', '1');

    fetch('/upload', { method: 'POST', body: fd })
      .then(async (r) => {
        try {
          const ct = (r.headers.get('content-type') || '').toLowerCase();
          const rawText = await r.text();
          let payload;
          if (ct.includes('application/json')) {
            payload = JSON.parse(rawText);
          } else {
            try { payload = JSON.parse(rawText); } catch (e) { payload = rawText; }
          }

          console.log('[upload] status:', r.status, 'payload:', payload);

          if (payload && Array.isArray(payload.debug)) {
            payload.debug.forEach((line) => console.log('[server]', line));
          }

          // Manejo de PDF protegido con contraseña
          if (!r.ok && payload && payload.need_password) {
            try {
              const choice = await (window.Swal ? Swal.fire({
                title: 'PDF protegido',
                text: 'Este documento requiere contraseña para extraer los datos. ¿Deseas anexarlo sin extraer o ingresar contraseña para extraer?',
                showDenyButton: true,
                showCancelButton: true,
                confirmButtonText: 'Ingresar contraseña',
                denyButtonText: 'Anexar sin extraer',
                cancelButtonText: 'Cancelar',
                allowOutsideClick: false
              }) : Promise.resolve({ isConfirmed: false, isDenied: true }));
              if (choice.isDenied) {
                allAnexos.push(file);
                if (typeof renderAnexosList === 'function') renderAnexosList();
                else if (anexosListEl) anexosListEl.innerHTML = '';
                return;
              }
              if (!choice.isConfirmed) {
                alert('Extracción cancelada.');
                return;
              }
              const pw = await (window.Swal ? Swal.fire({
                title: 'Ingresar contraseña',
                input: 'password',
                inputLabel: 'Contraseña',
                inputAttributes: { autocapitalize: 'off', autocomplete: 'current-password' },
                showCancelButton: true,
                confirmButtonText: 'Continuar',
                cancelButtonText: 'Cancelar',
                allowOutsideClick: false
              }) : Promise.resolve({ isConfirmed: false, value: '' }));
              if (!pw.isConfirmed || !pw.value) { alert('Extracción cancelada.'); return; }
              const fd2 = new FormData();
              fd2.append('file', file);
              if (issuerEl && issuerEl.value) {
                fd2.append('issuer', issuerEl.value);
              }
              fd2.append('pdf_password', pw.value);
              fd2.append('debug', '1');
              const r2 = await fetch('/upload', { method: 'POST', body: fd2 });
              const ct2 = (r2.headers.get('content-type') || '').toLowerCase();
              const raw2 = await r2.text();
              let payload2;
              if (ct2.includes('application/json')) {
                payload2 = JSON.parse(raw2);
              } else {
                try { payload2 = JSON.parse(raw2); } catch (e) { payload2 = raw2; }
              }
              if (!r2.ok) {
                alert(typeof payload2 === 'string' ? payload2 : (payload2.error || 'Error al extraer datos con contraseña.'));
                return;
              }
              payload = payload2;
              r = r2;
            } catch (pwErr) {
              console.error('password flow error', pwErr);
              alert('No se pudo procesar el PDF protegido.');
              return;
            }
          }

          if (!r.ok) {
            alert(typeof payload === 'string' ? payload : (payload.error || 'Error al extraer datos.'));
            return;
          }

          if (payload && typeof payload.filename === 'string') {
            lastUploadedFilename = payload.filename;
          }

          if (payload && payload.provider) {
            setIssuerFromProvider(payload.provider);
          }

          let items = [];
          if (payload.items && Array.isArray(payload.items)) {
            items = payload.items.map(normalizeItem);
            console.log('[upload] items normalizados:', items); // verificar fechas antes de render
          } else if (payload.fields && typeof payload.fields === 'object') {
            items = [normalizeItem(payload.fields)];
            console.log('[upload] item normalizado (fields):', items[0]); // verificar fechas
          }

          const tipoPago = tipoPagoTopEl?.value || '';
          const estado   = estadoTopEl?.value || 'PENDIENTE';
          const pctCC    = pctComCompaniaEl?.value || '';
          const pctSA    = pctComSubAgenteEl?.value || '100';
          const impSA    = impComSubAgenteEl?.value || '';
          // NUEVO: Obtener producto por defecto del cliente si existe
          const defaultProducto = (window.selectedCliente && window.selectedCliente.ramos_producto) || '';

          items = items.map(it => {
            const importeCC = pctCC ? computeCommissionAmount(it.prima_neta, pctCC) : '';
            const importeSA = (pctSA && importeCC) ? computeSubAgentCommissionAmount(importeCC, pctSA) : impSA;
            // Si no viene producto del PDF, usar el del cliente
            const rProd = (it.ramos_producto && it.ramos_producto.trim()) ? it.ramos_producto : defaultProducto;
            
            return {
              ...it,
              ramos_producto: rProd,
              forma_pago: tipoPago || it.forma_pago || '',
              estado: estado || it.estado || 'PENDIENTE',
              comision_compania_pct: pctCC,
              comision_compania_importe: importeCC,
              comision_subagente_pct: pctSA,
              comision_subagente_importe: importeSA
            };
          });

          await ensureIssuerOptionsLoaded();
          const issuerOpts = getIssuerOptions();
          function pickLPVVariantByText(txt) {
            const t = (txt || '').toString().toLowerCase();
            if (t.includes('eps') || t.includes('entidad prestadora') || t.includes('salud') || t.includes('lpeps')) return 'lpv-eps';
            if (t.includes('vida') && t.includes('ley')) return 'lpv-vida-ley';
            if (t.includes('vida')) return 'lpv-vida';
            if (t.includes('pension') || t.includes('pensión')) return 'lpv-pension';
            return 'positiva';
          }
          function pickCrecerVariantByText(txt) {
            const t = (txt || '').toString().toLowerCase();
            return 'crecer';
          }
          function preferOption(val, label) {
            const v = (val || '').trim();
            if (v && issuerOpts.some(o => o.value === v)) return v;
            const l = (label || '').trim();
            if (l) {
              const byText = issuerOpts.find(o => (o.text || '').toLowerCase() === l.toLowerCase());
              if (byText) return byText.value;
              const inc = issuerOpts.find(o => (o.text || '').toLowerCase().includes(l.toLowerCase()));
              if (inc) return inc.value;
            }
            return v || '';
          }
          function normIssuerText(text) {
            const s = (text || '').toString().toLowerCase();
            try {
              return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
            } catch (e) {
              return s;
            }
          }
          function hasToken(normText, token) {
            const t = normIssuerText(normText);
            const re = new RegExp(`(^|[^a-z0-9])${token}([^a-z0-9]|$)`);
            return re.test(t);
          }
          function detectSlugFromText(text) {
            const t = (text || '').toString().toLowerCase();
            if (!t) return '';
            if (hasToken(t, 'rimac')) return 'rimac';
            if (t.includes('hdi')) return 'hdi';
            if (t.includes('ohio')) return 'ohio';
            if (t.includes('qualitas') || t.includes('quálitas')) return 'qualitas';
            if (t.includes('avla')) return 'avla';
            if (t.includes('grandia') && t.includes('eps')) return 'grandia-eps';
            if (t.includes('crecer')) return pickCrecerVariantByText(t);
            // Priorizar sanitas por encima del caso genérico "EPS"
            if (t.includes('sanitas')) return 'sanitas';
            // Positiva/LPV (incluye EPS genérico solo si no se detectó "sanitas")
            if (t.includes('positiva') || t.includes('lpv') || t.includes('vida ley') || t.includes('eps') || t.includes('entidad prestadora') || t.includes('salud') || t.includes('lpeps')) return pickLPVVariantByText(t);
            if (t.includes('mapfre')) return 'mapfre';
            if (t.includes('pacifico') || t.includes('pacífico')) return 'pacifico';
            if (t.includes('protecta') || t.includes('proctecta')) return 'proctecta';
            return '';
          }
          function inferIssuerForItem(it, provider) {
            const p = (provider || '').toString();
            const haystack = [
              it.cia, it.aseguradora, it.asegurado, it.asegurada, it.colectivo_asegurado,
              it.producto, it.ramos_producto, it.ramo, p
            ].filter(Boolean).join(' | ');
            const slug = detectSlugFromText(haystack);
            if (slug) return preferOption(slug, slug);
            // Fallback: buscar por coincidencia de texto en opciones
            const t = haystack.toLowerCase();
            const inc = issuerOpts.find(o => (o.text || '').toLowerCase() && t.includes((o.text || '').toLowerCase()));
            return inc ? inc.value : '';
          }
          items = items.map(it => {
            const already = ((it.cia_value || '').trim() || (it.cia || '').trim());
            if (already) return it;
            const val = inferIssuerForItem(it, (payload && payload.provider) ? String(payload.provider) : '');
            if (!val) return it;
            const opt = issuerOpts.find(o => o.value === val);
            return { ...it, cia_value: val, cia: (opt ? opt.text : (it.cia || '')) || it.cia };
          });

          extractedItems = items;
          render(extractedItems);

          try {
            const missingDocIdx = (extractedItems || []).findIndex(it => {
              const doc = (it && it.numero_documento_extracted != null) ? String(it.numero_documento_extracted).trim() : '';
              return doc === '';
            });
            if (missingDocIdx >= 0) {
              const msg = `Fila ${missingDocIdx + 1}: falta el número de documento (DNI/RUC) en la columna "Documento".`;
              if (window.Swal) Swal.fire({ icon: 'warning', title: 'Documento vacío', text: msg });
              else alert(msg);
              const td = getTd(missingDocIdx, 'numero_documento_extracted');
              td?.focus();
            }
          } catch (_) {}

          // Autocompletar % comisión de compañía desde la tabla comisiones_temp (servidor)
          try {
            const fillPromises = extractedItems.map(async (it, i) => {
              const hasPct = it.comision_compania_pct !== undefined && it.comision_compania_pct !== null && String(it.comision_compania_pct).trim() !== '';
              if (!hasPct) {
                 await fetchCommissionPct(i);
              }
            });
            await Promise.all(fillPromises);
          } catch (e) {
             console.error('Error autocompleting commissions:', e);
          }

          const elapsed = ((performance.now() - startTs) / 1000).toFixed(2);
          if (hint) {
            hint.textContent = items.length
              ? `Se extrajeron ${items.length} ítem(s) en ${elapsed}s. Revisa y guarda.`
              : `Sin datos. Procesado en ${elapsed}s.`;
          }
        } catch (e) {
          console.error('[upload] processing error]:', e);
          alert('Error procesando respuesta del servidor.');
        }
      })
      .catch((err) => {
        console.error('[upload] fetch error:', err);
        alert('No se pudo conectar con el servidor (/upload).');
      })
      .finally(() => {
        closeLoadingSwal();
        btnUpload.disabled = false;
        if (issuerEl) issuerEl.disabled = false;
        fileEl.disabled = false;
        btnUpload.textContent = 'Extraer datos';
      });
  });

  // Preseleccionar subagente si viene del servidor
  if (subAgenteEl && window.selectedCliente) {
    subAgenteEl.value = window.selectedCliente.subagente || '';
  }

  function showInfoDialog(title, text) {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    if (window.Swal) {
      Swal.fire({
        icon: 'info',
        title: title || 'Aviso',
        text: text || '',
        confirmButtonText: 'Aceptar',
        confirmButtonColor: '#3b82f6',
        background: isDark ? '#1a1a1a' : '#ffffff',
        color: isDark ? '#ffffff' : '#333333',
        customClass: {
          popup: 'rounded-4',
          confirmButton: 'rounded-pill px-4'
        }
      });
      return;
    }
    alert(text || title || 'Aviso');
  }

  // % Comisión Cía superior → recalcular todas las filas
  pctComCompaniaEl?.addEventListener('input', () => {
    const pct = pctComCompaniaEl.value || '';
    if (!extractedItems || !extractedItems.length) {
      if (impComCompaniaEl) impComCompaniaEl.value = '';
      return;
    }
    extractedItems = extractedItems.map(it => ({
      ...it,
      comision_compania_pct: pct,
      comision_compania_importe: pct ? computeCommissionAmount(it.prima_neta, pct) : ''
    }));
    render(extractedItems);
    if (impComCompaniaEl) impComCompaniaEl.value = sumCommission(extractedItems);
    scheduleAutoSave();
  });

  // Modal PDF
  const btnVerPDF = document.getElementById('btnVerPDF');
  const pdfModalEl = document.getElementById('pdfModal');
  const pdfFrameEl = document.getElementById('pdfFrame');
  const pdfOpenNewTabEl = document.getElementById('pdfOpenNewTab');
  let pdfModalInstance = null;
  if (pdfModalEl && window.bootstrap) {
    pdfModalInstance = new bootstrap.Modal(pdfModalEl, { backdrop: 'static' });
  }

  btnVerPDF?.addEventListener('click', () => {
    let src = '';
    let label = 'Vista de PDF';
    if (lastUploadedFilename) {
      const safe = encodeURIComponent(lastUploadedFilename);
      src = `/uploads/${safe}`; // ruta servidor
      label = `PDF: ${lastUploadedFilename}`;
    } else if (fileEl?.files?.[0]) {
      const blobUrl = URL.createObjectURL(fileEl.files[0]);
      src = blobUrl;
      label = `PDF local (no subido): ${fileEl.files[0].name}`;
    } else {
      showInfoDialog('Sin PDF', 'Aún no hay PDF para visualizar. Sube uno primero.');
      return;
    }

    if (pdfFrameEl) pdfFrameEl.src = src;
    if (pdfOpenNewTabEl) pdfOpenNewTabEl.href = src;
    const titleEl = document.getElementById('pdfModalLabel');
    if (titleEl) titleEl.textContent = label;

    if (pdfModalInstance) {
      pdfModalInstance.show();
    } else {
      window.open(src, '_blank', 'noopener');
    }
  });

  pdfModalEl?.addEventListener('hidden.bs.modal', () => {
    try { if (pdfFrameEl) pdfFrameEl.src = 'about:blank'; } catch (e) {}
  });

  // Guardado manual (btnSave) - UN SOLO HANDLER + GUARD CLAUSE
  btnSave?.addEventListener('click', async (e) => {
    try { e.preventDefault(); } catch (_) {}
    try { e.stopPropagation(); } catch (_) {}
    if (isSaving) return; // evita clics repetidos
    isSaving = true;
    try {
      const tipoDocSel = (tipoDocTopEl?.value || '').toString().trim();
      if (!tipoDocSel) {
        isSaving = false;
        if (window.Swal) Swal.fire({ icon: 'warning', title: 'Falta completar', text: 'Selecciona el Tipo de Doc antes de guardar.' });
        else alert('Selecciona el Tipo de Doc antes de guardar.');
        if (btnSave) btnSave.disabled = (extractedItems || []).length === 0 || true;
        return;
      }
      const tipoPagoSel = (tipoPagoTopEl?.value || '').toString().trim();
      if (!tipoPagoSel) {
        isSaving = false;
        if (window.Swal) Swal.fire({ icon: 'warning', title: 'Falta completar', text: 'Selecciona el Tipo de Pago antes de guardar.' });
        else alert('Selecciona el Tipo de Pago antes de guardar.');
        if (btnSave) {
          const hasTipoDoc = ((tipoDocTopEl?.value || '').toString().trim() !== '');
          btnSave.disabled = (extractedItems || []).length === 0 || !hasTipoDoc || true;
        }
        return;
      }
      const tipoVigenciaSeleccionada = resolveTipoVigenciaForSave(extractedItems);
      if (!tipoVigenciaSeleccionada || tipoVigenciaSeleccionada === '__MIXED__') {
        isSaving = false;
        const msg = tipoVigenciaSeleccionada === '__MIXED__'
          ? 'Las filas tienen vigencias distintas. Ajusta Inicio/Fin de vigencia para que sean mensual, trimestral o anual.'
          : 'No se pudo determinar el Tipo de Vigencia. Revisa Inicio y Fin de vigencia (mensual, trimestral o anual).';
        if (window.Swal) Swal.fire({ icon: 'warning', title: 'Tipo de vigencia', text: msg });
        else alert(msg);
        if (btnSave) {
          const hasTipoDoc = ((tipoDocTopEl?.value || '').toString().trim() !== '');
          const hasTipoPago = ((tipoPagoTopEl?.value || '').toString().trim() !== '');
          btnSave.disabled = (extractedItems || []).length === 0 || !hasTipoDoc || !hasTipoPago;
        }
        return;
      }
      if (btnSave) btnSave.disabled = true;

      const selected = Object.assign({}, (window.selectedCliente || {}), {
        subagente: (document.getElementById('subAgenteTop')?.value ||
                    document.getElementById('subAgente')?.value ||
                    (window.selectedCliente || {}).subagente || ''),
        motivo: '', // (motivoTopEl?.value || '').trim(),
        // ramos_producto: (ramoProductoTopEl?.value || '').trim(), // REMOVED
        tipo_doc: (tipoDocTopEl?.value || '').trim() || ((window.selectedCliente || {}).tipo_doc || (window.selectedCliente || {}).tipo_documento || ''),
        // NUEVO: ejecutivo desde el select superior
        ejecutivo: (ejecutivoTopEl?.value || '').trim(),
        // NUEVO: campos endosatario y tipo vigencia
        endosatario: (endosatarioTopEl?.value || '').trim(),
        tipo_vigencia: tipoVigenciaSeleccionada,
        pdf_filename: lastUploadedFilename
      });

      const missingDocIdx = (extractedItems || []).findIndex(it => {
        const doc = (it && it.numero_documento_extracted != null) ? String(it.numero_documento_extracted).trim() : '';
        return doc === '';
      });
      if (missingDocIdx >= 0) {
        isSaving = false;
        const msg = `Fila ${missingDocIdx + 1}: falta el número de documento (DNI/RUC) en la columna "Documento".`;
        if (window.Swal) Swal.fire({ icon: 'warning', title: 'Documento vacío', text: msg });
        else alert(msg);
        try {
          const td = getTd(missingDocIdx, 'numero_documento_extracted');
          td?.focus();
        } catch (_) {}
        if (btnSave) {
          const hasTipoDoc = ((tipoDocTopEl?.value || '').toString().trim() !== '');
          const hasTipoPago = ((tipoPagoTopEl?.value || '').toString().trim() !== '');
          btnSave.disabled = (extractedItems || []).length === 0 || !hasTipoDoc || !hasTipoPago;
        }
        return;
      }

      // Asegurar 'asegurado' y limpiar 'ramo' si no coincide con abbrs; forzar ramos_producto desde el bloque superior si existe
      const abbrs = (window.ramosAbbrs || []).map(s => (s || '').trim());
      const nroOpTopSave = (nroOperacionTopEl?.value || '').trim(); // NUEVO: leer valor al guardar

      const isNETEO = ((tipoDocSel || '').toString().trim().toUpperCase() === 'NETEO');
      const itemsForAuto = (extractedItems || []).map(it => {
        const copy = { ...it };
        if (copy.colectivo_asegurado && !copy.asegurado) {
          copy.asegurado = copy.colectivo_asegurado;
        }
        // Alinear fecha de pago con ultimo_dia_pago para el backend
        if (!copy.ultimo_dia_pago && copy.fecha_pago) {
          copy.ultimo_dia_pago = copy.fecha_pago;
        }
        // Alinear factura con recibo si procede
        if (!copy.recibo && copy.factura) {
          copy.recibo = copy.factura;
        }
        const r = (copy.ramo || '').trim();
        if (r && !abbrs.includes(r)) {
          copy.ramo = '';
        }
        // const rpTop = (selected.ramos_producto || '').trim(); // REMOVED
        // if (rpTop) {
        //   copy.ramos_producto = rpTop;
        // }
        // NUEVO: aplicar nro operación global si existe (sobrescribe o rellena)
        if (nroOpTopSave) {
          copy.nro = nroOpTopSave;
        }
        if (isNETEO) {
          copy.estado = 'SIN PRIMA';
          copy.forma_pago = 'SIN PRIMA';
        }
        return copy;
      });

      // NUEVO: Log para verificar lo que se envía
      console.log('[save:manual] sending selected:', selected);

      // PREPARAR FORMDATA (para incluir archivos anexos)
      const formData = new FormData();
      formData.append('json_data', JSON.stringify({ items: itemsForAuto, selected }));

      // Usar allAnexos (acumulados) en lugar de anexosFilesEl.files
      if (allAnexos && allAnexos.length > 0) {
        allAnexos.forEach(file => {
          formData.append('anexos', file);
        });
      }
      const hasRowFacturas = rowFacturasMap && rowFacturasMap.size > 0;
      if (hasRowFacturas) {
        Array.from(rowFacturasMap.entries()).forEach(([i, files]) => {
          (files || []).forEach(file => {
            formData.append(`facturas_${i}`, file);
          });
        });
      } else {
        if (allFacturas && allFacturas.length > 0) {
          allFacturas.forEach(file => {
            formData.append('facturas', file);
          });
        }
      }

      const r = await fetch('/polizas/save', {
        method: 'POST',
        body: formData
      });

      const ct = (r.headers.get('content-type') || '').toLowerCase();
      const raw = await r.text();
      let payload;
      try { payload = JSON.parse(raw); } catch (e) { payload = { rawText: raw }; }

      console.log('[save:manual] status:', r.status, 'payload:', payload);

      if (!r.ok || !payload?.ok) {
        const msg = (payload?.errors && Array.isArray(payload.errors) && payload.errors.join('; '))
          || payload?.error
          || payload?.rawText
          || 'Error al guardar pólizas.';
        if (window.Swal) Swal.fire({ icon: 'error', title: 'No se guardó', text: msg });
        else alert(msg);
        return;
      }

      if (window.Swal) Swal.fire({ icon: 'success', title: 'Guardado', text: `Se insertaron ${payload.count} póliza(s).` });
      if (hint) hint.textContent = `Guardado manual: ${payload.count}.`;
      resetAddPolizaView();
    } catch (err) {
      console.error('[save:manual] error:', err);
      if (window.Swal) Swal.fire({ icon: 'error', title: 'Error de red', text: String(err) });
      else alert('No se pudo conectar con el servidor (/polizas/save).');
    } finally {
      isSaving = false;
      if (btnSave) btnSave.disabled = (extractedItems || []).length === 0;
    }
  });

  // Sincronizar cambios del bloque superior
  issuerEl?.addEventListener('change', () => {
    const text = issuerEl?.options?.[issuerEl.selectedIndex]?.text || (issuerEl?.value || '');
    extractedItems = (extractedItems || []).map(it => ({ ...it, cia: text }));
    render(extractedItems);
  });

  tipoPagoTopEl?.addEventListener('change', () => {
    const val = (tipoPagoTopEl?.value || '').trim();
    extractedItems = (extractedItems || []).map(it => ({ ...it, forma_pago: val }));
    render(extractedItems);
    if (btnSave) {
      const hasTipoDoc = ((tipoDocTopEl?.value || '').toString().trim() !== '');
      const hasTipoPago = ((tipoPagoTopEl?.value || '').toString().trim() !== '');
      btnSave.disabled = (extractedItems || []).length === 0 || !hasTipoDoc || !hasTipoPago;
    }
  });

  estadoTopEl?.addEventListener('change', () => {
    const val = (estadoTopEl?.value || '').trim();
    extractedItems = (extractedItems || []).map(it => ({ ...it, estado: val }));
    render(extractedItems);
  });

  tipoDocTopEl?.addEventListener('change', () => {
    const val = (tipoDocTopEl?.value || '').trim().toUpperCase();
    if (val === 'NETEO') {
      resetAddPolizaView(true);
      if (tipoPagoTopEl) {
        tipoPagoTopEl.value = 'SIN PRIMA';
        tipoPagoTopEl.dispatchEvent(new Event('change'));
      }
      if (estadoTopEl) {
        estadoTopEl.value = 'SIN PRIMA';
        estadoTopEl.dispatchEvent(new Event('change'));
      } else {
        // Forzar estado en el modelo aunque no exista el campo en UI
        extractedItems = (extractedItems || []).map(it => ({ ...it, estado: 'SIN PRIMA' }));
        render(extractedItems);
      }
    } else {
      if (tipoPagoTopEl) {
        tipoPagoTopEl.value = '';
        tipoPagoTopEl.dispatchEvent(new Event('change'));
      }
      if (estadoTopEl) {
        estadoTopEl.value = '';
        if (estadoTopEl.value !== '') {
          estadoTopEl.selectedIndex = 0;
        }
        estadoTopEl.dispatchEvent(new Event('change'));
      } else {
        // Limpiar estado en el modelo si no hay campo de UI
        extractedItems = (extractedItems || []).map(it => {
          const copy = { ...it };
          delete copy.estado;
          return copy;
        });
        render(extractedItems);
      }
    }
    if (btnSave) {
      const hasTipoDoc = ((tipoDocTopEl?.value || '').toString().trim() !== '');
      const hasTipoPago = ((tipoPagoTopEl?.value || '').toString().trim() !== '');
      btnSave.disabled = (extractedItems || []).length === 0 || !hasTipoDoc || !hasTipoPago;
    }
  });

  /* REMOVED: ramoProductoTopEl listener
  ramoProductoTopEl?.addEventListener('input', () => {
    const val = (ramoProductoTopEl?.value || '').trim();
    if (!val) return;
    extractedItems = (extractedItems || []).map(it => {
      if (!it.ramos_producto || it.ramos_producto.trim() === '') {
        return { ...it, ramos_producto: val };
      }
      return it;
    });
    render(extractedItems);
    scheduleAutoSave();
  });
  */

  // NUEVO: Anexos (acumulativo)
  function renderAnexosList() {
    if (!anexosListEl) return;
    if (allAnexos.length === 0) {
      anexosListEl.innerHTML = '<span class="text-muted">Sin anexos seleccionados.</span>';
      return;
    }
    let html = '<ul class="list-unstyled mb-0">';
    allAnexos.forEach((file, idx) => {
      html += `
        <li class="d-flex justify-content-between align-items-center mb-1">
          <span class="text-truncate me-2" style="max-width: 200px;" title="${file.name}">
            <i class="bi bi-paperclip me-1"></i>${file.name}
          </span>
          <div class="d-flex align-items-center gap-2">
            <button type="button" class="btn btn-sm btn-outline-secondary p-0 px-2 btn-view-anexo" data-index="${idx}" title="Ver">
              <i class="bi bi-eye"></i>
            </button>
          <button type="button" class="btn btn-sm btn-link text-danger p-0 border-0 btn-remove-anexo" data-index="${idx}">
            <i class="bi bi-x-circle"></i>
          </button>
          </div>
        </li>
      `;
    });
    html += '</ul>';
    anexosListEl.innerHTML = html;

    // Listener para eliminar
    anexosListEl.querySelectorAll('.btn-remove-anexo').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = Number(e.currentTarget.dataset.index);
        if (Number.isFinite(idx)) {
          allAnexos.splice(idx, 1);
          renderAnexosList();
        }
      });
    });
    // Listener para ver
    anexosListEl.querySelectorAll('.btn-view-anexo').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = Number(e.currentTarget.dataset.index);
        const file = Number.isFinite(idx) ? allAnexos[idx] : null;
        if (!file) return;
        try {
          const url = URL.createObjectURL(file);
          const titleEl = document.getElementById('pdfModalLabel');
          if (titleEl) titleEl.textContent = `Anexo: ${file.name}`;
          if (typeof window.openPdfInModal === 'function') {
            window.openPdfInModal(url);
          } else {
            window.open(url, '_blank', 'noopener');
          }
          setTimeout(() => { try { URL.revokeObjectURL(url); } catch (_) {} }, 10000);
        } catch (err) {
          console.error('preview anexo error', err);
          alert('No se pudo abrir el anexo para vista previa.');
        }
      });
    });
  }

  function renderFacturasList() {
    if (!facturasListEl) return;
    if (allFacturas.length === 0) {
      facturasListEl.innerHTML = '<span class="text-muted">Sin facturas seleccionadas.</span>';
      return;
    }
    let html = '<ul class="list-unstyled mb-0">';
    allFacturas.forEach((file, idx) => {
      const meta = facturaMetaMap.get(keyForFile(file));
      const metaText = meta ? `<small class="text-muted ms-2">(Factura: ${meta.factura || '—'}; Pago: ${meta.fecha_pago || '—'})</small>` : '';
      html += `
        <li class="d-flex justify-content-between align-items-center mb-1">
          <span class="text-truncate me-2" style="max-width: 200px;" title="${file.name}">
            <i class="bi bi-receipt me-1"></i>${file.name}${metaText}
          </span>
          <div class="d-flex align-items-center gap-2">
            <button type="button" class="btn btn-sm btn-outline-secondary p-0 px-2 btn-view-factura" data-index="${idx}" title="Ver">
              <i class="bi bi-eye"></i>
            </button>
            <button type="button" class="btn btn-sm btn-link text-danger p-0 border-0 btn-remove-factura" data-index="${idx}">
              <i class="bi bi-x-circle"></i>
            </button>
          </div>
        </li>
      `;
    });
    html += '</ul>';
    facturasListEl.innerHTML = html;
    facturasListEl.querySelectorAll('.btn-remove-factura').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = Number(e.currentTarget.dataset.index);
        if (Number.isFinite(idx)) {
          allFacturas.splice(idx, 1);
          renderFacturasList();
        }
      });
    });
    facturasListEl.querySelectorAll('.btn-view-factura').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = Number(e.currentTarget.dataset.index);
        const file = Number.isFinite(idx) ? allFacturas[idx] : null;
        if (!file) return;
        try {
          const url = URL.createObjectURL(file);
          const titleEl = document.getElementById('pdfModalLabel');
          if (titleEl) titleEl.textContent = `Factura: ${file.name}`;
          if (typeof window.openPdfInModal === 'function') {
            window.openPdfInModal(url);
          } else {
            window.open(url, '_blank', 'noopener');
          }
          setTimeout(() => { try { URL.revokeObjectURL(url); } catch (_) {} }, 10000);
        } catch (err) {
          console.error('preview factura error', err);
          alert('No se pudo abrir la factura para vista previa.');
        }
      });
    });
  }

  // Cargar aseguradoras si no existe select global y refrescar selects por fila
  (async () => {
    await ensureIssuerOptionsLoaded();
    const opts = getIssuerOptions();
    if (opts && opts.length) {
      Array.from(document.querySelectorAll('.issuer-row')).forEach(sel => {
        const current = (sel.value || '').trim();
        const html = ['<option value="">Selecciona...</option>'].concat(
          opts.map(o => `<option value="${o.value}" ${o.value === current ? 'selected' : ''}>${o.text}</option>`)
        ).join('');
        sel.innerHTML = html;
      });
    }
  })();

  anexosFilesEl?.addEventListener('change', () => {
    if (!anexosFilesEl.files || anexosFilesEl.files.length === 0) return;
    
    // Acumular archivos
    Array.from(anexosFilesEl.files).forEach(file => {
      // Evitar duplicados por nombre y tamaño (básico)
      const exists = allAnexos.some(f => f.name === file.name && f.size === file.size);
      if (!exists) {
        allAnexos.push(file);
      }
    });

    // Limpiar input para permitir seleccionar el mismo archivo de nuevo si se borró
    anexosFilesEl.value = '';
    renderAnexosList();
  });

  // Aux: almacenar metadatos extraídos por archivo
  const facturaMetaMap = new Map(); // key(file) -> { factura, fecha_pago, provider }
  function keyForFile(f) { return `${f.name}:${f.size}:${f.lastModified}`; }
  function setCellValue(index, field, value) {
    if (!Number.isFinite(index) || !field) return;
    if (!extractedItems[index]) return;
    extractedItems[index][field] = value;
    const td = getTd(index, field);
    if (td) td.textContent = value || '';
  }
  async function extractFacturaMetaFromFile(file) {
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch('/cuotas/extract', { method: 'POST', body: fd, credentials: 'same-origin' });
      if (!r.ok) return { factura: '', fecha_pago: '' };
      const payload = await r.json().catch(() => ({}));
      const d = (payload && payload.data) ? payload.data : {};
      return {
        factura: d.factura || d.cupon || '',
        fecha_pago: d.fecha_pago || d.fecha_vencimiento || '',
        fecha_vencimiento: d.fecha_vencimiento || '',
        cuotas: Array.isArray(d.cuotas) ? d.cuotas : []
      };
    } catch (_) {
      return { factura: '', fecha_pago: '' };
    }
  }
  function mergeExtractedCuotas(index, meta) {
    if (!Number.isFinite(index) || !meta || !extractedItems[index]) return;
    if (!Array.isArray(meta.cuotas) || meta.cuotas.length === 0) return;
    extractedItems[index].cuotas = meta.cuotas.map(c => ({
      cupon: c.cupon || '',
      fecha_vencimiento: c.fecha_vencimiento || '',
      importe: c.importe || '',
      factura: c.factura || '',
      fecha_pago: c.fecha_pago || '',
      moneda: c.moneda || extractedItems[index].moneda || 'S/'
    }));
    if (!extractedItems[index].factura && extractedItems[index].cuotas[0]) {
      extractedItems[index].factura = extractedItems[index].cuotas[0].factura || '';
      extractedItems[index].fecha_pago = extractedItems[index].cuotas[0].fecha_pago || '';
      extractedItems[index].fecha_vencimiento = extractedItems[index].cuotas[0].fecha_vencimiento || extractedItems[index].fecha_vencimiento || '';
    }
    refreshCuotasUI(index);
  }
  function applyFacturaMeta(meta) {
    if (!meta) return;
    if (!extractedItems || extractedItems.length === 0) return;
    
    // Si hay varias filas: intentar por coincidencia de recibo/factura; si no, aplicar al primer hueco libre
    let idx = extractedItems.findIndex(it => {
      const rec = (it.recibo || '').toString().trim();
      const fac = (it.factura || '').toString().trim();
      return (meta.factura && (rec === meta.factura || fac === meta.factura));
    });
    
    if (idx < 0) {
      // Si no hay coincidencia, buscar la primera fila sin cuotas o la primera fila
      const emptyIdx = extractedItems.findIndex(it => !it.cuotas || it.cuotas.length === 0);
      idx = emptyIdx >= 0 ? emptyIdx : 0;
    }

    if (Array.isArray(meta.cuotas) && meta.cuotas.length > 0) {
      mergeExtractedCuotas(idx, meta);
      return;
    }

    if (extractedItems[idx] && (!extractedItems[idx].cuotas || extractedItems[idx].cuotas.length === 0)) {
      extractedItems[idx].factura = meta.factura || '';
      extractedItems[idx].fecha_pago = meta.fecha_pago || '';
      if (meta.fecha_vencimiento && !extractedItems[idx].fecha_vencimiento) {
        extractedItems[idx].fecha_vencimiento = meta.fecha_vencimiento;
      }
      updateRowFilesUI(idx);
      return;
    }

    if (!extractedItems[idx].cuotas) extractedItems[idx].cuotas = [];
    const exists = extractedItems[idx].cuotas.some(c => c.factura === meta.factura);
    if (!exists) {
      extractedItems[idx].cuotas.push({
        factura: meta.factura || '',
        fecha_pago: meta.fecha_pago || '',
        fecha_vencimiento: meta.fecha_vencimiento || '',
        importe: '',
        moneda: extractedItems[idx].moneda || 'S/'
      });
      refreshCuotasUI(idx);
    }
  }
  facturasFilesEl?.addEventListener('change', async () => {
    if (!facturasFilesEl.files || facturasFilesEl.files.length === 0) return;
    const files = Array.from(facturasFilesEl.files);
    for (const file of files) {
      const exists = allFacturas.some(f => f.name === file.name && f.size === file.size);
      if (!exists) {
        allFacturas.push(file);
        // Intentar extraer factura y fecha de pago de cada archivo
        const meta = await extractFacturaMetaFromFile(file);
        facturaMetaMap.set(keyForFile(file), meta);
        applyFacturaMeta(meta);
      }
    }
    facturasFilesEl.value = '';
    renderFacturasList();
  });

  // NUEVO: función para resetear tabla y campos superiores
  function resetAddPolizaView(keepTipoDoc = false) {
      extractedItems = [];
      if (tbody) tbody.innerHTML = '';
      if (btnSave) btnSave.disabled = true;
      if (hint) hint.textContent = 'Sube un PDF para ver información.';
      if (impComCompaniaEl) impComCompaniaEl.value = '';
      if (pctComCompaniaEl) pctComCompaniaEl.value = '';
      if (pctComSubAgenteEl) pctComSubAgenteEl.value = '100';
      if (impComSubAgenteEl) impComSubAgenteEl.value = '';
      // if (motivoTopEl) motivoTopEl.value = '';
      // if (ramoProductoTopEl) ramoProductoTopEl.value = '';
      if (tipoDocTopEl && !keepTipoDoc) tipoDocTopEl.value = '';
      if (issuerEl) issuerEl.value = '';
      if (anexosFilesEl) anexosFilesEl.value = '';
      allAnexos = [];
      if (typeof renderAnexosList === 'function') {
        renderAnexosList();
      } else if (anexosListEl) {
        anexosListEl.innerHTML = '';
      }
      if (facturasFilesEl) facturasFilesEl.value = '';
      allFacturas = [];
      rowFacturasMap = new Map();
      cuotaFacturaFileMap = new Map();
      if (typeof facturaMetaMap?.clear === 'function') facturaMetaMap.clear();
      if (typeof renderFacturasList === 'function') {
        renderFacturasList();
      } else if (facturasListEl) {
        facturasListEl.innerHTML = '';
      }
      if (aseguradaTopEl) aseguradaTopEl.value = '';
      if (nroOperacionTopEl) nroOperacionTopEl.value = '';
      if (endosatarioTopEl) endosatarioTopEl.value = '';
      if (tipoVigenciaTopEl) {
        tipoVigenciaTopEl.value = '';
        if (tipoVigenciaTopEl.selectedIndex !== 0) tipoVigenciaTopEl.selectedIndex = 0;
      }
      tipoVigenciaManualOverride = false;
      if (tipoPagoTopEl) {
        tipoPagoTopEl.value = '';
        if (tipoPagoTopEl.selectedIndex !== 0) tipoPagoTopEl.selectedIndex = 0;
        tipoPagoTopEl.dispatchEvent(new Event('change'));
      }
      if (estadoTopEl) {
        estadoTopEl.value = '';
        if (estadoTopEl.selectedIndex !== 0) estadoTopEl.selectedIndex = 0;
        estadoTopEl.dispatchEvent(new Event('change'));
      }
      if (fileEl) fileEl.value = '';
      const pdfFrameEl = document.getElementById('pdfFrame');
      if (pdfFrameEl) pdfFrameEl.src = 'about:blank';
      if (typeof pdfModalInstance?.hide === 'function') pdfModalInstance.hide();
      if (pdfOpenNewTabEl) pdfOpenNewTabEl.href = 'about:blank';
      // Eliminar archivo temporal del servidor si existe
      if (lastUploadedFilename) {
        const tempName = lastUploadedFilename;
        lastUploadedFilename = null;
        fetch('/upload/temp/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: tempName })
        }).catch(() => {});
      } else {
        lastUploadedFilename = null;
      }
      render(extractedItems);
  }

  function resetFieldsAfterSave() {
    const rows = Array.from(tbody?.querySelectorAll('tr') || []);
    rows.forEach((tr, idx) => {
      if (extractedItems[idx]) {
        extractedItems[idx].cuotas = [];
        extractedItems[idx].numero_documento_extracted = '';
      }
      refreshCuotasUI(idx);
      const tdDoc = getTd(idx, 'numero_documento_extracted');
      if (tdDoc) tdDoc.textContent = '';
      rowFacturasMap.set(idx, []);
      Array.from(cuotaFacturaFileMap.keys()).forEach(k => {
        if (String(k).startsWith(`${idx}:`)) cuotaFacturaFileMap.delete(k);
      });
      updateRowFilesUI(idx);
    });
    allFacturas = [];
    if (facturasFilesEl) facturasFilesEl.value = '';
    if (typeof renderFacturasList === 'function') {
      renderFacturasList();
    } else if (facturasListEl) {
      facturasListEl.innerHTML = '';
    }
    const hasTipoDoc = ((tipoDocTopEl?.value || '').toString().trim() !== '');
    const hasTipoPago = ((tipoPagoTopEl?.value || '').toString().trim() !== '');
    if (btnSave) btnSave.disabled = extractedItems.length === 0 || !hasTipoDoc || !hasTipoPago;
  }

  // NUEVO: ejecutar el reset al cargar la página y al mostrar (bfcache)
  let __resetInvoked = false;
  async function __resetOnce() {
    if (__resetInvoked) return;
    __resetInvoked = true;
    try { await ensureIssuerOptionsLoaded(); } catch (e) {}
    resetAddPolizaView();
  }
  document.addEventListener('DOMContentLoaded', __resetOnce);
  window.addEventListener('pageshow', () => { __resetOnce(); });





  // Autoguardado
  function scheduleAutoSave() {
    if (!AUTO_SAVE_ENABLED) return;
    clearTimeout(autoSaveTimer);
    autoSaveTimer = setTimeout(async () => {
      const selected = Object.assign({}, (window.selectedCliente || {}), {
        subagente: (document.getElementById('subAgenteTop')?.value ||
                    document.getElementById('subAgente')?.value ||
                    (window.selectedCliente || {}).subagente || ''),
        pdf_filename: lastUploadedFilename
      });
      try {
        const r = await fetch('/polizas/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ items: extractedItems, selected })
        });

        const ct = (r.headers.get('content-type') || '').toLowerCase();
        const raw = await r.text();
        let payload;
        try { payload = JSON.parse(raw); } catch (e) { payload = { rawText: raw }; }

        console.log('[save] status:', r.status, 'payload:', payload);

        if (!r.ok || !payload?.ok) {
          const msg = (payload?.errors && Array.isArray(payload.errors) && payload.errors.join('; '))
            || payload?.error
            || payload?.rawText
            || 'Error al guardar pólizas.';
          if (hint) hint.textContent = `Error al guardar: ${msg}`;
          if (window.Swal) Swal.fire({ icon: 'error', title: 'No se guardó', text: msg });
          return;
        }

        if (hint) hint.textContent = `Cambios guardados automáticamente (${payload.count}).`;
      } catch (err) {
        console.error('[autosave] error:', err);
        if (window.Swal) Swal.fire({ icon: 'error', title: 'Error de red', text: String(err) });
      }
    }, 800);
  }

  async function loadAllProducts() {
     if (productsCache) return productsCache;
     try {
       const res = await fetch('/api/maestros/productos?per_page=all');
       const json = await res.json();
       productsCache = (json && json.rows) ? json.rows : (Array.isArray(json) ? json : []);
       return productsCache;
     } catch (e) {
       console.error('loadAllProducts error', e);
       productsCache = [];
       return productsCache;
     }
  }

  function getProductsForRamoSync(products, ramo) {
     if (!ramo) return [];
     const needle = (ramo || '').toString().trim().toLowerCase();
     return (products || []).filter(p => {
       const rn = (p.ramo_nombre || p.ramo || '').toString().trim().toLowerCase();
       const pn = (p.nombre || '').toString().trim().toLowerCase();
       return rn === needle || rn.includes(needle) || pn.includes(needle);
     });
   }

   async function populateProductsForRamo(index, ramo) {
     const td = getTd(index, 'ramos_producto');
     if (!td) return;

     // Preserve current value
     const currentVal = (extractedItems[index] && extractedItems[index].ramos_producto) ? extractedItems[index].ramos_producto : '';

     // If no ramo selected, restore editable cell
     if (!ramo || ramo.toString().trim() === '') {
       td.classList.add('editable');
       td.setAttribute('contenteditable', 'true');
       td.innerText = currentVal || '';
       return;
     }

     try {
       const products = await loadAllProducts();
       const matches = getProductsForRamoSync(products, ramo);
       if (!matches || matches.length === 0) {
         // No hay productos: dejar editable
         td.classList.add('editable');
         td.setAttribute('contenteditable', 'true');
         td.innerText = currentVal || '';
         return;
       }

       // Construir select de productos
       const sel = document.createElement('select');
       sel.className = 'form-select form-select-sm producto-select';
       sel.dataset.index = index;

       const emptyOpt = document.createElement('option');
       emptyOpt.value = '';
       emptyOpt.textContent = 'Selecciona producto...';
       sel.appendChild(emptyOpt);

       matches.forEach(p => {
         const opt = document.createElement('option');
         opt.value = p.nombre || p.id || '';
         opt.textContent = p.nombre || p.id || '';
         // Si el valor actual coincide, marcarlo
         if ((currentVal || '').toString().trim() !== '' && (p.nombre || '').toString().trim() === (currentVal || '').toString().trim()) {
           opt.selected = true;
         }
         sel.appendChild(opt);
       });

       // Autoselección: si no hay valor actual y solo existe un producto para el ramo
       if (!currentVal || currentVal.toString().trim() === '') {
         if (matches.length === 1) {
           sel.value = matches[0].nombre || matches[0].id || '';
           // Reflejar en el modelo y disparar guardado
           if (extractedItems && extractedItems[index]) {
             const txt = matches[0].nombre || matches[0].id || '';
             extractedItems[index].ramos_producto = txt;
           }
           scheduleAutoSave();
         }
       } else {
         // Fallback: si hay valor actual pero no marcó nada por igualdad exacta,
         // intentar seleccionar por coincidencia flexible (case-insensitive, incluye).
         const cur = currentVal.toString().trim().toLowerCase();
         const opts = Array.from(sel.options);
         let picked = null;
         // 1) Igualdad insensible a mayúsculas
         picked = opts.find(o => (o.textContent || '').toString().trim().toLowerCase() === cur);
         // 2) Contiene palabra clave (ej. "salud", "pensión") en el texto del option
         if (!picked && cur) {
           picked = opts.find(o => (o.textContent || '').toString().trim().toLowerCase().includes(cur));
         }
         // 3) Heurística para "Salud" o "Pensión"
         if (!picked && (cur === 'salud' || cur === 'salúd')) {
           picked = opts.find(o => (o.textContent || '').toString().trim().toLowerCase().includes('salud'));
         } else if (!picked && cur.startsWith('pens')) {
           picked = opts.find(o => (o.textContent || '').toString().trim().toLowerCase().includes('pens'));
         }
         if (picked && picked.value !== '') {
           sel.value = picked.value;
           if (extractedItems && extractedItems[index]) {
             const txt = picked.textContent || picked.value || '';
             extractedItems[index].ramos_producto = txt;
           }
           scheduleAutoSave();
         }
       }

       // Reemplazar el contenido de la celda
       td.classList.remove('editable');
       td.removeAttribute('contenteditable');
       td.innerHTML = '';
       td.appendChild(sel);
     } catch (e) {
       console.error('populateProductsForRamo error', e);
       td.classList.add('editable');
       td.setAttribute('contenteditable', 'true');
       td.innerText = currentVal || '';
     }
   }

  // Inicializar selects de productos inmediatamente después de renderizar
  const _orig_render = render;
  // No sobrescribimos render; simplemente después de cada render llamamos a poblar selects
  (function(){
    const originalRender = render;
    render = function(items) {
      originalRender(items);
      try {
        (items || []).forEach((it, idx) => {
          // Si hay ramo en la fila, intentar poblar productos
          const r = (it.ramo || '').toString().trim();
          if (r) populateProductsForRamo(idx, r).then(()=>{}).catch(()=>{});
        });
          } catch (e) { console.error('post-render populate products error', e); }
    };
  })();

  // ─── Modal de Comisiones ────────────────────────────────────────────────────
  (function initComisionesModal() {
    const btnVer       = document.getElementById('btnVerComisiones');
    const modalEl      = document.getElementById('modalComisiones');
    const tbodyEl      = document.getElementById('comModalTbody');
    const searchEl     = document.getElementById('comModalSearch');
    const infoEl       = document.getElementById('comModalInfo');

    if (!btnVer || !modalEl) return;

    let bsModal = null;
    let allRows  = [];   // caché de todas las filas
    let loaded   = false;

    function fmt(v) {
      if (v === null || v === undefined || v === '') return '<span class="text-muted">—</span>';
      const n = parseFloat(v);
      if (!isNaN(n)) return n.toFixed(2);
      return v;
    }

    function renderRows(rows) {
      if (!rows || rows.length === 0) {
        tbodyEl.innerHTML = '<tr><td colspan="14" class="text-center text-muted py-3">Sin resultados</td></tr>';
        if (infoEl) infoEl.textContent = '0 registros';
        return;
      }
      const html = rows.map(c => `
        <tr>
          <td>${c.ramo_nombre  || ''}</td>
          <td>${c.ramo_abreviacion || ''}</td>
          <td>${c.producto     || ''}</td>
          <td>${c.producto_abrev || ''}</td>
          <td>${fmt(c.pos_eps)}</td>
          <td>${fmt(c.pos_vsr)}</td>
          <td>${fmt(c.pos_sr)}</td>
          <td>${fmt(c.pacifico)}</td>
          <td>${fmt(c.sanitas)}</td>
          <td>${fmt(c.protecta)}</td>
          <td>${fmt(c.mapfre)}</td>
          <td>${fmt(c.crecer)}</td>
          <td>${fmt(c.ohio_natural)}</td>
          <td>${fmt(c.factor)}</td>
        </tr>`).join('');
      tbodyEl.innerHTML = html;
      if (infoEl) infoEl.textContent = `${rows.length} registro${rows.length !== 1 ? 's' : ''}`;
    }

    function filterRows(q) {
      if (!q) return allRows;
      const term = q.toLowerCase();
      return allRows.filter(c =>
        (c.ramo_nombre       || '').toLowerCase().includes(term) ||
        (c.ramo_abreviacion  || '').toLowerCase().includes(term) ||
        (c.producto          || '').toLowerCase().includes(term) ||
        (c.producto_abrev    || '').toLowerCase().includes(term)
      );
    }

    async function loadComisiones() {
      tbodyEl.innerHTML = '<tr><td colspan="14" class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm me-2" role="status"></span>Cargando...</td></tr>';
      try {
        const resp = await fetch('/api/comisiones/list');
        const data = await resp.json();
        if (data.ok) {
          allRows = data.rows || [];
          renderRows(allRows);
          loaded = true;
        } else {
          tbodyEl.innerHTML = `<tr><td colspan="14" class="text-center text-danger py-3">Error: ${data.error || 'Error desconocido'}</td></tr>`;
        }
      } catch (e) {
        tbodyEl.innerHTML = `<tr><td colspan="14" class="text-center text-danger py-3">Error de red: ${e.message}</td></tr>`;
      }
    }

    btnVer.addEventListener('click', () => {
      if (!bsModal) {
        bsModal = new bootstrap.Modal(modalEl);
      }
      bsModal.show();
      if (!loaded) loadComisiones();
    });

    // Buscador en tiempo real
    if (searchEl) {
      searchEl.addEventListener('input', () => {
        renderRows(filterRows(searchEl.value.trim()));
      });
    }

    // Limpiar búsqueda al cerrar el modal
    modalEl.addEventListener('hidden.bs.modal', () => {
      if (searchEl) searchEl.value = '';
      if (allRows.length > 0) renderRows(allRows);
    });
  })();
  // ─── Fin Modal de Comisiones ────────────────────────────────────────────────

})();
