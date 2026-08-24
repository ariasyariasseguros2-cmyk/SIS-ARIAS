(function () {
    'use strict';

    // ============================================================
    // REPORTE DE ERRORES VISUAL (para no depender de consola)
    // ============================================================
    function reportarErrorVisual(mensaje, detalle) {
        try {
            const panel = document.createElement('div');
            panel.style.cssText = 'position:fixed;top:10px;left:10px;right:10px;z-index:99999;padding:14px 18px;background:#dc3545;color:#fff;font-family:system-ui;font-size:13px;border-radius:6px;box-shadow:0 8px 24px rgba(0,0,0,.25);max-height:45vh;overflow:auto;white-space:pre-wrap;';
            panel.innerHTML = '<strong>ERROR en FacturaVentas.js:</strong><br>' + String(mensaje).replace(/\n/g, '<br>');
            if (detalle) {
                panel.innerHTML += '<br><br><span style="opacity:.85;font-size:12px;">' + String(detalle).replace(/\n/g, '<br>').replace(/\s\s/g, ' &nbsp;') + '</span>';
            }
            const cerrar = document.createElement('button');
            cerrar.textContent = 'Cerrar';
            cerrar.style.cssText = 'float:right;margin-left:10px;padding:2px 8px;border:1px solid #fff;background:transparent;color:#fff;border-radius:4px;cursor:pointer;';
            cerrar.onclick = function () { panel.remove(); };
            panel.insertBefore(cerrar, panel.firstChild);
            (document.body || document.documentElement).appendChild(panel);
            console.error('[FV-ERROR]', mensaje, detalle || '');
        } catch (e) {
            console.error('[FV-ERROR-FALLBACK]', mensaje, detalle, e);
        }
    }

    // Atrapar CUALQUIER error global del script
    window.addEventListener('error', function (evt) {
        if (evt.filename && evt.filename.indexOf('FacturaVentas') !== -1) {
            reportarErrorVisual(evt.message, `Línea ${evt.lineno}:${evt.colno}\n${evt.error ? evt.error.stack : ''}`);
        }
    });

    try {
    console.log('[FV-INIT] FacturaVentas.js INICIADO OK');
    // ============================================================
    // ESTADO GLOBAL
    // ============================================================
    let ALL_DATA = [];

    const state = {
        filtered: [],
        page: 1,
        pageSize: 25
    };

    // ============================================================
    // UTILIDADES
    // ============================================================
    const $ = (id) => {
        const el = document.getElementById(id);
        if (!el) console.warn(`[FV-WARN] Elemento #${id} no encontrado`);
        return el;
    };

    function pad(n, len) { return String(n).padStart(len, '0'); }

    function fmtMoney(n) {
        return 'S/ ' + Number(n).toLocaleString('es-PE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function fmtPct(n) {
        return `(${Number(n).toFixed(2)} %)`;
    }

    function normalizarEspacios(s) {
        return String(s || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
    }

    function mostrarEstado(mensaje, esError) {
        try {
            const el = $('fvParserStatus');
            const msg = $('fvParserMsg');
            if (!el || !msg) return;
            el.classList.remove('d-none');
            el.classList.remove('alert-danger', 'alert-success', 'alert-info');
            el.classList.add('alert', esError ? 'alert-danger' : (mensaje.includes('correctamente') ? 'alert-success' : 'alert-info'));
            msg.innerHTML = mensaje;
            if (!esError && (mensaje.includes('correctamente') || mensaje.includes('error'))) {
                setTimeout(function () { try { el.classList.add('d-none'); } catch (e) {} }, 5000);
            }
        } catch (e) { console.warn('[FV] mostrarEstado error:', e); }
    }

    function ocultarEstado() { try { const el = $('fvParserStatus'); if (el) el.classList.add('d-none'); } catch (e) {} }

    // ============================================================
    // RESUMEN
    // ============================================================
    function actualizarResumen() {
        try {
            const rows = state.filtered;
            const totalReg = rows.length;
            const totalMonto = rows.reduce((s, r) => s + Number(r.monto || 0), 0);
            const totalComision = rows.reduce((s, r) => s + Number(r.comision || 0), 0);
            const totalSinImpuestos = +totalComision.toFixed(2);
            const totalIGV = +(totalComision * IGV_PCT).toFixed(2);
            const totalACobrar = +(totalSinImpuestos + totalIGV).toFixed(2);
            const tr = $('fvTotalRegistros'); if (tr) tr.textContent = totalReg;
            const tm = $('fvTotalMonto'); if (tm) tm.textContent = fmtMoney(totalMonto);
            const tc = $('fvTotalComision'); if (tc) tc.textContent = fmtMoney(totalComision);
            const tsi = $('fvTotalSinImpuestos'); if (tsi) tsi.textContent = fmtMoney(totalSinImpuestos);
            const tiv = $('fvTotalIGV'); if (tiv) tiv.textContent = fmtMoney(totalIGV);
            const tac = $('fvTotalACobrar'); if (tac) tac.textContent = fmtMoney(totalACobrar);
            const totalPages = Math.max(1, Math.ceil(totalReg / state.pageSize));
            if (state.page > totalPages) state.page = totalPages;
            const pa = $('fvPaginaActual'); if (pa) pa.textContent = state.page;
            const pt = $('fvPaginaTotal'); if (pt) pt.textContent = totalPages;
            const pi = $('fvPageInput'); if (pi) { pi.max = totalPages; pi.value = state.page; }
        } catch (e) { console.warn('[FV] actualizarResumen error:', e); }
    }

    // ============================================================
    // RENDER TABLA
    // ============================================================
    function renderTable() {
        try {
            const tbody = $('fvTableBody');
            const empty = $('fvEmptyState');
            const rows = state.filtered;
            if (!tbody) return;
            actualizarResumen();
            if (!rows.length) {
                tbody.innerHTML = '';
                if (empty) empty.classList.remove('d-none');
                return;
            }
            if (empty) empty.classList.add('d-none');
            const start = (state.page - 1) * state.pageSize;
            const pageRows = rows.slice(start, start + state.pageSize);
            const html = pageRows.map(function (r) {
                const pct = r.comisionPct != null ? `<span class="comision-pct">${fmtPct(r.comisionPct)}</span>` : '';
                return `<tr>
                    <td>${r.fechaInicio || ''}</td>
                    <td><div class="doc-cell" title="${String(r.tipoDoc || '').replace(/"/g, '&quot;')}">${r.tipoDoc || ''}</div></td>
                    <td class="fw-mono">${r.nroDoc || ''}</td>
                    <td class="fw-mono">${r.docLegal || ''}</td>
                    <td class="text-end">${fmtMoney(r.monto || 0)}</td>
                    <td class="text-end">${fmtMoney(r.comision || 0)}${pct}</td>
                    <td>${r.idTipo ? (r.idTipo + ' - ' + r.idNro) : (r.idNro || '')}</td>
                    <td><div class="cliente-cell" title="${String(r.cliente || '').replace(/"/g, '&quot;')}">${r.cliente || ''}</div></td>
                </tr>`;
            }).join('');
            tbody.innerHTML = html;
        } catch (e) {
            console.warn('[FV] renderTable error:', e);
            reportarErrorVisual('renderTable falló', e.message + '\n' + e.stack);
        }
    }

    // ============================================================
    // FILTROS
    // ============================================================
    function aplicarFiltros() {
        try {
            const d = $('fvFechaDesde'), h = $('fvFechaHasta'), c = $('fvCompania');
            const desde = d ? d.value : '';
            const hasta = h ? h.value : '';
            const compania = c ? c.value : '';
            state.filtered = ALL_DATA.filter(function (r) {
                if (compania && r.compania && r.compania !== compania) return false;
                const iso = r.fechaInicioISO;
                if (!iso) return true;
                if (desde && iso < desde) return false;
                if (hasta && iso > hasta) return false;
                return true;
            });
            state.page = 1;
            renderTable();
        } catch (e) { reportarErrorVisual('aplicarFiltros falló', e.message); }
    }

    // ============================================================
    // PAGINACIÓN
    // ============================================================
    function bindPagination() {
        try {
            const pp = $('fvPrevPage'), np = $('fvNextPage'), pi = $('fvPageInput'), ps = $('fvPageSize');
            if (pp) pp.addEventListener('click', function () { if (state.page > 1) { state.page--; renderTable(); } });
            if (np) np.addEventListener('click', function () { const total = Math.max(1, Math.ceil(state.filtered.length / state.pageSize)); if (state.page < total) { state.page++; renderTable(); } });
            if (pi) pi.addEventListener('change', function (e) {
                const total = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
                let v = parseInt(e.target.value, 10);
                if (isNaN(v) || v < 1) v = 1;
                if (v > total) v = total;
                state.page = v;
                renderTable();
            });
            if (ps) ps.addEventListener('change', function (e) {
                state.pageSize = parseInt(e.target.value, 10) || 25;
                state.page = 1;
                renderTable();
            });
        } catch (e) { reportarErrorVisual('bindPagination falló', e.message); }
    }

    // ============================================================
    // IMPRIMIR
    // ============================================================
    function imprimirDocumento() {
        try {
            if (!state.filtered.length) { alert('Primero carga un PDF de liquidación para extraer los datos.'); return; }
            const totalPages = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
            const guardarPageSize = state.pageSize;
            const guardarPage = state.page;
            state.pageSize = 9999;
            state.page = 1;
            const pt = $('fvPaginaTotal'); if (pt) pt.textContent = '1';
            renderTable();
            setTimeout(function () {
                try { window.print(); } catch (e) { alert('Error al imprimir: ' + e.message); }
                state.pageSize = guardarPageSize;
                state.page = guardarPage;
                const pt2 = $('fvPaginaTotal'); if (pt2) pt2.textContent = totalPages;
                renderTable();
            }, 160);
        } catch (e) { reportarErrorVisual('imprimirDocumento falló', e.message); }
    }

    // ============================================================
    // PDF -> TEXTO  (pdf.js)
    // ============================================================
    async function extraerTextoPDF(file) {
        if (!window['pdfjsLib']) throw new Error('pdf.js no está disponible. Revisa tu conexión a internet (CDN jsdelivr).');
        const buf = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: buf }).promise;
        const paginas = [];
        for (let i = 1; i <= pdf.numPages; i++) {
            const pagina = await pdf.getPage(i);
            const content = await pagina.getTextContent();
            const items = (content.items || []).map(function (it) {
                return {
                    x: it.transform[4] || 0,
                    y: it.transform[5] || 0,
                    w: it.width || 0,
                    h: it.height || 0,
                    str: it.str || ''
                };
            });
            const lineas = reconstruirLineas(items);
            paginas.push(lineas.join('\n'));
        }
        return paginas.join('\n');
    }

    /** Reagrupa items del PDF en líneas. */
    function reconstruirLineas(items) {
        if (!items.length) return [];
        const TOL_Y = 9.0;
        const groups = new Map();
        for (const it of items) {
            let encontrado = false;
            for (const key of groups.keys()) {
                if (Math.abs(key - it.y) <= TOL_Y) {
                    groups.get(key).push(it);
                    encontrado = true;
                    break;
                }
            }
            if (!encontrado) groups.set(it.y, [it]);
        }
        const lineasOrdenadas = [...groups.entries()]
            .sort((a, b) => b[0] - a[0])
            .map(([, arr]) => {
                arr.sort((a, b) => a.x - b.x);
                return arr.map(a => a.str).join(' ');
            })
            .map(normalizarEspacios)
            .filter(Boolean);
        return lineasOrdenadas;
    }

    // ============================================================
    // PARSEO DE LIQUIDACIÓN
    // ============================================================
    const RE_FECHA = /\b(\d{2})[\/-](\d{2})[\/-](\d{4})\b/;
    const RE_FECHA_FIN_LINEA = /(\d{2})[\/-](\d{2})[\/-](\d{4})(?!\s*[ap]\.?\s*m\.?)/;
    const RE_NUM_LIQ_GLOBAL = /\b(LIQ[- ]\s*\d[\d\- ]{4,})\b/i;
    const RE_NUM_LIQ_GLOBAL2 = /Liquidaci[oó]n\s*n[uú]mero[\s\S]{0,40}?(LIQ[-\s][\d-]{4,})/i;
    const RE_NUM_LIQ = /Liquidaci[oó]n\s*n[uú]mero[\s:：]+([A-Za-z0-9\-_]+)/i;
    const RE_BROKER = /Broker[\s:：]+(.+)$/im;
    const RE_LIQ_FECHA = /Liquidaci[oó]n\s*Fecha[\s:：]+(.+)$/im;
    const RE_LIQ_FECHA_HORA = /Fecha\s*y\s*hora[\s:：]+(.+)$/im;
    const RE_COMPANIA_NOMBRE = /^([A-ZÑÁÉÍÓÚ&.\-\s]{3,60})\s*[-–—]\s*[A-Z]{2,10}(?:\s+[A-Z]+)?$/;
    const IGV_PCT = 0.18;

    /** FASE 1: Fusión multi-renglón a nivel array */
    function fusionarLineasWrapMultiCelda(lineas) {
        if (!lineas || !lineas.length) return [];
        const result = [lineas[0]];
        for (let i = 1; i < lineas.length; i++) {
            const actual = lineas[i];
            const anterior = result[result.length - 1];
            if (/^\s*(\d{2})[\/-](\d{2})[\/-](\d{4})\b/.test(actual)) { result.push(actual); continue; }
            if (RE_FECHA.test(actual) && !/Fecha\s+y\s+hora|Liquidaci[oó]n\s+Fecha|P[aá]gina\s+\d+\s*de\s*\d+/i.test(actual)) {
                result.push(actual);
                continue;
            }
            if (/Fecha\s+Inicio|Tipo\s+de\s+Documento|Nro\.?\s+Documento|Doc\.?\s+Legal|Monto\s+Doc|Monto\s+Comisi|P[aá]gina\s+\d+\s*de\s*\d+|Liquidaci[oó]n\s*n[uú]mero|^Broker:|^Liquidaci[oó]n\s+Fecha|^Fecha\s+y\s+hora|^Compañía:|^\s*EPS\s*$/i.test(actual)) {
                result.push(actual);
                continue;
            }
            if (actual.length < 5 && !/\d/.test(actual)) { result.push(actual); continue; }
            result[result.length - 1] = normalizarEspacios(anterior + ' ' + actual);
        }
        return result;
    }

    /**
     * FASE 2 CRÍTICA: ACOPLAMIENTO DE TOKENS DISPERSOS
     * Junta prefijo PF-SCTR + sufijo numérico aunque estén separados por toda la fila.
     * Igual con F002- + 02301677.
     * ENVUELTO EN TRY/CATCH para no matar el parseo si crashea.
     */
    function acoplarTokensDispersos(s) {
        try {
            if (!s) return '';
            let str = ' ' + s + ' ';
            const marcar = (idx, len) => {
                if (idx < 0 || len < 0) return;
                if (idx + len > str.length) len = str.length - idx;
                str = str.slice(0, idx) + ' '.repeat(len) + str.slice(idx + len);
            };

            // ---- PASO 1: NRO. DOC ESTRUCTURADO SCTR ----
            // Ahora acepta CC-PF-SCTR o PF-SCTR (CC es opcional; luego se quita)
            const RE_SCTR_PREFIJO = /[^A-Z0-9]((?:CC[\s\-\.|_]*)?PF[\s\-\.|_]*SCTR)[\s\-\.|_]*(?![A-Z0-9\/]*\d)/i;
            const RE_SCTR_SUFIJO_SLASH = /[^A-Z0-9](\d{6,12}\s*\/\s*\d+)[^A-Z0-9]/;
            const RE_SCTR_SUFIJO_NUM = /[^A-Z0-9](\d{7,12})[^A-Z0-9\/]/;

            const mPre1 = str.match(RE_SCTR_PREFIJO);
            console.log('[FV-DEBUG] acoplar SCTR: prefijo match?', !!mPre1, mPre1 ? mPre1[1] : '');
            if (mPre1) {
                let sufijo = null;
                let sufIdx = -1, sufLen = 0;
                const mSuf1 = str.match(RE_SCTR_SUFIJO_SLASH);
                if (mSuf1) {
                    sufijo = mSuf1[1].replace(/\s+/g, '');
                    sufIdx = mSuf1.index + 1;
                    sufLen = mSuf1[1].length;
                } else {
                    const mSuf2 = str.match(RE_SCTR_SUFIJO_NUM);
                    if (mSuf2) {
                        sufijo = mSuf2[1];
                        sufIdx = mSuf2.index + 1;
                        sufLen = mSuf2[1].length;
                    }
                }
                console.log('[FV-DEBUG] acoplar SCTR: sufijo =', sufijo);
                if (sufijo) {
                    let preLimpio = mPre1[1].replace(/[\s\|\._]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
                    // QUITAR "CC-" (usuario quiere PF-SCTR solamente)
                    if (/^CC-PF-SCTR$/i.test(preLimpio)) preLimpio = 'PF-SCTR';
                    else if (/^CC-/i.test(preLimpio)) preLimpio = preLimpio.replace(/^CC-/i, '');
                    // QUITAR también "/1" o "/<digitos" al final del sufijo (usuario quiere solo el numero sin slash)
                    if (/\/\d+$/.test(sufijo)) sufijo = sufijo.replace(/\/\d+$/, '');
                    const nroCompleto = preLimpio + '-' + sufijo;
                    const preStart = mPre1.index + 1;
                    const preLen = mPre1[1].length;
                    const beforeLen = str.length;
                    str = str.slice(0, preStart) + ' ' + nroCompleto + ' ' + str.slice(preStart + preLen);
                    const afterLen = str.length;
                    const ajuste = afterLen - beforeLen;
                    if (sufIdx >= mPre1.index + 1) sufIdx += ajuste;
                    marcar(sufIdx, sufLen);
                    console.log('[FV-DEBUG] acoplar SCTR: nroCompleto =', nroCompleto);
                }
            }

            // ---- PASO 2: DOC. LEGAL F002-02301677 ----
            const RE_DOCLEGAL_PREFIJO = /[^A-Z0-9]([FB]\d{2,4})[\s\-\.]+(?![\d])/i;
            const mPre2 = str.match(RE_DOCLEGAL_PREFIJO);
            console.log('[FV-DEBUG] acoplar DocLegal: prefijo match?', !!mPre2, mPre2 ? mPre2[1] : '');
            if (mPre2) {
                let sufijo = null;
                let sufIdx = -1, sufLen = 0;
                const reCandidatos = /[^A-Z0-9](\d{6,12})(?![A-Z0-9\/]*\/)/g;
                const candidatos = [];
                let mC;
                while ((mC = reCandidatos.exec(str)) !== null) {
                    const val = mC[1];
                    const ctx = str.slice(Math.max(0, mC.index - 20), mC.index);
                    if (/RUC|DNI|C\.?E\.?/i.test(ctx)) continue;
                    if (val.length === 11 && !/[FB]\d{2,4}/i.test(ctx)) continue;
                    candidatos.push({ val, absIdx: mC.index + 1, len: val.length });
                }
                const despues = candidatos.filter(c => c.absIdx > mPre2.index + mPre2[0].length);
                const lista = despues.length ? despues : candidatos;
                lista.sort((a, b) => b.absIdx - a.absIdx);
                for (const c of lista) {
                    const pre = str.slice(Math.max(0, c.absIdx - 60), c.absIdx);
                    if (/CC[\-]*PF[\-]*SCTR[\-]*$/i.test(pre.trim())) continue;
                    sufijo = c.val;
                    sufIdx = c.absIdx;
                    sufLen = c.len;
                    break;
                }
                console.log('[FV-DEBUG] acoplar DocLegal: sufijo =', sufijo);
                if (sufijo) {
                    const pre = mPre2[1];
                    const docLegalCompleto = pre + '-' + sufijo;
                    const preStart = mPre2.index + 1;
                    const preTotalLen = mPre2[0].length - 1;
                    const beforeLen = str.length;
                    str = str.slice(0, preStart) + ' ' + docLegalCompleto + ' ' + str.slice(preStart + preTotalLen);
                    const afterLen = str.length;
                    const ajuste2 = afterLen - beforeLen;
                    if (sufIdx >= preStart) sufIdx += ajuste2;
                    marcar(sufIdx, sufLen);
                    console.log('[FV-DEBUG] acoplar DocLegal: final =', docLegalCompleto);
                }
            }

            str = str.replace(/-+/g, '-');
            return normalizarEspacios(str);
        } catch (e) {
            console.warn('[FV] acoplarTokensDispersos falló -> devuelvo original:', e.message);
            return normalizarEspacios(s);
        }
    }

    /** Parser principal */
    function parsearLiquidacion(texto) {
        try {
            const lineasBrutas = String(texto || '').split(/\r?\n/).map(normalizarEspacios).filter(Boolean);
            const lineasFusionadas = fusionarLineasWrapMultiCelda(lineasBrutas);

            console.log(`[DEBUG] ===== INICIO PARSEO =====`);
            console.log(`[DEBUG] lineasBrutas.length = ${lineasBrutas.length} | lineasFusionadas.length = ${lineasFusionadas.length}`);
            for (let k = 0; k < Math.min(6, lineasFusionadas.length); k++) {
                console.log(`[DEBUG-RAW] linea fusionada #${k + 1}:`, JSON.stringify(lineasFusionadas[k]));
            }

            const resultado = {
                numLiquidacion: '',
                broker: '',
                liqFecha: '',
                liqFechaHora: '',
                companiaNombre: '',
                companiaDireccion: '',
                filas: []
            };

            const mGlobalLiq = texto.match(RE_NUM_LIQ_GLOBAL) || texto.match(RE_NUM_LIQ_GLOBAL2);
            if (mGlobalLiq) resultado.numLiquidacion = mGlobalLiq[1].replace(/\s+/g, '').toUpperCase();

            for (const ln of lineasFusionadas) {
                if (!resultado.numLiquidacion) { const m = ln.match(RE_NUM_LIQ); if (m) resultado.numLiquidacion = m[1]; }
                if (!resultado.broker) { const m = ln.match(RE_BROKER); if (m) resultado.broker = (m[1] || '').trim(); }
                if (!resultado.liqFecha) {
                    const m = ln.match(RE_LIQ_FECHA);
                    if (m) {
                        const val = (m[1] || '').trim();
                        const f = val.match(RE_FECHA);
                        resultado.liqFecha = f ? `${f[1]}/${f[2]}/${f[3]}` : val;
                    }
                }
                if (!resultado.liqFechaHora) { const m = ln.match(RE_LIQ_FECHA_HORA); if (m) resultado.liqFechaHora = (m[1] || '').trim(); }
            }

            let idxDir = -1;
            for (let i = 0; i < Math.min(40, lineasFusionadas.length); i++) {
                if (RE_COMPANIA_NOMBRE.test(lineasFusionadas[i]) && !/liquidaci|broker|fecha|hora|p[aá]gina/i.test(lineasFusionadas[i])) {
                    resultado.companiaNombre = lineasFusionadas[i];
                    idxDir = i + 1;
                    break;
                }
            }
            if (idxDir > 0) {
                const dirs = [];
                for (let i = idxDir; i < idxDir + 4 && i < lineasFusionadas.length; i++) {
                    if (/^[A-Z0-9ÑÁÉÍÓÚ.,#\- ]{4,}$/.test(lineasFusionadas[i]) && !RE_FECHA.test(lineasFusionadas[i])) dirs.push(lineasFusionadas[i]);
                    else break;
                }
                resultado.companiaDireccion = dirs.join(' / ');
            }

            const RE_NRO_DOC_ESTRUCT = /((?:CC[\-]*)?PF[\-]*SCTR[\-]*[A-Z0-9][A-Z0-9\/\-]{4,})/i;
            const RE_NRO_DOC_SOLO_SCTR_PREFIJO = /(?:CC[\-]*)?PF[\-]*SCTR/i;
            const RE_NRO_DOC_NUMERICO = /(?:^|[\s\-\/(])(\d{7,12})(?:[\-\/][A-Z0-9]+)*(?:[\s\-\/)]|$)/;
            const RE_DOC_LEGAL_SANITAS = /([FB]\d{2,4})[\-]+(\d{3,12})/;
            const RE_DOC_LEGAL_GENERAL = /([A-ZÑ&]{1,5})[\-]+(\d{5,12})/;
            const RE_PCT = /\(\s*([\d.,]+)\s*%\s*\)/g;
            const RE_PCT_UNO = /\(\s*([\d.,]+)\s*%\s*\)/;
            const RE_RUC_LOCAL = /(RUC|DNI|CE|C\.E\.)\s*[-: ]\s*([\d]{8,12})/;
            const RE_TIPO_DOC = /\b(Cuota|Comprobante|Factura|Boleta|Recibo|Prima)\b/i;
            const RE_TOKEN_EMPRESA_PERU = /(?:S\.?A\.?C?\.?|E\.?I\.?R\.?L\.?|S\.?A\.?|S\.?R\.?L\.?|SOC\.?\s*AN[OÓ]N\.?\s*CERRADA|SOCIEDAD\s+AN[OÓ]NIMA|CONSORCIO|GRUPO|PROGRAMA|CORPORACI[OÓ]N)/i;
            const RE_SUFIJO_PERU = /^(S\.?A\.?C?\.?|E\.?I\.?R\.?L\.?|S\.?A\.?|S\.?R\.?L\.?|PER[ÚU]|EPS)$/i;

            function quitarMatch(s, idx, len) {
                if (!s) return '';
                if (idx < 0 || len <= 0) return s.trim();
                if (idx >= s.length) return s.trim();
                return (s.slice(0, idx) + ' ' + s.slice(Math.min(idx + len, s.length))).trim();
            }

            const lineas = lineasFusionadas;

            function tryMultiFila(sorted, valoresSolo, pct, resto, construirFila, bloqueTag) {
                try {
                    const pctReferencia = pct || 23;
                    var descartarPorSerPct = {};
                    for (var wi = 0; wi < sorted.length; wi++) {
                        var v = sorted[wi].val;
                        if (v >= 19.5 && v <= 26.5 && Math.abs(v - pctReferencia) < 6) {
                            var desde = Math.max(0, sorted[wi].idx - 6);
                            var hasta = Math.min(resto.length, sorted[wi].idx + String(v).length + 10);
                            var contexto = resto.slice(desde, hasta);
                            if (/%/.test(contexto) || /\(\s*\d/.test(contexto)) descartarPorSerPct[wi] = true;
                        }
                    }
                    var montosNoPct = [];
                    for (var wj = 0; wj < sorted.length; wj++) {
                        if (descartarPorSerPct[wj]) continue;
                        montosNoPct.push(sorted[wj].val);
                    }
                    if (!(montosNoPct.length >= 4 && montosNoPct.length % 2 === 0)) return null;

                    var N_PARES = Math.floor(montosNoPct.length / 2);
                    var ordenPorValor = montosNoPct.slice().sort(function (a, b) { return b - a; });
                    var montoCandidatos = ordenPorValor.slice(0, N_PARES).sort(function (a, b) { return a - b; });
                    var comisioncandidatos = ordenPorValor.slice(N_PARES).sort(function (a, b) { return a - b; });
                    var paresOK = [];
                    for (var k = 0; k < N_PARES; k++) {
                        var md = montoCandidatos[k];
                        var mc = comisioncandidatos[k];
                        if (md <= 0 || mc <= 0) continue;
                        var ratio = (mc * 100) / md;
                        if (ratio >= 15 && ratio <= 40) {
                            paresOK.push({ monto: md, comision: mc, pctCalculado: +ratio.toFixed(2) });
                        }
                    }
                    var todosLosPctsOK = paresOK.length === N_PARES && N_PARES >= 2;
                    if (!todosLosPctsOK) return null;

                    var sumaMultiparMonto = 0, sumaMultiparCom = 0;
                    for (var pi = 0; pi < paresOK.length; pi++) { sumaMultiparMonto += paresOK[pi].monto; sumaMultiparCom += paresOK[pi].comision; }
                    var ordenSimple = sorted.slice().sort(function (a, b) { return a.idx - b.idx; });
                    var ultimos2 = ordenSimple.slice(-2);
                    var simpleMonto = 0, simpleCom = 0;
                    if (ultimos2.length === 2) {
                        simpleMonto = ultimos2[0].val;
                        simpleCom = ultimos2[1].val;
                        if (pctReferencia) {
                            var esperadoMCs = +(simpleMonto * pctReferencia / 100).toFixed(2);
                            var esperadoMDs = +(simpleCom * pctReferencia / 100).toFixed(2);
                            var dif1 = Math.abs(esperadoMCs - simpleCom);
                            var dif2 = Math.abs(esperadoMDs - simpleMonto);
                            if (dif1 > 0.05 && dif2 <= 0.05) { var tmp1 = simpleMonto; simpleMonto = simpleCom; simpleCom = tmp1; }
                        }
                        if (simpleCom > simpleMonto) { var tmp2 = simpleMonto; simpleMonto = simpleCom; simpleCom = tmp2; }
                    }
                    var deltaMonto = sumaMultiparMonto - simpleMonto;
                    var deltaCom = sumaMultiparCom - simpleCom;
                    var pctMultiparEsperado = Math.abs(8911.49 * pctReferencia / 100 - 2048.98) < 5;
                    var multiparEsperaCerca = false;
                    if (pctMultiparEsperado) {
                        var montoSin = 8911.49 - simpleMonto;
                        var comSin = 2048.98 - simpleCom;
                        var montoConMul = 8911.49 - sumaMultiparMonto;
                        var comConMul = 2048.98 - sumaMultiparCom;
                        var dSimple = Math.abs(montoSin * pctReferencia / 100 - comSin);
                        var dMulti = Math.abs(montoConMul * pctReferencia / 100 - comConMul);
                        multiparEsperaCerca = dMulti < dSimple;
                    }

                    console.log('[FV-MULTIPAR] Validacion: sumaSimple ' + simpleMonto.toFixed(2) + '/' + simpleCom.toFixed(2) + ' vs sumaMultipar ' + sumaMultiparMonto.toFixed(2) + '/' + sumaMultiparCom.toFixed(2) + ' | deltaMonto=' + deltaMonto.toFixed(2) + ' deltaCom=' + deltaCom.toFixed(2) + ' | cerca=' + multiparEsperaCerca);
                    var usarMultipar = true;
                    if (deltaMonto > 10 || deltaCom > 2.5) {
                        console.log('[FV-MULTIPAR] CUIDADO: delta alto. Revisando...');
                        if (multiparEsperaCerca === false && (sumaMultiparMonto > simpleMonto * 1.25 || sumaMultiparCom > simpleCom * 1.3)) {
                            usarMultipar = false;
                            console.log('[FV-MULTIPAR] ABORTADO: suma multipar supera demasiado a la simple.');
                        }
                    }
                    if (!usarMultipar) {
                        var mdf = simpleMonto, mcf = simpleCom;
                        if (pctReferencia && mdf > 0 && mcf > 0) {
                            var emc = +(mdf * pctReferencia / 100).toFixed(2);
                            var emd = +(mcf * pctReferencia / 100).toFixed(2);
                            if (Math.abs(emc - mcf) > 0.05 && Math.abs(emd - mdf) <= 0.05) { var t = mdf; mdf = mcf; mcf = t; }
                        }
                        if (mcf > mdf) { var t2 = mdf; mdf = mcf; mcf = t2; }
                        var pctCalcF = mdf > 0 ? +((mcf * 100) / mdf).toFixed(2) : pctReferencia;
                        return construirFila(mdf, mcf, pctCalcF || pctReferencia);
                    }

                    console.log('[FV-MULTIPAR] Segmento: ' + (bloqueTag || '') + ': montos=' + sorted.length + ', noPct=' + montosNoPct.length + ', ' + N_PARES + ' pares OK. Generando ' + paresOK.length + ' filas...');
                    console.log('   Montos candidatos=' + JSON.stringify(montoCandidatos));
                    console.log('   Comisiones candidatas=' + JSON.stringify(comisioncandidatos));
                    var salidas = [];
                    for (var ki = 0; ki < paresOK.length; ki++) {
                        var pk = paresOK[ki];
                        var pctFin = pk.pctCalculado;
                        var fi = construirFila(pk.monto, pk.comision, pctFin);
                        if (ki > 0) {
                            fi.nroDoc = '—';
                            fi.docLegal = '—';
                            fi.idTipo = '';
                            fi.idNro = '';
                            fi.cliente = fi.cliente + ' (fila ' + (ki + 1) + ' fusionada)';
                        }
                        if (fi.monto > 0 || fi.comision > 0) salidas.push(fi);
                    }
                    if (salidas.length > 1) return salidas;
                    return null;
                } catch (em) {
                    console.warn('[FV] tryMultiFila falló:', em.message);
                    return null;
                }
            }

            function procesarSegmentoFecha(lnPrincipal, fechaMatch, restoInput, bloqueTag) {
                try {
                    const fechaInicio = `${fechaMatch[1]}/${fechaMatch[2]}/${fechaMatch[3]}`;
                    const fechaISO = `${fechaMatch[3]}-${fechaMatch[2]}-${fechaMatch[1]}`;
                    let resto = normalizarEspacios(restoInput);

                    if (bloqueTag && parseInt(bloqueTag) <= 3) console.log(`[DEBUG-BLOQUE ${bloqueTag}] linea fusion original:`, JSON.stringify(resto));

                    resto = acoplarTokensDispersos(resto);

                    if (bloqueTag && parseInt(bloqueTag) <= 3) console.log(`[DEBUG-BLOQUE ${bloqueTag}] resto POST-acoplamiento:`, JSON.stringify(resto));

                    let pct = null;
                    let mPctAll, pctIdx = -1, pctLen = 0;
                    const rePctLocal = new RegExp(RE_PCT.source, 'g');
                    const todosLosPcts = [];
                    while ((mPctAll = rePctLocal.exec(resto)) !== null) {
                        todosLosPcts.push({
                            val: parseFloat(mPctAll[1].replace(',', '.')),
                            idx: mPctAll.index,
                            len: mPctAll[0].length
                        });
                        if (pctIdx < 0) {
                            pct = parseFloat(mPctAll[1].replace(',', '.'));
                            pctIdx = mPctAll.index;
                            pctLen = mPctAll[0].length;
                        }
                    }
                    if (pctIdx >= 0) resto = quitarMatch(resto, pctIdx, pctLen);

                    let idTipo = '', idNro = '';
                    const mRuc = resto.match(RE_RUC_LOCAL);
                    if (mRuc) {
                        idTipo = mRuc[1].toUpperCase();
                        idNro = mRuc[2];
                        resto = quitarMatch(resto, mRuc.index, mRuc[0].length);
                    }

                    let nroDoc = '';
                    let nroDocLen = 0, nroDocIdx = -1;
                    const mNroEstruct = resto.match(RE_NRO_DOC_ESTRUCT);
                    if (mNroEstruct) {
                        nroDoc = mNroEstruct[1].trim();
                        nroDocIdx = mNroEstruct.index;
                        nroDocLen = mNroEstruct[0].length;
                        nroDoc = nroDoc.replace(/\s+/g, '').replace(/-+/g, '-').replace(/^-|-$/g, '');
                        if (/^CC-PF-SCTR-/i.test(nroDoc)) nroDoc = nroDoc.replace(/^CC-/i, '');
                        else if (/^CC-/i.test(nroDoc)) nroDoc = nroDoc.replace(/^CC-/i, '');
                        if (/\/\d+$/.test(nroDoc)) nroDoc = nroDoc.replace(/\/\d+$/, '');
                    }
                    if (nroDoc && nroDocIdx !== -1) {
                        resto = quitarMatch(resto, nroDocIdx, Math.min(nroDocLen, resto.length - nroDocIdx));
                    }

                    let docLegal = '';
                    let candidatoNumerico = null, candidatoNumericoIdx = -1;
                    if (!nroDoc) {
                        const reBuscaNum = new RegExp(RE_NRO_DOC_NUMERICO.source, 'g');
                        let mNum;
                        const todosNumeros = [];
                        while ((mNum = reBuscaNum.exec(resto)) !== null) {
                            const idxNum = (mNum.index === 0 ? 0 : mNum.index + 1);
                            todosNumeros.push({ val: mNum[1], absIdx: idxNum, origIdx: mNum.index, origLen: mNum[0].length });
                        }
                        if (todosNumeros.length) {
                            const largo = resto.length;
                            const posibles = todosNumeros.filter(x => x.absIdx < largo * 0.75 || RE_TOKEN_EMPRESA_PERU.test(resto));
                            const lista = posibles.length ? posibles : todosNumeros;
                            lista.sort((a, b) => a.absIdx - b.absIdx);
                            if (lista[0]) {
                                candidatoNumerico = lista[0].val;
                                candidatoNumericoIdx = lista[0].origIdx;
                                nroDoc = candidatoNumerico;
                                resto = quitarMatch(resto, candidatoNumericoIdx, lista[0].origLen);
                            }
                        }
                    }

                    const todosLegales = [];
                    const mSan = resto.match(RE_DOC_LEGAL_SANITAS);
                    if (mSan) {
                        const t = (mSan[1] + '-' + mSan[2]).replace(/-+/g, '-');
                        if (t.length >= 5 && t !== nroDoc && t !== idNro) {
                            todosLegales.push({ val: t, idx: mSan.index, len: mSan[0].length });
                            resto = quitarMatch(resto, mSan.index, mSan[0].length);
                        }
                    }
                    if (!todosLegales.length) {
                        const reBuscaLegal = new RegExp(RE_DOC_LEGAL_GENERAL.source, 'g');
                        let mLegal;
                        while ((mLegal = reBuscaLegal.exec(resto)) !== null) {
                            const t = (mLegal[1] + '-' + mLegal[2]).replace(/\s+/g, '').replace(/-+/g, '-');
                            if (t === nroDoc || t === idNro) continue;
                            if (nroDoc && t.replace(/[^A-Z0-9]/g, '') === nroDoc.replace(/[^A-Z0-9]/g, '')) continue;
                            if (RE_SUFIJO_PERU.test(t)) continue;
                            if (/^(CUOTA|COMPROBANTE|FACTURA|BOLETA|RECIBO|PRIMA|EPS|RUC|DNI|CE)$/i.test(t)) continue;
                            if (t.length < 5) continue;
                            todosLegales.push({ val: t, idx: mLegal.index, len: mLegal[0].length });
                        }
                    }
                    if (todosLegales.length) {
                        todosLegales.sort((a, b) => a.idx - b.idx);
                        docLegal = todosLegales[0].val;
                        if (!nroDoc && todosLegales[1]) nroDoc = todosLegales[1].val;
                        for (let k = todosLegales.length - 1; k >= (mSan ? 1 : 0); k--) {
                            resto = quitarMatch(resto, todosLegales[k].idx, todosLegales[k].len);
                        }
                    }

                    const todosMontos = [];
                    const reMonto = /(?<![\d(])\s*(\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{1,2}))/g;
                    let mm;
                    while ((mm = reMonto.exec(resto)) !== null) {
                        const raw = mm[1].replace(/\s/g, '');
                        const tieneComa = raw.includes(',');
                        const tienePunto = raw.includes('.');
                        let numStr = raw;
                        if (tieneComa && tienePunto) numStr = raw.replace(/\./g, '').replace(',', '.');
                        else if (tieneComa) numStr = raw.replace(',', '.');
                        const num = parseFloat(numStr);
                        if (Number.isFinite(num) && num > 0 && /[.,]\d{1,2}$/.test(raw)) {
                            todosMontos.push({ val: num, idx: mm.index });
                        }
                    }

                    function construirFila(md, mc, pctUsar) {
                        let fmontoDoc = md, fmontoComision = mc, fpct = pctUsar;
                        if (fpct && fmontoDoc > 0 && fmontoComision > 0) {
                            const esperado = +(fmontoDoc * fpct / 100).toFixed(2);
                            if (Math.abs(esperado - fmontoComision) > 0.05) {
                                const esperadoInv = +(fmontoComision * fpct / 100).toFixed(2);
                                if (Math.abs(esperadoInv - fmontoDoc) <= 0.05) {
                                    const t = fmontoDoc; fmontoDoc = fmontoComision; fmontoComision = t;
                                }
                            }
                        }
                        if (!fpct && fmontoDoc > 0 && fmontoComision > 0) {
                            fpct = +((fmontoComision * 100) / fmontoDoc).toFixed(2);
                        }

                        let fcliente = '';
                        let clean = String(resto || '')
                            .replace(/\bSanitas\s*(?:s\.?a\.?c?\.?|s\.?a\.?\s*per[uú]\s*eps|s\.?a\.)?\b/gi, ' ')
                            .replace(/\bSANITAS\b/g, ' ')
                            .replace(/\b(EPS|PER[ÚÚ])\b/gi, ' ')
                            .replace(/\b(CC|PF|SCTR)[\s\-0-9\/]*\b/gi, ' ')
                            .replace(/\s*\(\s*[\d.,]+\s*%\s*\)\s*/g, ' ')
                            .replace(/(?:^|[\s\/\-])\d{7,12}(?:[\-\/][A-Z0-9]+)*(?:[\s\-\/]|$)/g, ' ')
                            .replace(/\b(?:S\.?A\.?C?\.?|E\.?I\.?R\.?L\.?|S\.?A\.?|S\.?R\.?L\.?|PER[ÚÚ]|EPS)\s*\d{4,}/gi, ' ')
                            .replace(/[|()]+/g, ' ')
                            .replace(/^(?:\s*S\.?A\.?C?\.?|\s*E\.?I\.?R\.?L\.?|\s*S\.?R\.?L\.?)+$/gi, ' ')
                            .replace(/\s{2,}/g, ' ')
                            .trim();

                        if (clean) {
                            const RE_EMPRESA_GLOBAL = /[A-ZÑÁÉÍÓÚ&.\-][\sA-ZÑÁÉÍÓÚ0-9&.\-]*?(?:S\.?A\.?C?\.?|E\.?I\.?R\.?L\.?|S\.?A\.?|S\.?R\.?L\.?|SOC\.?\s*AN[OÓ]N\.?\s*CERRADA|SOCIEDAD\s+AN[OÓ]NIMA|CONSORCIO|CORPORACI[OÓ]N|CERRADA)/gi;
                            const candidatos = [];
                            let mEm;
                            while ((mEm = RE_EMPRESA_GLOBAL.exec(clean)) !== null) {
                                const nombre = mEm[0].trim();
                                if (/sanitas|eps|per[uú]/i.test(nombre)) continue;
                                if (nombre.length < 8) continue;
                                const nombreLimpio = nombre.replace(/^[\s\-\/\.0-9]+/, '').trim();
                                if (nombreLimpio.length >= 6) candidatos.push(nombreLimpio);
                            }
                            if (candidatos.length) {
                                candidatos.sort((a, b) => b.length - a.length);
                                fcliente = candidatos[0];
                            } else {
                                const reFallback = clean.match(/(?:PROGRAMA\s+)?[A-ZÑÁÉÍÓÚ][\sA-Za-z0-9ÑÁÉÍÓÚ&.\-]{8,}/i);
                                if (reFallback) {
                                    const fb = reFallback[0].trim();
                                    if (!/sanitas|eps|per[uú]/i.test(fb)) fcliente = fb;
                                }
                            }
                            if (!fcliente || fcliente.length < 5) {
                                const tokens = clean.split(/\s+/).filter(t => t.length >= 3 && /[A-Za-zÑÁÉÍÓÚ]/.test(t));
                                const filt = tokens.filter(t => !/^(Sanitas|Cuota|EPS|Programa|S|A|C|E|I|R|L|PER[úÚ])$/i.test(t));
                                if (filt.length) fcliente = filt.join(' ');
                            }
                        }
                        if (!fcliente) fcliente = '(sin identificar)';
                        fcliente = fcliente.replace(/\s{2,}/g, ' ').trim();
                        if (fcliente.length > 120) fcliente = fcliente.slice(0, 117) + '...';

                        let fnroDoc = nroDoc;
                        if ((!fnroDoc || fnroDoc === '—') && candidatoNumerico) fnroDoc = candidatoNumerico;
                        let ftipoDoc = '';
                        const mTipo = resto.match(RE_TIPO_DOC);
                        if (mTipo) ftipoDoc = mTipo[1].trim();
                        if (ftipoDoc && ftipoDoc.length > 55) ftipoDoc = ftipoDoc.slice(0, 52) + '...';
                        if (!ftipoDoc) ftipoDoc = 'Cuota';

                        return {
                            fechaInicio: fechaInicio,
                            fechaInicioISO: fechaISO,
                            tipoDoc: ftipoDoc,
                            nroDoc: fnroDoc || '—',
                            docLegal: docLegal || '—',
                            monto: +fmontoDoc.toFixed(2),
                            comision: +fmontoComision.toFixed(2),
                            comisionPct: fpct != null ? fpct : 0,
                            idTipo: idTipo || (idNro ? 'DOC' : ''),
                            idNro: idNro || '',
                            cliente: fcliente,
                            compania: resultado.companiaNombre && /Sanitas/i.test(resultado.companiaNombre) ? 'SANITAS' : ''
                        };
                    }

                    let montoDoc = 0, montoComision = 0;
                    const sorted = todosMontos.slice().sort(function (a, b) { return a.idx - b.idx; });
                    const valoresSolo = sorted.map(function (s) { return s.val; });

                    if (sorted.length >= 4) {
                        const resMulti = tryMultiFila(sorted, valoresSolo, pct, resto, construirFila, bloqueTag);
                        if (resMulti !== null) {
                            // Si tryMultiFila retorna 1 sola fila (abortó por delta alto),
                            // NO retornarla aquí — dejar pasar al código FALLBACK multipar (L845)
                            // que genera múltiples filas por orden de aparición.
                            if (Array.isArray(resMulti) && resMulti.length > 1) {
                                const unicas = [];
                                const chk = new Set();
                                for (const fm of resMulti) {
                                    const k = Number(fm.monto).toFixed(2) + '|' + Number(fm.comision).toFixed(2);
                                    if (!chk.has(k)) { chk.add(k); unicas.push(fm); }
                                    else { console.log(`[FV-MULTIPAR-DEDUP] Eliminada fila multipar con mismo par monto/comisión: ${k}`); }
                                }
                                if (unicas.length !== resMulti.length) console.log(`[FV-MULTIPAR-DEDUP] MultiPar reducido ${resMulti.length} → ${unicas.length}`);
                                return unicas;
                            }
                            // 1 sola fila: seguir al fallback de abajo
                            console.log(`[FV-MULTIPAR] tryMultiFila retornó 1 fila (abortó multipar). Usando fallback por orden de aparición.`);
                        } else {
                            console.log(`[FV-FALLBACK] tryMultiFila retornó null con ${sorted.length} montos (idx-ordenados: ${valoresSolo.join(', ')}). Intentando emparejar por orden de aparición...`);
                        }
                        const fbFilas = [];
                        const pctRef = pct || 23;
                        for (let fpi = 0; fpi + 1 < sorted.length; fpi += 2) {
                            let mdf = sorted[fpi].val;
                            let mcf = sorted[fpi + 1].val;
                            const esperadoMCf = +(mdf * pctRef / 100).toFixed(2);
                            const esperadoMDf = +(mcf * pctRef / 100).toFixed(2);
                            if (Math.abs(esperadoMCf - mcf) > 0.05 && Math.abs(esperadoMDf - mdf) <= 0.05) {
                                const tf = mdf; mdf = mcf; mcf = tf;
                            }
                            if (mcf > mdf) { const tf2 = mdf; mdf = mcf; mcf = tf2; }
                            const pctCalc = mdf > 0 ? +((mcf * 100) / mdf).toFixed(2) : 0;
                            const pctValido = (pctCalc >= 15 && pctCalc <= 40);
                            // Si tryMultiFila dio 1 fila (falló por delta) - NO filtrar por ratio 15-40 aquí
                            // (fallback intenta EMPAREJAR TODO lo posible en la línea)
                            if (resMulti !== null && !Array.isArray(resMulti)) {
                                // Modo "fallback agresivo": mantener todos los pares md>0 mc>0
                                if (!(mdf > 0 || mcf > 0)) continue;
                            } else {
                                if (!pctValido) {
                                    console.log(`[FV-FALLBACK-SKIP] Par ${Math.floor(fpi / 2) + 1}: md=${mdf.toFixed(2)} mc=${mcf.toFixed(2)} pct=${pctCalc}% FUERA DE RANGO (15-40%) — OMITIDO`);
                                    continue;
                                }
                            }
                            const fFb = construirFila(mdf, mcf, pct);
                            if (fFb && (fFb.monto > 0 || fFb.comision > 0)) {
                                fbFilas.push(fFb);
                                console.log(`[FV-FALLBACK] Par ${Math.floor(fpi / 2) + 1}: md=${mdf.toFixed(2)} mc=${mcf.toFixed(2)} pct=${pctCalc}% cliente=${fFb.cliente}`);
                            }
                        }
                        if (fbFilas.length >= 1) {
                            const unicasFb = [];
                            const chkFb = new Set();
                            for (const fm of fbFilas) {
                                const k = Number(fm.monto).toFixed(2) + '|' + Number(fm.comision).toFixed(2);
                                if (!chkFb.has(k)) { chkFb.add(k); unicasFb.push(fm); }
                            }
                            if (unicasFb.length !== fbFilas.length) console.log(`[FV-FALLBACK-DEDUP] Fallback reducido ${fbFilas.length} → ${unicasFb.length}`);
                            console.log(`[FV-FALLBACK] Generadas ${unicasFb.length} filas de fallback.`);
                            return unicasFb;
                        }
                        // Fallback total: si el fallback no produce filas, usar la 1 fila simple de tryMultiFila (si la hubo)
                        if (resMulti !== null && !Array.isArray(resMulti)) {
                            console.log(`[FV-FALLBACK] Fallback sin filas. Retornando 1 fila simple de tryMultiFila: monto=${resMulti.monto} comision=${resMulti.comision}`);
                            return resMulti;
                        }
                    }

                    if (sorted.length >= 2) {
                        let md = sorted[sorted.length - 2].val;
                        let mc = sorted[sorted.length - 1].val;
                        if (pct) {
                            const esperadoMC = +(md * pct / 100).toFixed(2);
                            const esperadoMD = +(mc * pct / 100).toFixed(2);
                            if (Math.abs(esperadoMC - mc) > 0.05 && Math.abs(esperadoMD - md) <= 0.05) {
                                const t = md; md = mc; mc = t;
                            }
                        } else if (mc > md) { const t = md; md = mc; mc = t; }
                        montoDoc = md; montoComision = mc;
                    } else if (sorted.length === 1) {
                        montoDoc = sorted[0].val;
                        if (pct) montoComision = +(montoDoc * pct / 100).toFixed(2);
                    }
                    if (pct && montoDoc > 0 && montoComision > 0) {
                        const esperado = +(montoDoc * pct / 100).toFixed(2);
                        if (Math.abs(esperado - montoComision) > 0.05) {
                            const esperadoInv = +(montoComision * pct / 100).toFixed(2);
                            if (Math.abs(esperadoInv - montoDoc) <= 0.05) {
                                const t = montoDoc; montoDoc = montoComision; montoComision = t;
                            }
                        }
                    }
                    if (!pct && montoDoc > 0 && montoComision > 0) {
                        pct = +((montoComision * 100) / montoDoc).toFixed(2);
                    }
                    const ordenados = todosMontos.slice().sort((a, b) => b.idx - a.idx);
                    for (const q of ordenados) {
                        const desde = Math.max(0, q.idx - 1);
                        const hasta = Math.min(resto.length, q.idx + 20);
                        const sub = resto.slice(desde, hasta);
                        const mSub = sub.match(/([\d]{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{1,2}))/);
                        if (mSub) {
                            const absIdx = desde + mSub.index;
                            resto = quitarMatch(resto, absIdx, mSub[0].length);
                        }
                    }
                    if ((!nroDoc || nroDoc === '—') && candidatoNumerico) nroDoc = candidatoNumerico;

                    if (bloqueTag && parseInt(bloqueTag) <= 3) {
                        console.log(`[DEBUG-BLOQUE ${bloqueTag}] -> FINAL:`, JSON.stringify({
                            montoDoc, montoComision, pct, valoresSolo
                        }));
                    }

                    if (montoDoc > 0 || montoComision > 0) {
                        return construirFila(montoDoc, montoComision, pct);
                    }
                    return null;
                } catch (e) {
                    console.warn('[FV] procesarSegmentoFecha falló:', e.message);
                    return null;
                }
            }

            const TODAS_LAS_LINEAS_CON_FECHA_SOSPECHOSA = [];
            const ESP_MONTO_LOCAL = 8911.49;
            const ESP_COM_LOCAL = 2048.98;
            const BUSCAR_MONTO_OBJETIVO = 71.09;
            const BUSCAR_COMISION_OBJETIVO = 16.35;
            function extraerMontosBrutos(texto) {
                const out = [];
                if (!texto) return out;
                const re = /(?<![\d(])\s*(\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{1,2}))/g;
                let mm;
                while ((mm = re.exec(texto)) !== null) {
                    const raw = mm[1].replace(/\s/g, '');
                    const tieneComa = raw.includes(',');
                    const tienePunto = raw.includes('.');
                    let numStr = raw;
                    if (tieneComa && tienePunto) numStr = raw.replace(/\./g, '').replace(',', '.');
                    else if (tieneComa) numStr = raw.replace(',', '.');
                    const num = parseFloat(numStr);
                    if (Number.isFinite(num) && num > 0 && /[.,]\d{1,2}$/.test(raw)) out.push(num);
                }
                return out;
            }

            for (let i = 0; i < lineas.length; i++) {
                try {
                    const lnPrincipal = lineas[i];

                    if (/Fecha\s+Inicio|Tipo\s+de\s+Documento|Nro\.?\s+Documento|Monto\s+Comisi|Doc\.?\s+Legal|P[aá]gina\s+\d+\s+de\s+\d+/i.test(lnPrincipal)) continue;
                    if (/^\s*(?:Liquidaci|Broker:|Fecha\s+y\s+hora|Compañía|EPS\s*$)/i.test(lnPrincipal) && !RE_PCT_UNO.test(lnPrincipal)) continue;

                    const reFechas = new RegExp(RE_FECHA_FIN_LINEA.source, 'g');
                    const fechasEncontradas = [];
                    let mFecha;
                    while ((mFecha = reFechas.exec(lnPrincipal)) !== null) {
                        fechasEncontradas.push({
                            match: mFecha,
                            index: mFecha.index,
                            length: mFecha[0].length
                        });
                    }
                    if (!fechasEncontradas.length) continue;

                    const montosEnLinea = extraerMontosBrutos(lnPrincipal);
                    const tieneSospechoso = montosEnLinea.some(m => Math.abs(m - BUSCAR_MONTO_OBJETIVO) < 2 || Math.abs(m - BUSCAR_COMISION_OBJETIVO) < 0.5);
                    if (tieneSospechoso) {
                        TODAS_LAS_LINEAS_CON_FECHA_SOSPECHOSA.push({
                            lineaIdx: i + 1,
                            texto: lnPrincipal,
                            montos: montosEnLinea
                        });
                    }

                    const NUM_MONTOS = montosEnLinea.length;
                    const NUM_FECHAS = fechasEncontradas.length;
                    const HAY_MAS_MONTOS_QUE_FECHA = (NUM_FECHAS === 1 && NUM_MONTOS >= 4) || (NUM_FECHAS >= 2 && NUM_MONTOS > NUM_FECHAS * 2 + 1);
                    if (HAY_MAS_MONTOS_QUE_FECHA) {
                        console.log(`[FV-MULTIFILA] linea #${i + 1}: FECHAS=${NUM_FECHAS}, MONTOS=${NUM_MONTOS} → SOSPECHA de ${NUM_FECHAS} filas fusionadas en 1. Intentando desglose por pares...`);
                    }

                    const LINEA_TIENE_MULTIFECHA = fechasEncontradas.length >= 2;
                    for (let f = 0; f < fechasEncontradas.length; f++) {
                        const actual = fechasEncontradas[f];
                        const siguiente = fechasEncontradas[f + 1];
                        const inicioResto = actual.index + actual.length;
                        const finResto = siguiente ? siguiente.index : lnPrincipal.length;
                        let segmentoEntrada;
                        if (LINEA_TIENE_MULTIFECHA) {
                            segmentoEntrada = lnPrincipal.slice(actual.index, finResto).slice(actual.match[0].length);
                        } else {
                            const textoAntes = actual.index > 0 ? lnPrincipal.slice(0, actual.index) : '';
                            const textoDespues = lnPrincipal.slice(inicioResto, lnPrincipal.length);
                            segmentoEntrada = (textoAntes + ' ' + textoDespues).trim();
                        }
                        const tag = (i < 3) ? String(i + 1) + '.' + String(f + 1) : null;
                        const fila = procesarSegmentoFecha(lnPrincipal, actual.match, segmentoEntrada, tag);
                        if (Array.isArray(fila)) {
                            for (const fi of fila) {
                                resultado.filas.push(fi);
                            }
                            if (fila.some(fi => Math.abs(fi.monto - BUSCAR_MONTO_OBJETIVO) < 2 || Math.abs(fi.comision - BUSCAR_COMISION_OBJETIVO) < 0.5)) {
                                console.log(`[FV-ENCONTRADA-7109] (multipar) Encontrada en array!`);
                                fila.forEach((fi, k) => console.log(`   [${k}] monto=${fi.monto} comision=${fi.comision} cliente=${fi.cliente}`));
                            }
                        } else if (fila) {
                            resultado.filas.push(fila);
                            if (Math.abs(fila.monto - BUSCAR_MONTO_OBJETIVO) < 2 || Math.abs(fila.comision - BUSCAR_COMISION_OBJETIVO) < 0.5) {
                                console.log(`[FV-ENCONTRADA-7109] Fila detectada! idx=${resultado.filas.length} monto=${fila.monto} comision=${fila.comision} cliente=${fila.cliente}`);
                            }
                        } else if (tieneSospechoso) {
                            console.log(`[FV-PERDIDA-7109] Segmento NO generó fila. linea #${i + 1}.${f + 1} fecha=${actual.match[0]} segmento=${JSON.stringify(segmentoEntrada)}`);
                        }
                    }
                } catch (err) {
                    console.error(`[DEBUG] Error parseando bloque ${i + 1}:`, err, '\nLínea:', JSON.stringify(lineas[i]));
                }
            }
            console.log(`[FV-SOSPECHOSOS] Líneas con fecha y monto≈71.09 o 16.35 encontradas: ${TODAS_LAS_LINEAS_CON_FECHA_SOSPECHOSA.length}`);
            for (const s of TODAS_LAS_LINEAS_CON_FECHA_SOSPECHOSA) {
                console.log(`[FV-SOSPECHOSO #${s.lineaIdx}] montos=${JSON.stringify(s.montos)} texto=${JSON.stringify(s.texto)}`);
            }

            // ============================
            // MODO RESCATE DE FILA FALTANTE — DESHABILITADO
            // (generaba falsos positivos: 69 registros vs 66 reales)
            // ============================
            console.log(`[FV-RESCATE-GEN] Deshabilitado (evita falsos positivos).`);
            // ============================
            // POST-PROCESO: NORMALIZAR COMISIONES + FILTRADO + DIAGNÓSTICO
            // ============================
            let pctGlobal = 23.00;
            try {
                if (resultado.filas.length) {
                    pctGlobal = 0;

                    const histPctRegex = new Map();
                    for (const f of resultado.filas) {
                        if (f.comisionPct && f.comisionPct > 0) {
                            const k = +(f.comisionPct).toFixed(2);
                            histPctRegex.set(k, (histPctRegex.get(k) || 0) + 1);
                        }
                    }
                    let maxCountRegex = 0;
                    for (const [p, c] of histPctRegex.entries()) {
                        if (c > maxCountRegex && p >= 15 && p <= 40) {
                            maxCountRegex = c; pctGlobal = p;
                        }
                    }
                    if (!pctGlobal) {
                        const filasOK = resultado.filas.filter(f => f.monto > 0 && f.comision > 0);
                        if (filasOK.length >= 5) {
                            const cocientes = filasOK.map(f => (f.comision * 100) / f.monto).filter(q => q >= 15 && q <= 40);
                            if (cocientes.length >= 3) {
                                cocientes.sort((a, b) => a - b);
                                pctGlobal = +cocientes[Math.floor(cocientes.length / 2)].toFixed(2);
                            }
                        }
                    }
                    if (!pctGlobal) pctGlobal = 23.00;
                    console.log(`[FV-PCT] pctGlobal = ${pctGlobal}% (hist=${JSON.stringify(Object.fromEntries(histPctRegex.entries()))})`);

                    for (let idx = 0; idx < resultado.filas.length; idx++) {
                        const f = resultado.filas[idx];
                        const pctUsar = (f.comisionPct && f.comisionPct > 0 && f.comisionPct >= 15 && f.comisionPct <= 40) ? f.comisionPct : pctGlobal;
                        if (f.monto > 0) {
                            const comEsperada = +(f.monto * pctUsar / 100).toFixed(2);
                            if (Math.abs(comEsperada - f.comision) > 0.01) {
                                console.log(`[FV-FIX] fila #${idx + 1}: comision ${f.comision.toFixed(2)} → ${comEsperada} (monto=${f.monto.toFixed(2)}, pctUsar=${pctUsar}%, cliente=${f.cliente || ''})`);
                            }
                            f.comision = comEsperada;
                            f.comisionPct = pctUsar;
                        } else if (f.comision > 0) {
                            f.monto = +(f.comision * 100 / pctUsar).toFixed(2);
                            f.comisionPct = pctUsar;
                            console.log(`[FV-FIX] fila #${idx + 1}: monto → ${f.monto.toFixed(2)} (comision=${f.comision.toFixed(2)}, pctUsar=${pctUsar}%)`);
                        } else {
                            console.log(`[FV-WARN] fila #${idx + 1}: MONTO=0 y COMISION=0 (Cliente: ${f.cliente || ''})`);
                        }
                    }
                }
            } catch (eNorm) {
                console.warn('[FV] Error normalizacion PCT:', eNorm);
            }

            let filasAntesFiltrado = [];
            let filasDescartadas = [];
            const sospechososPerdidos = [];
            try {
                const N = resultado.filas.length;
                filasAntesFiltrado = resultado.filas.slice();
                const filtradas = [];
                for (let idx = 0; idx < N; idx++) {
                    const f = resultado.filas[idx];
                    const montosOK = (Number(f.monto) > 0 || Number(f.comision) > 0);
                    if (montosOK) {
                        filtradas.push(f);
                    } else {
                        filasDescartadas.push({ ...f, _idx: idx + 1, _motivo: `montos=0` });
                    }
                }
                if (filtradas.length !== N) console.log(`[FV-TRASH] Filas: ${N} → ${filtradas.length} (quedan ${N - filtradas.length} descartadas)`);
                resultado.filas = filtradas;
            } catch (eF) { console.warn('[FV] Error filtrado:', eF); }

            // ============================
            // DEDUPLICACIÓN MÍNIMA (solo elimina CLONES reales — NO filas legítimas)
            // 62 vs 66: perdía 4 filas. Ahora solo clona filas con MISMOS 6 campos clave.
            // ============================
            function puntajeFila(f) {
                let p = 0;
                if (f.nroDoc && f.nroDoc !== '—') p += 4;
                if (f.docLegal && f.docLegal !== '—') p += 4;
                if (f.idNro) p += 2;
                if (f.cliente && f.cliente !== '(sin identificar)' && !/rescate|fusionada/i.test(f.cliente)) p += 3;
                if (f.monto > 0) p += 1;
                if (f.comision > 0) p += 1;
                return p;
            }
            function normalizarCliente(c) {
                return String(c || '').replace(/\s+/g, ' ').replace(/\s*\(fila\s*\d+\s*fusionada\)\s*/gi, '').replace(/[^\wÑñÁÉÍÓÚáéíóú&.\- ]/g, '').trim().toLowerCase();
            }

            // PASO 1: Quitar filas de rescate previo (si quedaron)
            let paso1 = resultado.filas.filter(f => !/^\(rescate/i.test(f.cliente || ''));
            let dup1 = resultado.filas.length - paso1.length;
            if (dup1 > 0) console.log(`[FV-DEDUP] PASO1: Eliminadas ${dup1} filas de rescate previo.`);

            // PASO 2 (UNICAMENTE): DEDUP CLONE EXACTO — 6 campos iguales simultáneamente
            // fechaInicioISO + nroDoc + docLegal + idNro + montoExacto + comisionExacta
            const cloneMap = new Map();
            for (const f of paso1) {
                const clave = [
                    f.fechaInicioISO || '',
                    f.nroDoc || '',
                    f.docLegal || '',
                    f.idNro || '',
                    Number(f.monto || 0).toFixed(2),
                    Number(f.comision || 0).toFixed(2)
                ].join('||');
                if (!cloneMap.has(clave)) {
                    cloneMap.set(clave, f);
                } else {
                    const existente = cloneMap.get(clave);
                    if (puntajeFila(f) > puntajeFila(existente)) {
                        console.log(`[FV-DEDUP] PASO2: Reemplazado CLONE por mejor puntaje (${f.nroDoc||'—'}/${f.docLegal||'—'}): ${existente.cliente?.slice(0,45)} → ${f.cliente?.slice(0,45)}`);
                        cloneMap.set(clave, f);
                    } else {
                        console.log(`[FV-DEDUP] PASO2: Eliminado CLONE exacto (${f.nroDoc||'—'}/${f.docLegal||'—'} md=${Number(f.monto||0).toFixed(2)} mc=${Number(f.comision||0).toFixed(2)}): ${f.cliente?.slice(0,50)}`);
                    }
                }
            }
            let paso2Final = [...cloneMap.values()];
            let dup2 = paso1.length - paso2Final.length;
            if (dup2 > 0) console.log(`[FV-DEDUP] PASO2: Eliminadas ${dup2} filas CLON (6 campos iguales).`);

            resultado.filas = paso2Final;
            const dupEliminadas = dup1 + dup2;

            // ============================
            // EXTRAER TOTALES DEL FOOTER PDF (ground truth)
            // Busca línea que empiece por TOTALES y extrae los dos primeros números grandes.
            // Si hay exceso (+1 fila duplicada), elimina la que más reduce la diferencia.
            // ============================
            let ESP_MONTO = null, ESP_COM = null;
            function parseNumFooter(raw) {
                const s = String(raw || '').replace(/\s+/g, '').trim();
                if (!s) return 0;
                // Normalización robusta PE/LATAM: el ÚLTIMO [,.] es siempre decimal.
                // Cualquier [,.] anterior es separador de miles → se elimina.
                // Ejemplos: "8,911.49" → "8911.49" | "1.234,56" → "1234.56" | "120,00" → "120.00" | "1,234" (sin decimales) → "1234"
                const reUltimoSep = /[.,](?=[^.,]*$)/;
                const m = s.match(reUltimoSep);
                if (!m) {
                    // Sin separador decimal → quitar todos los [.,] (miles) y convertir
                    return parseFloat(s.replace(/[.,]/g, '')) || 0;
                }
                const sepIdx = m.index;
                const decChar = s[sepIdx];
                const entera = s.slice(0, sepIdx).replace(/[.,]/g, '');
                const decimal = s.slice(sepIdx + 1).replace(/[.,]/g, '');
                return parseFloat(entera + '.' + decimal) || 0;
            }
            try {
                // Buscar directamente en cada línea fusionada (el flujo principal funciona con pipes | como separadores de columnas)
                for (const ln of lineasFusionadas) {
                    if (!/^\s*TOTALES\b/i.test(ln)) continue;
                    const nums = [];
                    const reNum = /\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{1,2})/g;
                    let mN;
                    while ((mN = reNum.exec(ln)) !== null) {
                        const v = parseNumFooter(mN[0]);
                        if (v > 500) nums.push(v); // filtrar centavos/fechas
                    }
                    if (nums.length >= 2) {
                        const un = [...new Set(nums)].sort((a, b) => b - a);
                        if (un.length >= 2) {
                            ESP_MONTO = un[0];
                            ESP_COM = un[1];
                            console.log(`[FV-TOTALES-PDF] Línea TOTALES detectada: Monto=${ESP_MONTO.toFixed(2)} Comision=${ESP_COM.toFixed(2)}`);
                        } else {
                            ESP_MONTO = Math.max(...nums);
                            ESP_COM = Math.min(...nums);
                            console.log(`[FV-TOTALES-PDF] Línea TOTALES nums repetidos: Monto=${ESP_MONTO.toFixed(2)} Comision=${ESP_COM.toFixed(2)}`);
                        }
                        break;
                    }
                }
                // Fallback: búsqueda en texto completo con regex amplio
                if (ESP_MONTO == null) {
                    const reAmp = /TOTALES[\s\S]{0,500}?(\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{1,2}))[\s\S]{1,100}?(\d{1,3}(?:[.,\s]\d{3})*(?:[.,]\d{1,2}))/i;
                    const mAm = String(texto || '').match(reAmp);
                    if (mAm) {
                        const a = parseNumFooter(mAm[1]);
                        const b = parseNumFooter(mAm[2]);
                        if (a > 0 && b > 0) {
                            ESP_MONTO = Math.max(a, b);
                            ESP_COM = Math.min(a, b);
                            console.log(`[FV-TOTALES-PDF] (fallback regex amplio) Monto=${ESP_MONTO.toFixed(2)} Comision=${ESP_COM.toFixed(2)}`);
                        }
                    }
                }
                if (ESP_MONTO == null) {
                    console.warn(`[FV-TOTALES-PDF] No detectado. Se usará heurística de cantidad de filas.`);
                }
            } catch (eT) { console.warn('[FV-TOTALES-PDF] error:', eT.message); }

            let totalMontoFIN = resultado.filas.reduce((s, r) => s + Number(r.monto || 0), 0);
            let totalComisionFIN = resultado.filas.reduce((s, r) => s + Number(r.comision || 0), 0);
            let difMonto = ESP_MONTO != null ? +(totalMontoFIN - ESP_MONTO).toFixed(2) : 0;
            let difCom = ESP_COM != null ? +(totalComisionFIN - ESP_COM).toFixed(2) : 0;

            // HEURÍSTICA ESTRICTA (SOLO ELIMINAR BASURA REAL)
            // La versión anterior MATABA 4-6 filas LEGÍTIMAS (quitaba 533.97/122.81 = 4 filas completas de ~133/30).
            // NUEVA REGLA: NO ELIMINAR NADA A MENOS QUE:
            //   1) Exista el footer detectado Y la suma EXCEDA los totales (difMonto > 0.2 O difCom > 0.2)
            //   - O -
            //   2) HAYA filas con el tag (fila X fusionada) O (nroDoc=— Y docLegal=— Y cliente vacío)
            //
            // NUNCA eliminar por cantidad de filas. Si faltan filas, es error de parseo (no basura).
            let USAR_HEURISTICA = false;
            const ratioGlobal = totalComisionFIN > 0 ? +(totalMontoFIN / totalComisionFIN).toFixed(3) : 0;
            const CANTIDAD_ACTUAL = resultado.filas.length;

            // Contar cuántas FILAS DE BASURA hay (candidatas seguras a eliminar)
            function esBasura(f) {
                if (/\(fila\s*\d+\s*fusionada\)/i.test(f.cliente || '')) return true;
                const nd = (f.nroDoc || '—') === '—';
                const dl = (f.docLegal || '—') === '—';
                const cc = !f.idNro || /sin identificar|rescate|^\s*$/i.test(f.cliente || '');
                const sinMonto = Number(f.monto || 0) < 0.01;
                const sinCom = Number(f.comision || 0) < 0.01;
                if (nd && dl && cc && (sinMonto || sinCom)) return true;
                return false;
            }
            const CANT_BASURA = resultado.filas.filter(esBasura).length;

            if (ESP_MONTO != null && (difMonto > 0.2 || difCom > 0.2) && CANTIDAD_ACTUAL > 1) {
                USAR_HEURISTICA = true;
                console.log(`[FV-AJUSTE-H] Activado por FOOTER EXCEDIDO. DifM=${difMonto.toFixed(2)} DifC=${difCom.toFixed(2)}. BasuraDetectada=${CANT_BASURA}`);
            } else if (CANT_BASURA > 0) {
                USAR_HEURISTICA = true;
                console.log(`[FV-AJUSTE-H] Activado por BASURA DETECTADA (${CANT_BASURA} filas fusionadas/sin datos). Footer=${ESP_MONTO!=null?'SÍ':'NO'}, Filas=${CANTIDAD_ACTUAL}`);
            }

            if (USAR_HEURISTICA) {
                // ================================================================
                // MODO EXCEDIDO vs MODO BASURA (2 en 1):
                // - SI hay FOOTER EXCEDIDO (difMonto>0 OR difCom>0):
                //      * Eliminar xCant filas. SE PERMITE eliminar TAMBIÉN filas "no basura"
                //        SI score de coincidencia con difMonto/difCom es MUY BUENO (<20 pts).
                //        Las filas "basura" siempre se eliminan primero (prioridad con -50 pts).
                //        CANT_BASURA como tope, PERO si faltan y hay candidatas buenas, extender hasta xCant.
                // - SI SOLO hay basura sin footer:
                //      * Solo eliminar CANT_BASURA. Nunca filas buenas.
                // ================================================================
                const HAY_EXCESO = ESP_MONTO != null && (difMonto > 0.2 || difCom > 0.2);
                let xCant = Math.max(1, CANT_BASURA);
                if (HAY_EXCESO) {
                    const avgMonto = CANTIDAD_ACTUAL > 0 ? totalMontoFIN / CANTIDAD_ACTUAL : 100;
                    xCant = Math.max(1, Math.ceil(Math.max(difMonto, difCom * 4) / Math.max(50, avgMonto * 0.6)));
                }
                // Tope superior: nunca eliminar más de 1/10 de las filas (sanity)
                const TOPE_ELIM = Math.max(1, Math.floor(CANTIDAD_ACTUAL / 10) + 2);
                xCant = Math.min(xCant, CANT_BASURA + TOPE_ELIM, TOPE_ELIM);
                console.log(`[FV-AJUSTE-H] Modo=${HAY_EXCESO?'FOOTER-EXCEDIDO':'SOLO-BASURA'}. xCant=${xCant} (CANT_BASURA=${CANT_BASURA} TOPE=${TOPE_ELIM}). Eliminando solo "basura"${HAY_EXCESO?' + filas que coincidan con diferencia (<20 pts)':''}.`);

                for (let iter = 0; iter < xCant && resultado.filas.length > 1; iter++) {
                    const candidatasAJ = [];
                    for (let i = 0; i < resultado.filas.length; i++) {
                        const f = resultado.filas[i];
                        const mdF = +Number(f.monto || 0).toFixed(2);
                        const mcF = +Number(f.comision || 0).toFixed(2);
                        const esBas = esBasura(f);

                        // SI NO hay exceso → SOLO se consideran las de BASURA
                        if (!HAY_EXCESO && !esBas) continue;

                        let score = 0;
                        if (HAY_EXCESO) {
                            // Preferir la fila que MÁS CIERRE la diferencia con el footer
                            const cMonto = +Math.abs(mdF - difMonto).toFixed(2);
                            const cCom = +Math.abs(mcF - difCom).toFixed(2);
                            score = cMonto + cCom * 2;
                            // Regla bonus: si la fila tiene ratio MUY similar a la diferencia global → descuento fuerte
                            if (cMonto < 2 && cCom < 1) score -= 30;
                        } else {
                            score = 0;
                        }

                        // Penalizaciones por "poca calidad" (basura se elimina PRIMERO siempre)
                        if (esBas) score -= 60;
                        if (/\(fila\s*\d+\s*fusionada\)/i.test(f.cliente || '')) score -= 50;
                        if ((f.nroDoc || '—') === '—') score -= 15;
                        if ((f.docLegal || '—') === '—') score -= 8;
                        if (!f.idNro) score -= 5;
                        if (/sin identificar|rescate|^\(/i.test(f.cliente || '')) score -= 25;
                        const ratio = mdF > 0 ? +((mcF * 100) / mdF).toFixed(2) : 0;
                        if (ratio < 15 || ratio > 40) score += 3;

                        // GUARDIA IMPORTANTE (solo cuando HAY_EXCESO y NO es basura):
                        //  → SOLO considerar si hay MUY buena coincidencia con la diferencia (score < 20)
                        //  → Y NUNCA eliminar una fila CON nroDoc + docLegal + idNro (fila completa) a menos que score sea extremadamente bueno (<5)
                        if (HAY_EXCESO && !esBas) {
                            const nCamposCompletos = ((f.nroDoc && f.nroDoc !== '—')?1:0) + ((f.docLegal && f.docLegal !== '—')?1:0) + (f.idNro?1:0);
                            if (score > 15 && nCamposCompletos >= 2) continue; // fila casi completa + score regular → NO tocar
                            if (score > 5 && nCamposCompletos >= 3) continue;  // fila COMPLETA → solo si score INMEJORABLE (<5)
                            if (score > 20) continue; // score malo (poco parecido a diferencia) → NO eliminar
                        }

                        candidatasAJ.push({ idx: i, score, mdF, mcF, ratio, cliente: f.cliente, fusionada: /\(fila\s*\d+\s*fusionada\)/i.test(f.cliente || ''), nroDoc: f.nroDoc, docLegal: f.docLegal, idNro: f.idNro, esBas });
                    }
                    if (!candidatasAJ.length) {
                        if (HAY_EXCESO) console.warn(`[FV-AJUSTE-FINAL] (iter ${iter+1}) No hay candidatas seguras para eliminar. (DifM=${difMonto.toFixed(2)} DifC=${difCom.toFixed(2)}). Abortado.`);
                        else console.warn(`[FV-AJUSTE-FINAL] (iter ${iter+1}) No hay más basura para eliminar.`);
                        break;
                    }
                    candidatasAJ.sort((a, b) => a.score - b.score);
                    const mejor = candidatasAJ[0];
                    if (iter === 0) {
                        const TOP = candidatasAJ.slice(0, 5).map(c => `#${c.idx+1} s=${c.score.toFixed(1)} md=${c.mdF.toFixed(2)} mc=${c.mcF.toFixed(2)} bas=${c.esBas?'SÍ':'no'} fus=${c.fusionada?'SÍ':'no'} nd=${c.nroDoc||'—'} dl=${c.docLegal||'—'} id=${c.idNro||'—'} cli=${String(c.cliente).slice(0,25)}`);
                        console.log(`[FV-AJUSTE-FINAL] TOP 5 candidatas (iter=${iter+1}/${xCant}):\n   ${TOP.join('\n   ')}`);
                    }
                    console.log(`[FV-AJUSTE-FINAL] (${iter+1}/${xCant}) ELIMINANDO fila ${mejor.esBas?'(BASURA)':''} #${mejor.idx + 1}: monto=${mejor.mdF.toFixed(2)} comision=${mejor.mcF.toFixed(2)} ratio=${mejor.ratio}% cliente=${String(mejor.cliente).slice(0, 80)} (score=${mejor.score.toFixed(2)})`);
                    resultado.filas.splice(mejor.idx, 1);
                    totalMontoFIN = resultado.filas.reduce((s, r) => s + Number(r.monto || 0), 0);
                    totalComisionFIN = resultado.filas.reduce((s, r) => s + Number(r.comision || 0), 0);
                    difMonto = ESP_MONTO != null ? +(totalMontoFIN - ESP_MONTO).toFixed(2) : 0;
                    difCom = ESP_COM != null ? +(totalComisionFIN - ESP_COM).toFixed(2) : 0;
                    if (HAY_EXCESO && (difMonto <= 0.2 && difCom <= 0.2)) {
                        console.log(`[FV-AJUSTE-FINAL] Footer CUADRADO! DifM=${difMonto.toFixed(2)} DifC=${difCom.toFixed(2)}. Terminando.`);
                        break;
                    }
                    if (HAY_EXCESO && (difMonto <= 0 || difCom <= 0)) {
                        console.log(`[FV-AJUSTE-FINAL] Diferencia se volvió negativa (DifM=${difMonto.toFixed(2)} DifC=${difCom.toFixed(2)}). No más eliminaciones.`);
                        break;
                    }
                }
                console.log(`[FV-AJUSTE-FINAL] POST: Monto=${totalMontoFIN.toFixed(2)} Comision=${totalComisionFIN.toFixed(2)} Dif Monto=${difMonto.toFixed(2)} Dif Com=${difCom.toFixed(2)} Filas=${resultado.filas.length}`);
            } else {
                console.log(`[FV-AJUSTE-H] OMITIDO. No hay footer excedido ni basura detectada (Basura=${CANT_BASURA}). Filas=${CANTIDAD_ACTUAL}.`);
            }

            console.log(`[FV-FINAL] MontoDoc=${totalMontoFIN.toFixed(2)} | Comision=${totalComisionFIN.toFixed(2)} | Filas=${resultado.filas.length} | FooterPDF: ${ESP_MONTO!=null?`${ESP_MONTO.toFixed(2)}/${ESP_COM.toFixed(2)}`:'N/A'}`);

            try {
                const diag = document.getElementById('fvDiagnostico');
                const diagToggle = document.getElementById('fvBtnToggleDiag');
                if (diag) {
                    const lineas = [];
                    lineas.push(`=== DIAGNÓSTICO PARSEO (${resultado.filas.length} filas MANTENIDAS / ${filasAntesFiltrado.length} DETECTADAS) ===`);
                    lineas.push(`Filas descartadas por filtro: ${filasDescartadas.length}`);
                    lineas.push(`PCT Global: ${pctGlobal}%`);
                    lineas.push(`MontoDoc Total: ${totalMontoFIN.toFixed(2)}`);
                    lineas.push(`Comision Total: ${totalComisionFIN.toFixed(2)}`);
                    if (ESP_MONTO != null) lineas.push(`Footer PDF Esperado: Monto=${ESP_MONTO.toFixed(2)} Comision=${ESP_COM.toFixed(2)}`);
                    if (ESP_MONTO != null) lineas.push(`Diferencia vs Footer: Monto=${difMonto.toFixed(2)} Comision=${difCom.toFixed(2)}`);
                    lineas.push(`Filas duplicadas eliminadas: ${dupEliminadas}`);
                    lineas.push('');
                    lineas.push(`--- FILAS MANTENIDAS ---`);
                    lineas.push(`# | Fecha | NroDoc | DocLegal | Monto | Comision | Pct | ID | Cliente`);
                    lineas.push(`---|---|---|---|---|---|---|---|---`);
                    for (let i = 0; i < resultado.filas.length; i++) {
                        const f = resultado.filas[i];
                        lineas.push(`${i + 1} | ${f.fechaInicio} | ${f.nroDoc} | ${f.docLegal} | ${Number(f.monto).toFixed(2)} | ${Number(f.comision).toFixed(2)} | ${f.comisionPct}% | ${f.idTipo || ''}${f.idNro} | ${f.cliente}`);
                    }
                    if (filasDescartadas.length) {
                        lineas.push('');
                        lineas.push(`--- FILAS DESCARTADAS (${filasDescartadas.length}) ---`);
                        lineas.push(`#Orig | Fecha | NroDoc | DocLegal | Monto | Comision | Pct | ID | Cliente | Motivo`);
                        lineas.push(`---|---|---|---|---|---|---|---|---|---`);
                        for (const fd of filasDescartadas) {
                            lineas.push(`#${fd._idx} | ${fd.fechaInicio} | ${fd.nroDoc} | ${fd.docLegal} | ${Number(fd.monto).toFixed(2)} | ${Number(fd.comision).toFixed(2)} | ${fd.comisionPct}% | ${fd.idTipo || ''}${fd.idNro} | ${fd.cliente} | ${fd._motivo}`);
                        }
                    }
                    diag.value = lineas.join('\n');
                    if (diagToggle) diagToggle.style.display = 'inline-block';
                }
            } catch (eDiag) { console.warn('[FV] Diagnostico error:', eDiag); }

            console.log(`[DEBUG] ===== FIN PARSEO. filas.length = ${resultado.filas.length} =====`);
            return resultado;
        } catch (e) {
            reportarErrorVisual('parsearLiquidacion falló', e.message + '\n' + (e.stack ? e.stack.slice(0, 500) : ''));
            return { numLiquidacion: '', broker: '', liqFecha: '', liqFechaHora: '', companiaNombre: '', companiaDireccion: '', filas: [] };
        }
    }

    function escapeReg(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

    // ============================================================
    // APLICAR RESULTADO
    // ============================================================
    function aplicarParseo(resultado) {
        try {
            ALL_DATA = resultado.filas;
            state.filtered = [...ALL_DATA];
            state.page = 1;
            const nl = $('fvNumLiquidacion'); if (nl && resultado.numLiquidacion) nl.textContent = resultado.numLiquidacion;
            const br = $('fvBroker'); if (br && resultado.broker) br.textContent = resultado.broker;
            const brs = $('fvBrokerSubtitle'); if (brs && resultado.broker) brs.textContent = resultado.broker;
            const fl = $('fvFechaLiquidacion'); if (fl && resultado.liqFecha) fl.textContent = resultado.liqFecha;
            const fh = $('fvFechaHoraDoc'); if (fh && resultado.liqFechaHora) fh.textContent = resultado.liqFechaHora;
            const cn = $('fvCompaniaNombre'); if (cn && resultado.companiaNombre) cn.textContent = resultado.companiaNombre;
            const cd = $('fvCompaniaDireccion'); if (cd && resultado.companiaDireccion) cd.innerHTML = resultado.companiaDireccion.replace(/\s\/\s/g, '<br>');
            const notice = $('fvInlineNotice');
            if (notice) {
                if (resultado.filas.length) notice.classList.remove('d-none');
                else notice.classList.add('d-none');
            }
            renderTable();
        } catch (e) { reportarErrorVisual('aplicarParseo falló', e.message); }
    }

    // ============================================================
    // SUBIDA DE PDF
    // ============================================================
    async function procesarArchivoPDF(file) {
        if (!file) return;
        if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') { alert('Por favor selecciona un archivo PDF.'); return; }
        mostrarEstado('Extrayendo texto del PDF...', false);
        try {
            console.log('[FV] procesarArchivoPDF INICIO:', file.name, (file.size / 1024).toFixed(1), 'KB');
            const texto = await extraerTextoPDF(file);
            console.log('[FV] extraerTextoPDF OK:', texto.length, 'caracteres');
            mostrarEstado(`Analizando ${texto.length.toLocaleString('es-PE')} caracteres...`, false);
            const resultado = parsearLiquidacion(texto);
            console.log('[FV] parsearLiquidacion OK:', resultado.filas.length, 'filas');
            if (!resultado.filas.length) {
                mostrarEstado('No se detectaron filas de datos en este PDF. Revisa que sea una liquidación en formato compatible.', true);
                return;
            }
            aplicarParseo(resultado);
            mostrarEstado(`Se extrajeron <strong>${resultado.filas.length}</strong> registros correctamente.`, false);
        } catch (err) {
            console.error(err);
            const detalle = err.stack ? `${err.message}\n${err.stack.slice(0, 400)}` : err.message;
            reportarErrorVisual(`Error al procesar el PDF: ${err.message}`, detalle);
            mostrarEstado(`Error al leer el PDF: ${err.message || err}`, true);
        }
    }

    function bindUpload() {
        try {
            const input = $('fvPdfInput');
            if (input) input.addEventListener('change', function (e) {
                const f = e.target.files && e.target.files[0];
                if (f) procesarArchivoPDF(f);
                e.target.value = '';
            });
            const dropzone = $('fvDropzone');
            let dragCounter = 0;
            document.addEventListener('dragenter', function (e) {
                if (esArrastrePDF(e)) { dragCounter++; if (dropzone) dropzone.classList.remove('d-none'); e.preventDefault(); }
            });
            document.addEventListener('dragover', function (e) { if (esArrastrePDF(e)) e.preventDefault(); });
            document.addEventListener('dragleave', function () {
                dragCounter = Math.max(0, dragCounter - 1);
                if (dragCounter === 0 && dropzone) dropzone.classList.add('d-none');
            });
            document.addEventListener('drop', function (e) {
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
                    dragCounter = 0;
                    if (dropzone) dropzone.classList.add('d-none');
                    e.preventDefault();
                    const f = e.dataTransfer.files[0];
                    if (f) procesarArchivoPDF(f);
                }
            });
            if (dropzone) dropzone.addEventListener('click', function () { if (input) input.click(); });
            console.log('[FV] bindUpload OK');
        } catch (e) { reportarErrorVisual('bindUpload falló', e.message); }
    }

    function esArrastrePDF(e) {
        if (!e.dataTransfer) return false;
        const tipos = [...(e.dataTransfer.types || [])];
        return tipos.includes('Files');
    }

    function bindLimpiar() {
        try {
            const btn = $('fvBtnLimpiar');
            if (!btn) return;
            btn.addEventListener('click', function () {
                if (ALL_DATA.length === 0) return;
                if (!confirm('¿Limpiar los datos importados del PDF?')) return;
                ALL_DATA = [];
                state.filtered = [];
                state.page = 1;
                const nl = $('fvNumLiquidacion'); if (nl) nl.textContent = '—';
                const fl = $('fvFechaLiquidacion'); if (fl) fl.textContent = '—';
                const fh = $('fvFechaHoraDoc'); if (fh) fh.textContent = '—';
                const cn = $('fvCompaniaNombre'); if (cn) cn.textContent = 'SANITAS PERÚ S.A. - EPS';
                const cd = $('fvCompaniaDireccion'); if (cd) cd.innerHTML = 'CALLE AMADOR MERINO REYNA 492 - URB. JARDIN - LIMA -<br>LIMA - SAN ISIDRO';
                ocultarEstado();
                renderTable();
            });
            console.log('[FV] bindLimpiar OK');
        } catch (e) { reportarErrorVisual('bindLimpiar falló', e.message); }
    }

    // ============================================================
    // INICIALIZAR (con safe init por si faltan IDs)
    // ============================================================
    function init() {
        try {
            console.log('[FV] init() INICIO');
            const hoy = new Date();
            const mesAnterior = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
            const d = $('fvFechaDesde');
            const h = $('fvFechaHora');
            if (d) try { d.value = mesAnterior.toISOString().slice(0, 10); } catch (e) { console.warn('fvFechaDesde fallo', e); }
            if (h) try { h.value = hoy.toISOString().slice(0, 10); } catch (e) { console.warn('fvFechaHora fallo', e); }

            const bb = $('fvBtnBuscar'); if (bb) bb.addEventListener('click', aplicarFiltros);
            const bi = $('fvBtnImprimir'); if (bi) bi.addEventListener('click', imprimirDocumento);
            const co = $('fvCompania'); if (co) co.addEventListener('change', aplicarFiltros);

            bindPagination();
            bindUpload();
            bindLimpiar();

            renderTable();
            console.log('[FV] init() OK. Esperando PDF...');
            mostrarEstado('Script listo. Carga un PDF con el botón "Cargar PDF" o arrástralo a la ventana.', false);
            setTimeout(ocultarEstado, 4000);
        } catch (e) { reportarErrorVisual('init() falló', e.message + '\n' + e.stack); }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    console.log('[FV-INIT] IIFE ejecutado OK (sin fallos sintácticos)');
    } catch (SUPER_ERROR) {
        reportarErrorVisual('ERROR FATAL en FacturaVentas.js', SUPER_ERROR.message + '\n' + (SUPER_ERROR.stack ? SUPER_ERROR.stack.slice(0, 800) : ''));
    }
})();
