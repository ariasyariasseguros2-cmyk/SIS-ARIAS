(() => {
  'use strict';

  const tbody   = document.getElementById('tbodyReporteDiario');
  const cardTotal = document.getElementById('cardTotal');
  const cardPEN   = document.getElementById('cardPEN');
  const cardUSD   = document.getElementById('cardUSD');
  const cardRamos = document.getElementById('cardRamos');
  const fechaHoy  = document.getElementById('fechaHoy');
  const btnRefresh  = document.getElementById('btnRefresh');
  const btnExcel    = document.getElementById('btnExcelDiario');
  const btnPdf      = document.getElementById('btnPdfDiario');

  // Mostrar fecha legible
  const hoy = new Date();
  if (fechaHoy) {
    fechaHoy.textContent = hoy.toLocaleDateString('es-PE', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
  }

  function fmtMoney(val) {
    const n = parseFloat(val) || 0;
    return n.toLocaleString('es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function fmtFecha(val) {
    if (!val) return '–';
    // val puede ser 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:mm:ss'
    return val.substring(0, 10);
  }

  function fmtHora(val) {
    if (!val) return '–';
    // val: 'YYYY-MM-DDTHH:mm:ss' o 'YYYY-MM-DD HH:mm:ss'
    const t = val.replace('T', ' ');
    return t.length >= 19 ? t.substring(11, 19) : t;
  }

  function estadoBadge(estado) {
    const map = {
      'ACTIVO':    'success',
      'PENDIENTE': 'warning',
      'RENOVADA':  'info',
      'VENCIDA':   'secondary',
      'ANULADA':   'danger',
    };
    const color = map[(estado || '').toUpperCase()] || 'secondary';
    return `<span class="badge bg-${color}">${estado || '–'}</span>`;
  }

  function renderRows(rows) {
    if (!rows || rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="14" class="text-center py-5 text-muted">
        <i class="bi-inbox fs-3 d-block mb-2"></i>No hay pólizas registradas hoy.</td></tr>`;
      cardTotal.textContent = '0';
      cardPEN.textContent   = 'S/ 0.00';
      cardUSD.textContent   = '$ 0.00';
      cardRamos.textContent = '0';
      return;
    }

    let sumPEN = 0, sumUSD = 0;
    const ramos = new Set();

    const sorted = [...rows].sort((a, b) => {
      const ia = parseFloat(a.idPoliza) || parseFloat(a.poliza || a.contrato_nro || a.nro) || 0;
      const ib = parseFloat(b.idPoliza) || parseFloat(b.poliza || b.contrato_nro || b.nro) || 0;
      if (ib !== ia) return ib - ia;
      const ta = ((a.creado_en || '') + '').replace('T', ' ');
      const tb = ((b.creado_en || '') + '').replace('T', ' ');
      return tb.localeCompare(ta);
    });

    const html = sorted.map((r, i) => {
      const moneda = (r.moneda || '').toUpperCase();
      const prima  = parseFloat(r.prima_total) || 0;
      const monedaNorm = moneda.replace('.', '').replace('/', '').trim();
      if (['PEN','S','SOLES','SOL'].includes(monedaNorm)) sumPEN += prima;
      else if (['USD','US','DOLARES','DOLAR','$'].includes(monedaNorm)) sumUSD += prima;

      if (r.ramo) ramos.add(r.ramo);

      return `<tr>
        <td class="text-muted small">${i + 1}</td>
        <td><strong>${r.poliza || r.contrato_nro || r.nro || '–'}</strong></td>
        <td><span class="badge bg-light text-dark border">${r.recibo || '–'}</span></td>
        <td>${r.cliente || '–'}</td>
        <td>${r.cia || '–'}</td>
        <td><span class="badge bg-light text-dark border">${r.ramo || '–'}</span></td>
        <td>${r.moneda || '–'}</td>
        <td class="text-end">${r.prima_total != null && r.prima_total !== '' ? fmtMoney(r.prima_total) : '–'}</td>
        <td>${fmtFecha(r.vig_desde)}</td>
        <td>${fmtFecha(r.vig_hasta)}</td>
        <td>${r.ejecutivo || '–'}</td>
        <td>${estadoBadge(r.estado)}</td>
        <td class="small">${r.usuario_registro || '–'}</td>
        <td class="small text-muted">${fmtHora(r.creado_en)}</td>
      </tr>`;
    }).join('');

    tbody.innerHTML = html;
    cardTotal.textContent = rows.length;
    cardPEN.textContent   = 'S/ ' + fmtMoney(sumPEN);
    cardUSD.textContent   = '$ '  + fmtMoney(sumUSD);
    cardRamos.textContent = ramos.size;
  }

  function cargar() {
    tbody.innerHTML = `<tr><td colspan="14" class="text-center py-5 text-muted">
      <div class="spinner-border spinner-border-sm me-2" role="status"></div>Cargando...</td></tr>`;

    fetch('/api/reporte-diario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          renderRows(data.rows);
        } else {
          tbody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-danger">
            <i class="bi-exclamation-triangle me-1"></i>${data.error || 'Error al cargar datos'}</td></tr>`;
        }
      })
      .catch(err => {
        tbody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-danger">
          <i class="bi-exclamation-triangle me-1"></i>Error de conexión</td></tr>`;
        console.error(err);
      });
  }

  function descargar(url, btn, ext) {
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Generando...';

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error('Error al generar el archivo');
        // Intentar leer nombre desde Content-Disposition
        const cd = res.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename[^;=\n]*=["']?([^"';\n]+)["']?/i);
        const today = new Date().toLocaleDateString('es-PE', {
          day: '2-digit', month: '2-digit', year: 'numeric'
        }).replace(/\//g, '-');
        const defaultName = `Reporte Diario ${today}.${ext}`;
        const filename = match ? decodeURIComponent(match[1].trim()) : defaultName;
        return res.blob().then(blob => ({ blob, filename }));
      })
      .then(({ blob, filename }) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(a.href);
      })
      .catch(err => alert('Error: ' + err.message))
      .finally(() => {
        btn.disabled = false;
        btn.innerHTML = orig;
      });
  }

  if (btnRefresh) btnRefresh.addEventListener('click', cargar);
  if (btnExcel)   btnExcel.addEventListener('click', () => descargar('/api/reporte-diario/export/excel', btnExcel, 'xlsx'));
  if (btnPdf)     btnPdf.addEventListener('click',   () => descargar('/api/reporte-diario/export/pdf',   btnPdf,   'pdf'));

  // Carga automática al entrar
  cargar();
})();

