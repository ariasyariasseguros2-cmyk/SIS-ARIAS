(function () {
  let __asegLoadPromise = null;

  async function populateAseguradoras() {
    const sel = document.getElementById('companiaSelect');
    if (!sel) return;
    sel.innerHTML = '<option value="">Cargando aseguradoras…</option>';
    try {
      const res = await fetch('/api/aseguradoras', { credentials: 'same-origin' });
      const body = await res.json();
      const rows = body?.rows || [];
      sel.innerHTML = '<option value="">Selecciona…</option>';
      rows.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.slug || (a.nombre_corto || a.nombre || '').toUpperCase();
        opt.textContent = a.nombre_corto || a.nombre || opt.value;
        sel.appendChild(opt);
      });
    } catch (err) {
      console.warn('Error cargando aseguradoras:', err);
      sel.innerHTML = '<option value="">Error al cargar</option>';
    }
  }

  function normalize(str) {
    return (str || '')
      .normalize('NFD')
      .replace(/\p{Diacritic}/gu, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toUpperCase();
  }

  function slugHeuristic(ciaText) {
    const t = normalize(ciaText);
    if (t.includes('MAPFRE')) return 'mapfre';
    if (t.includes('POSITIVA') || t.includes('LPV')) return 'positiva';
    if (t.includes('PACIFICO') || t.includes('PACIFICO')) return 'pacifico';
    if (t.includes('SANITAS')) return 'sanitas';
    if (t.includes('CRECER') && t.includes('VIDA') && t.includes('LEY')) return 'vida-ley-crecer';
    return '';
  }

  function getRenovarModal() {
    const el = document.getElementById('renovarPolizaModal');
    if (!el || !window.bootstrap) return null;
    // Reutiliza instancia si existe; si no, crea una con la misma config
    return bootstrap.Modal.getInstance(el) || new bootstrap.Modal(el, { backdrop: 'static', keyboard: false });
  }

  // Expone la función para abrir el modal con datos (ahora async)
  async function openRenovarPolizaModal(data) {
    try {
      const modalEl = document.getElementById('renovarPolizaModal');
      if (!modalEl || !window.bootstrap) {
        console.warn('[renovar] Bootstrap o modal no disponible');
        return;
      }

      // Asegurar que las aseguradoras están cargadas antes de seleccionar
      if (!__asegLoadPromise) {
        __asegLoadPromise = populateAseguradoras();
      }
      await __asegLoadPromise;

      const m = getRenovarModal();

      // Mapear valores con defaults
      document.getElementById('companiaSelect')?.setAttribute('data-original', data?.compania || data?.cia || '');
      document.getElementById('productoSelect')?.setAttribute('data-original', data?.producto || '');
      document.getElementById('polizaInput')?.setAttribute('data-original', data?.poliza || '');
      document.getElementById('vigFinInput')?.setAttribute('data-original', data?.vig_fin || data?.vig_hasta || '');
      document.getElementById('ramoInput')?.setAttribute('data-original', data?.ramo || '');
      document.getElementById('tipoVigenciaSelect')?.setAttribute('data-original', data?.tipo_vigencia || 'DECLARACION MENSUAL');
      document.getElementById('vigInicioInput')?.setAttribute('data-original', data?.vig_inicio || data?.vig_desde || '');
      document.getElementById('fechaEmisionInput')?.setAttribute('data-original', data?.fecha_emision || '');

      // Escribe valores en los inputs/selects
      const producto = data?.producto || 'SALUD';
      const poliza = data?.poliza || '';
      const vigFin = data?.vig_fin || data?.vig_hasta || '';
      const ramo = data?.ramo || 'SCTR';
      const tipoVig = data?.tipo_vigencia || 'DECLARACION MENSUAL';
      const vigInicio = data?.vig_inicio || data?.vig_desde || '';
      const fechaEmision = data?.fecha_emision || '';

      const compSel = document.getElementById('companiaSelect');
      const prodSel = document.getElementById('productoSelect');
      const polInp = document.getElementById('polizaInput');
      const vigFinInp = document.getElementById('vigFinInput');
      const ramoInp = document.getElementById('ramoInput');
      const tipoVigSel = document.getElementById('tipoVigenciaSelect');
      const vigInicioInp = document.getElementById('vigInicioInput');
      const fechaEmisionInp = document.getElementById('fechaEmisionInput');

      // Selección robusta de compañía (texto exacto, parcial o por slug)
      if (compSel) {
        const ciaRaw = data?.compania || data?.cia || '';
        const ciaN = normalize(ciaRaw);
        let opt = Array.from(compSel.options).find(o => normalize(o.text || o.value) === ciaN);
        if (!opt && ciaN) {
          opt = Array.from(compSel.options).find(o => {
            const t = normalize(o.text || o.value);
            return t.includes(ciaN) || ciaN.includes(t);
          });
        }
        if (!opt) {
          const slug = slugHeuristic(ciaRaw);
          opt = Array.from(compSel.options).find(o => normalize(o.value) === normalize(slug));
        }
        compSel.value = opt ? opt.value : compSel.value;
      }

      if (prodSel) {
        const opt = Array.from(prodSel.options).find(o => normalize(o.text || o.value) === normalize(producto));
        prodSel.value = opt ? opt.value : prodSel.value;
      }
      if (polInp) polInp.value = poliza;
      if (vigFinInp) vigFinInp.value = vigFin;
      if (ramoInp) ramoInp.value = ramo;
      if (tipoVigSel) {
        const opt = Array.from(tipoVigSel.options).find(o => normalize(o.text || o.value) === normalize(tipoVig));
        tipoVigSel.value = opt ? opt.value : tipoVigSel.value;
      }
      if (vigInicioInp) vigInicioInp.value = vigInicio;
      if (fechaEmisionInp) fechaEmisionInp.value = fechaEmision;

      m?.show();
    } catch (e) {
      console.warn('openRenovarPolizaModal error:', e);
    }
  }

  // Exponer en window
  window.openRenovarPolizaModal = openRenovarPolizaModal;

  document.addEventListener('DOMContentLoaded', () => {
    // Cargar aseguradoras al entrar a la página (una sola vez)
    if (!__asegLoadPromise) {
      __asegLoadPromise = populateAseguradoras();
    }

    const table = document.getElementById('polizasTable');
    table?.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;

      const label = btn.textContent.trim().toLowerCase();
      if (!label.includes('renovar')) return;

      const row = btn.closest('tr');
      if (!row) return;

      // Mapeo según el orden de columnas en la tabla
      const pick = (n) => row.querySelector(`td:nth-child(${n})`)?.textContent?.trim() || '';

      const data = {
        contratante: pick(1),
        asegurado: pick(2),
        compania: pick(3),
        ramo: pick(4),
        producto: pick(5),
        poliza: pick(6),
        moneda: pick(7),
        vig_inicio: pick(8),
        vig_fin: pick(9),
        sub_agente: pick(10),
        asegurada: pick(11),
        tipo_vigencia: 'DECLARACION MENSUAL',
        fecha_emision: ''
      };

      openRenovarPolizaModal(data);
    });

    // Limpieza robusta al cerrar el modal
    const modalEl = document.getElementById('renovarPolizaModal');
    modalEl?.addEventListener('hidden.bs.modal', () => {
      // Elimina cualquier backdrop residual
      document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
      // Restaura el body
      document.body.classList.remove('modal-open');
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';
      // Opcional: resetear el formulario para evitar valores stale
      document.getElementById('renovarPolizaForm')?.reset();
    });

    // Si aún no hay envío al backend, cierra al pulsar "Renovar"
    document.getElementById('btnRenovarPoliza')?.addEventListener('click', () => {
      const m = getRenovarModal();
      m?.hide();
    });
  });
})();