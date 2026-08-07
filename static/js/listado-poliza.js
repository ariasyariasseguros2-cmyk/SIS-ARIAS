document.addEventListener('DOMContentLoaded', () => {
  // === REFERENCIAS DOM ===
  const globalSearchInput = document.getElementById('polizasSearch');
  const globalSearchBtn = document.getElementById('btnGlobalSearch');
  const searchTabs = document.getElementById('searchTabs');
  const table = document.getElementById('polizasListTable');
  const tbody = document.getElementById('polizasTableBody');
  const paginationBar = document.getElementById('paginationBar');
  const voiceSearchBtn = document.getElementById('btnVoiceSearch');
  const searchModalEl = document.getElementById('searchResultsModal');
  const searchModalBody = document.getElementById('searchResultsBody');
  const applyResultsToTableBtn = document.getElementById('applyResultsToTable');
  
  // URLs base desde atributos data
  // Corrección: Selector actualizado a .table-card
  const cardContainer = document.querySelector('.table-card[data-base-url]');
  const baseUrl = cardContainer?.getAttribute('data-base-url') || window.location.pathname;
  const primasUrlBase = cardContainer?.getAttribute('data-primas-url') || '/menu/primas';
  const cuotasUrlBase = cardContainer?.getAttribute('data-cuotas-url') || '/menu/cuotas';
  const editUrlBase = cardContainer?.getAttribute('data-edit-url') || '/menu/editar-poliza';
  const siniestrosUrlBase = cardContainer?.getAttribute('data-siniestros-url') || '/menu/siniestros-poliza';

  let currentSearchType = 'general';

  const anularModalEl = document.getElementById('anularPolizaModal');
  const anularModalInstance = (anularModalEl && window.bootstrap)
    ? bootstrap.Modal.getOrCreateInstance(anularModalEl, { backdrop: 'static' })
    : null;
  const anularFields = {
    numero: document.getElementById('anularPolizaNumero'),
    asegurado: document.getElementById('anularPolizaAsegurado'),
    vigInicio: document.getElementById('anularPolizaVigInicio'),
    vigFin: document.getElementById('anularPolizaVigFin'),
    fecha: document.getElementById('anularPolizaFecha'),
    motivo: document.getElementById('anularPolizaMotivo'),
    motivoError: document.getElementById('anularPolizaMotivoError'),
    btnOk: document.getElementById('anularPolizaConfirm'),
    btnCancel: document.getElementById('anularPolizaCancel')
  };

  const toDateInputValue = (dateObj) => {
    const year = dateObj.getFullYear();
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    const day = String(dateObj.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const setMotivoError = (message) => {
    if (!anularFields.motivo) return;
    if (message) {
      anularFields.motivo.classList.add('is-invalid');
      if (anularFields.motivoError) anularFields.motivoError.textContent = message;
    } else {
      anularFields.motivo.classList.remove('is-invalid');
    }
  };

  const openAnularPolizaModal = (data) => {
    if (!anularModalEl || !anularModalInstance || !anularFields.motivo || !anularFields.btnOk) {
      const motivo = window.prompt('Motivo de anulación:');
      if (!motivo) return Promise.resolve(null);
      return Promise.resolve({
        motivo: motivo.trim(),
        fechaAnulacion: toDateInputValue(new Date())
      });
    }

    if (anularFields.numero) anularFields.numero.value = data.poliza || '';
    if (anularFields.asegurado) anularFields.asegurado.value = data.asegurado || '';
    if (anularFields.vigInicio) anularFields.vigInicio.value = data.vig_inicio || '';
    if (anularFields.vigFin) anularFields.vigFin.value = data.vig_fin || '';
    if (anularFields.fecha) {
      anularFields.fecha.value = toDateInputValue(new Date());
    }
    anularFields.motivo.value = '';
    setMotivoError('');

    return new Promise((resolve) => {
      let decided = false;

      const cleanup = () => {
        anularFields.btnOk.removeEventListener('click', onOk);
        anularFields.btnCancel?.removeEventListener('click', onCancel);
        anularModalEl.removeEventListener('hidden.bs.modal', onHidden);
        anularFields.motivo.removeEventListener('input', onInput);
      };

      const onInput = () => setMotivoError('');

      const onOk = () => {
        const motivo = anularFields.motivo.value.trim();
        if (!motivo) {
          setMotivoError('Ingrese el motivo de la anulación.');
          return;
        }
        if (motivo.length > 200) {
          setMotivoError('El motivo no puede exceder 200 caracteres.');
          return;
        }
        decided = true;
        cleanup();
        anularModalInstance.hide();
        resolve({
          motivo,
          fechaAnulacion: (anularFields.fecha?.value || toDateInputValue(new Date()))
        });
      };

      const onCancel = () => {
        decided = true;
        cleanup();
        anularModalInstance.hide();
        resolve(null);
      };

      const onHidden = () => {
        if (decided) return;
        cleanup();
        resolve(null);
      };

      anularFields.btnOk.addEventListener('click', onOk);
      anularFields.btnCancel?.addEventListener('click', onCancel);
      anularModalEl.addEventListener('hidden.bs.modal', onHidden);
      anularFields.motivo.addEventListener('input', onInput);

      anularModalInstance.show();
      anularFields.motivo.focus();
    });
  };

  // === 1. LÓGICA DE TABS (FILTROS DE BÚSQUEDA) ===
  if (searchTabs) {
    searchTabs.addEventListener('click', (e) => {
      if (e.target.classList.contains('sub-nav-link')) {
        e.preventDefault();
        
        const clickedTab = e.target;
        const isAlreadyActive = clickedTab.classList.contains('active');

        // Resetear todos los tabs
        searchTabs.querySelectorAll('.sub-nav-link').forEach(link => link.classList.remove('active'));
        
        if (isAlreadyActive) {
          // Si ya estaba activo, lo desactivamos (toggle off) -> Búsqueda General
          currentSearchType = 'general';
        } else {
          // Si no estaba activo, lo activamos
          clickedTab.classList.add('active');
          currentSearchType = clickedTab.getAttribute('data-search-type');
        }
        
        // Actualizar placeholder
        let placeholder = "Búsqueda General...";
        switch(currentSearchType) {
          case 'historica': placeholder = "Buscar por Número de Póliza Histórica..."; break;
          case 'aviso': placeholder = "Buscar por Aviso de Cobranza..."; break;
          case 'placa': placeholder = "Buscar por Placa o Motor..."; break;
          case 'titular': placeholder = "Buscar por Titular o Dependiente..."; break;
          default: placeholder = "Búsqueda General (Contratante, asegurado, póliza, placa...)";
        }
        if (globalSearchInput) globalSearchInput.placeholder = placeholder;
        
        // No disparamos búsqueda automática al cambiar tab, solo actualizamos el criterio
      }
    });
  }

  // === 2. LÓGICA DE BÚSQUEDA GLOBAL ===
  async function performGlobalSearch() {
    if (!globalSearchInput || !tbody) return;
    
    const query = globalSearchInput.value.trim();
    const type = currentSearchType;
    
    // Si no hay query, recargar la página original para mostrar el listado por defecto
    if (!query) {
        window.location.href = baseUrl;
        return;
    }
    
    // Ocultar paginación durante búsqueda global
    if (paginationBar) paginationBar.style.display = 'none';

    // Mostrar estado de carga
    tbody.innerHTML = `
      <tr>
        <td colspan="11" class="text-center py-5">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Cargando...</span>
          </div>
          <p class="text-muted mt-2">Buscando en todo el sistema...</p>
        </td>
      </tr>
    `;

    try {
      const response = await fetch(`/api/polizas/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(type)}`);
      const data = await response.json();

      const rows = data.rows || [];
      renderTable(rows);
      showNuevaPolizaBtn(rows);

    } catch (error) {
      console.error('Error search:', error);
      showError('Error de conexión al buscar');
    }
  }

  function showNuevaPolizaBtn(rows) {
    let existing = document.getElementById('nueva-poliza-hint');
    if (existing) existing.remove();
    if (rows.length !== 1) return;

    const row = rows[0];
    const contratante = row.contratante || '';

    const wrapper = document.createElement('div');
    wrapper.id = 'nueva-poliza-hint';
    wrapper.className = 'nueva-poliza-hint';
    wrapper.innerHTML = `
      <span class="nueva-poliza-hint__label">
        <i class="bi-person-check-fill"></i>
        ${contratante}
      </span>
      <button id="btnNuevaPolizaDesdeCliente" type="button" class="nueva-poliza-hint__btn">
        <i class="bi-plus-lg"></i> Nueva Póliza
      </button>
    `;

    const btn = wrapper.querySelector('#btnNuevaPolizaDesdeCliente');
    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
      try {
        const resp = await fetch(`/api/polizas/cliente-from-poliza?id=${encodeURIComponent(row.idPoliza)}`);
        const json = await resp.json();
        if (json.ok && json.redirect) {
          window.location.href = json.redirect;
        } else {
          alert(json.error || 'No se pudo obtener el cliente');
          btn.disabled = false;
          btn.innerHTML = '<i class="bi-plus-lg"></i> Nueva Póliza';
        }
      } catch {
        alert('Error de conexión');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi-plus-lg"></i> Nueva Póliza';
      }
    });

    const searchContainer = document.querySelector('.search-container');
    if (searchContainer) searchContainer.after(wrapper);
  }

  async function performModalSearch(q) {
    if (!searchModalEl || !searchModalBody) return;
    const query = (q ?? '').trim();
    const type = currentSearchType;
    if (!query) return;
    searchModalBody.innerHTML = `
      <div class="d-flex flex-column align-items-center justify-content-center py-5">
        <div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div>
        <p class="text-muted mt-2">Buscando en todo el sistema...</p>
      </div>
    `;
    const modal = bootstrap.Modal.getOrCreateInstance(searchModalEl);
    modal.show();

    const esc = (s) => {
      if (s == null) return '';
      return String(s)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    };

    try {
      const response = await fetch(`/api/polizas/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(type)}`);
      const data = await response.json();
      const rows = data.rows || [];
      if (!rows.length) {
        searchModalBody.innerHTML = `
          <div class="text-center text-muted py-5">
            <i class="bi-search display-6 d-block mb-3 opacity-25"></i>
            No se encontraron resultados para "${esc(query)}"
          </div>
        `;
        return;
      }
      let html = `
        <div class="mb-2 text-muted small fw-medium">Se encontraron ${rows.length} resultado${rows.length !== 1 ? 's' : ''}</div>
        <div class="searchresults-wrap">
          <table class="searchresults-table">
            <colgroup>
              <col class="col-sr-contratante">
              <col class="col-sr-asegurado">
              <col class="col-sr-cia">
              <col class="col-sr-prod">
              <col class="col-sr-poliza">
              <col class="col-sr-vig">
              <col class="col-sr-accion">
            </colgroup>
            <thead>
              <tr>
                <th>Contratante</th>
                <th>Asegurado</th>
                <th>Cía</th>
                <th>Prod</th>
                <th>Póliza</th>
                <th>Vigencia</th>
                <th class="col-sr-accion">Acciones</th>
              </tr>
            </thead>
            <tbody>
      `;
      rows.forEach(r => {
        const vigDesde = esc(r.ren_vig_desde || r.vig_desde || '');
        const vigHasta = esc(r.ren_vig_hasta || r.vig_hasta || '');
        const pol = esc(r.poliza || '');
        const polEnc = encodeURIComponent(r.poliza || '');
        const ciaInfo = companyPill(r.cia);
        const prodInfo = prodChip(r.producto, r.ramo);
        html += `
          <tr>
            <td class="col-sr-contratante"><span class="sr-cell-nombre">${esc(r.contratante || '')}</span></td>
            <td class="col-sr-asegurado"><span class="sr-cell-nombre">${esc(r.asegurado || '')}</span></td>
            <td class="col-sr-cia"><span class="company-pill ${ciaInfo[0]}">${esc(ciaInfo[1] || r.cia || '')}</span></td>
            <td class="col-sr-prod"><span class="prod-chip ${prodInfo[0]}">${esc(prodInfo[1] || r.producto || '')}</span></td>
            <td class="col-sr-poliza"><span class="sr-cell-poliza">${pol}</span></td>
            <td class="col-sr-vig"><span class="sr-cell-vig">${vigDesde}${vigDesde && vigHasta ? ' → ' : ''}${vigHasta}</span></td>
            <td class="col-sr-accion">
              <div class="sr-action-btns">
                <a href="${esc(primasUrlBase)}?poliza=${polEnc}" class="sr-btn sr-btn--primas" title="Ir a Primas">Primas</a>
                <a href="${esc(cuotasUrlBase)}?poliza=${polEnc}" class="sr-btn sr-btn--extracto" title="Ir a Extracto/Cuotas">Extracto</a>
                <a href="/menu/detalles-poliza?id=${encodeURIComponent(String(r.idPoliza || ''))}" class="sr-btn sr-btn--detalles" title="Ver detalles">Detalles</a>
              </div>
            </td>
          </tr>
        `;
      });
      html += `
            </tbody>
          </table>
        </div>
      `;
      searchModalBody.innerHTML = html;
    } catch (error) {
      searchModalBody.innerHTML = `
        <div class="text-center text-danger py-5">
          <i class="bi-exclamation-circle display-6 d-block mb-3"></i>
          Error de conexión al buscar
        </div>
      `;
    }
  }

  function renderTable(rows) {
    if (!tbody) return;
    tbody.innerHTML = '';
    
    if (!rows || rows.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="11" class="text-center text-muted py-5">
            <i class="bi-search display-6 d-block mb-3 opacity-25"></i>
            No se encontraron resultados para "${globalSearchInput.value}"
          </td>
        </tr>
      `;
      return;
    }

    const esc = (s) => {
      if (s == null) return '';
      return String(s)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    };

    rows.forEach(r => {
      const idP = String(r.idPoliza || '');
      const pol = String(r.poliza || '');
      const polEnc = encodeURIComponent(pol);
      const cia = companyPill(r.cia);
      const prod = prodChip(r.producto, r.ramo);
      const vigDesde = esc(r.ren_vig_desde || r.vig_desde || '');
      const vigHasta = esc(r.ren_vig_hasta || r.vig_hasta || '');
      const contratante = esc(r.contratante || '');
      const asegurado = esc(r.asegurado || '');
      const ramo = esc(r.ramo || '');
      const subAg = esc(r.sub_agente || '');
      const mAseg = esc(r.asegurada || '');

      const tr = document.createElement('tr');
      tr.className = 'poliza-row';
      tr.setAttribute('data-id', idP);
      tr.setAttribute('data-emision', esc(r.fecha_emision || ''));
      tr.setAttribute('data-poliza', pol);

      // MISMA ESTRUCTURA QUE JINJA: (1) Contratante (2) Aseg (3) Cía (4) Ram (5) Prod (6) Pol (7) VigI (8) VigF (9) SubAg (10) MAseg (11) Acc
      tr.innerHTML = `
        <td class="col-contratante"><span class="cell-nombre">${contratante || '<span class="text-muted small">—</span>'}</span></td>
        <td class="col-asegurado"><span class="cell-nombre">${asegurado || '<span class="text-muted small">—</span>'}</span></td>
        <td class="col-cia">${cia ? `<span class="company-pill ${cia[0]}">${esc(cia[1])}</span>` : '<span class="text-muted small">—</span>'}</td>
        <td class="col-ramo"><span class="cell-ramo">${ramo || '<span class="text-muted small">—</span>'}</span></td>
        <td class="col-prod">${prod ? `<span class="prod-chip ${prod[0]}">${esc(prod[1])}</span>` : '<span class="text-muted small">—</span>'}</td>
        <td class="col-poliza"><span class="cell-poliza">${esc(pol)}</span></td>
        <td class="col-vig-i"><span class="date-cell">${vigDesde || '<span class="text-muted small">—</span>'}</span></td>
        <td class="col-vig-f"><span class="date-cell">${vigHasta || '<span class="text-muted small">—</span>'}</span></td>
        <td class="col-subagente"><span class="cell-subagente">${subAg || '<span class="text-muted small">—</span>'}</span></td>
        <td class="col-maseg"><span class="cell-maseg">${mAseg || '<span class="text-muted small">—</span>'}</span></td>
        <td class="col-accion">
          <div class="action-buttons-col">
            <button type="button" class="btn-action btn-danger" data-action="anular">
              <i class="bi bi-x-circle-fill"></i><span>ANULAR</span>
            </button>

            <button type="button" class="btn-nueva-poliza" data-action="nueva-poliza" title="Nueva póliza para este cliente"></button>

            <a href="${primasUrlBase}?poliza=${polEnc}" class="btn-action btn-primary text-decoration-none">
              <i class="bi bi-file-earmark-check-fill"></i><span>PRIMAS</span>
            </a>

            <a href="${cuotasUrlBase}?poliza=${polEnc}" class="btn-action btn-teal text-decoration-none">
              <i class="bi bi-file-earmark-lock"></i><span>EXTRACTO</span>
            </a>

            <a href="${editUrlBase}?id=${encodeURIComponent(idP)}" class="btn-action btn-success text-decoration-none">
              <i class="bi bi-pencil-square"></i><span>EDITAR</span>
            </a>

            <div class="dropdown action-dropdown w-100">
              <button class="btn-dropdown dropdown-toggle w-100" type="button" data-bs-toggle="dropdown" data-bs-boundary="viewport" data-bs-popper-config='{"strategy":"fixed"}' aria-expanded="false">
                <i class="bi bi-three-dots"></i><span>MAS OPCIONES</span>
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" href="${siniestrosUrlBase}?poliza=${polEnc}"><i class="bi bi-exclamation-triangle"></i> Siniestros</a></li>
                <li><a class="dropdown-item" href="#" data-action="solicitudes"><i class="bi bi-briefcase"></i> Solicitudes</a></li>
                <li><a class="dropdown-item" href="#" data-action="renovar"><i class="bi bi-arrow-repeat"></i> Renovar</a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item" href="/menu/detalles-poliza?id=${encodeURIComponent(idP)}"><i class="bi bi-info-circle"></i> Detalles</a></li>
                <li><a class="dropdown-item" href="/menu/detalles-poliza?id=${encodeURIComponent(idP)}&print=true" target="_blank"><i class="bi bi-printer"></i> Imprimir</a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-danger" href="#" data-action="eliminar"><i class="bi bi-trash-fill"></i> Eliminar</a></li>
              </ul>
            </div>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function showError(msg) {
    if (!tbody) return;
    tbody.innerHTML = `
      <tr>
        <td colspan="11" class="text-center text-danger py-5">
          <i class="bi-exclamation-circle display-6 d-block mb-3"></i>
          ${msg}
        </td>
      </tr>
    `;
  }

  // Helper: devuelve [clase pill, texto] para una compañía
  function companyPill(ciaStr) {
    if (!ciaStr) return null;
    const c = String(ciaStr).toLowerCase().replace(/\s+/g, '');
    if (c.includes('mapfre')) return ['company-mapfre', 'MAPFRE'];
    if (c.includes('rimac')) return ['company-rimac', 'RIMAC'];
    if (c.includes('lapositiva') || c.includes('positiva')) return ['company-la-positiva', 'LA POSITIVA'];
    if (c.includes('pacifico') || c.includes('pacífico')) return ['company-pacifico', 'PACÍFICO'];
    if (c.includes('hdi')) return ['company-hdi', 'HDI'];
    if (c.includes('crecer')) return ['company-crecer', 'CRECER'];
    return ['company-default', String(ciaStr).slice(0, 12).toUpperCase()];
  }

  // Helper: devuelve [clase chip, texto] para un producto
  function prodChip(prodStr, ramoStr) {
    const s = String(prodStr || ramoStr || '').toLowerCase().replace(/\s+/g, '');
    if (!s) return null;
    if (s.includes('soat')) return ['prod-chip--soat', 'SOAT'];
    if (s.includes('particular') || s.includes('vehicular')) return ['prod-chip--particular', 'PARTICULAR'];
    if (s.includes('empresarial') || s.includes('empresa') || s.includes('flota')) return ['prod-chip--empresarial', 'EMPRESARIAL'];
    return ['prod-chip--default', String(prodStr || ramoStr || '').slice(0, 10).toUpperCase()];
  }

  // Event Listeners Búsqueda Global
  if (globalSearchBtn) {
    globalSearchBtn.addEventListener('click', performGlobalSearch);
  }
  if (globalSearchInput) {
    globalSearchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') performGlobalSearch();
    });
  }
  if (voiceSearchBtn) {
    voiceSearchBtn.addEventListener('click', () => {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {
        alert('Tu navegador no soporta búsqueda por voz');
        return;
      }
      const recognition = new SR();
      recognition.lang = 'es-ES';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;
      const modal = searchModalEl ? bootstrap.Modal.getOrCreateInstance(searchModalEl) : null;
      const originalIcon = voiceSearchBtn.innerHTML;
      const setListeningUI = () => {
        voiceSearchBtn.disabled = true;
        voiceSearchBtn.classList.add('active');
        voiceSearchBtn.innerHTML = '<i class="bi-mic-mute-fill"></i>';
        if (searchModalBody && modal) {
          searchModalBody.innerHTML = `
            <div class="text-center py-5">
              <i class="bi-mic-fill display-6 text-danger d-block mb-3"></i>
              <div>Escuchando...</div>
              <div class="text-muted small mt-1">Hable ahora cerca del micrófono</div>
            </div>
          `;
          modal.show();
        }
      };
      const resetUI = () => {
        voiceSearchBtn.disabled = false;
        voiceSearchBtn.classList.remove('active');
        voiceSearchBtn.innerHTML = originalIcon;
      };
      recognition.onstart = setListeningUI;
      recognition.onresult = (event) => {
        const raw = (event.results?.[0]?.[0]?.transcript || '');
        const transcript = raw.replace(/[.。]+$/,'').trim();
        if (transcript) {
          if (globalSearchInput) globalSearchInput.value = transcript;
          if (searchModalBody) {
            searchModalBody.innerHTML = `
              <div class="text-center py-3">
                <div class="mb-2">Texto reconocido:</div>
                <div class="fs-5">${transcript}</div>
              </div>
            `;
          }
          performModalSearch(transcript);
        }
      };
      recognition.onerror = () => {
        if (searchModalBody) {
          searchModalBody.innerHTML = `
            <div class="text-center text-danger py-5">
              <i class="bi-exclamation-circle display-6 d-block mb-3"></i>
              No se pudo capturar audio
            </div>
          `;
        }
        resetUI();
      };
      recognition.onend = resetUI;
      recognition.start();
    });
  }
  if (applyResultsToTableBtn) {
    applyResultsToTableBtn.addEventListener('click', () => {
      if (!globalSearchInput.value.trim()) return;
      if (searchModalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(searchModalEl);
        modal.hide();
      }
      performGlobalSearch();
    });
  }

  // === 3. Sincronizar tamaño de página (Solo si no hay búsqueda global activa) ===
  const pageSizeSel = document.getElementById('page-size');
  if (pageSizeSel) {
    pageSizeSel.addEventListener('change', () => {
      // Si estamos en modo búsqueda global, quizás deberíamos re-buscar con límite diferente?
      // Por ahora, la búsqueda global es fija a 100 resultados.
      // Si NO estamos en búsqueda global (url normal), recargamos.
      if (!globalSearchInput.value.trim()) {
         const params = new URLSearchParams(window.location.search);
         params.set('per_page', pageSizeSel.value);
         params.set('page', '1');
         window.location.href = `${baseUrl}?${params.toString()}`;
      }
    });
  }

  // === 4. Manejo de Acciones (Delegación de eventos) ===
  if (table) {
    table.addEventListener('click', async (e) => {
        // Manejar clicks en botones o items de dropdown
        const actionEl = e.target.closest('[data-action]');

        // 🔴 GUARDA CRÍTICA: Si el clickeado es un <a href> SIN data-action (PRIMAS, EXTRACTO, EDITAR),
        //    NO hacemos nada. El browser hace la navegación NATIVA instantánea (sin demora, sin preventDefault).
        if (!actionEl) {
            const plainLink = e.target.closest('a[href]');
            if (plainLink && !plainLink.getAttribute('data-action')) {
                return; // ← DEJA NAVEGAR → instantáneo como antes
            }
            return;
        }

        e.preventDefault();
        const action = actionEl.getAttribute('data-action');
        const row = actionEl.closest('tr');
        const idPoliza = row?.getAttribute('data-id');
        const poliza = row?.getAttribute('data-poliza');

        if (!idPoliza) return;

        console.log(`Acción: ${action}, ID: ${idPoliza}, Poliza: ${poliza}`);

        if (action === 'renovar') {
            // Usar la función global de renovar-poliza.js
            if (window.openRenovarPolizaModal) {
                window.openRenovarPolizaModal({ idPoliza: idPoliza, poliza: poliza }); 
            } else {
                console.error('openRenovarPolizaModal no definido');
            }
        } else if (action === 'anular') {
             const modalResult = await openAnularPolizaModal({
                 poliza,
                 asegurado: row?.querySelector('td:nth-child(2)')?.textContent?.trim() || '',
                 vig_inicio: row?.querySelector('td:nth-child(7)')?.textContent?.trim() || '',
                 vig_fin: row?.querySelector('td:nth-child(8)')?.textContent?.trim() || ''
             });
             if (!modalResult) return;
             try {
                 const resp = await fetch('/api/polizas/anular', {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({
                       idPoliza,
                       motivo: modalResult.motivo,
                       fechaAnulacion: modalResult.fechaAnulacion
                     })
                 });
                 const json = await resp.json();
                 if (json.ok) {
                     row.style.opacity = '0.5';
                     row.classList.add('table-warning');
                 } else {
                     alert(json.error || 'No se pudo anular la póliza');
                 }
             } catch (e) {
                 console.error(e);
                 alert('Error de conexión al anular');
             }
        } else if (action === 'nueva-poliza') {
            const btn = actionEl;
            const originalHTML = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
            try {
                const resp = await fetch(`/api/polizas/cliente-from-poliza?id=${encodeURIComponent(idPoliza)}`);
                const json = await resp.json();
                if (json.ok && json.redirect) {
                    window.location.href = json.redirect;
                } else {
                    alert(json.error || 'No se pudo obtener el cliente');
                    btn.disabled = false;
                    btn.innerHTML = originalHTML;
                }
            } catch {
                alert('Error de conexión');
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            }
        } else if (action === 'eliminar') {
             if (!confirm(`ELIMINAR PERMANENTEMENTE la póliza "${poliza}" junto con todas sus cuotas. Esta acción es irreversible. ¿Continuar?`)) return;
             try {
                 const resp = await fetch('/polizas/hard-delete', {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({ idPoliza })
                 });
                 const json = await resp.json();
                 if (json.ok) {
                     row.remove();
                 } else {
                     alert(json.errors?.[0] || json.error || 'No se pudo eliminar la póliza');
                 }
             } catch (e) {
                 console.error(e);
                 alert('Error de conexión al eliminar');
             }
        } else if (action === 'solicitudes') {
             alert(`Funcionalidad de ${action} en desarrollo`);
        }
    });
  }

  // === 5. BOTONES DE FILTRO RÁPIDO (Vencen este Mes / Ver Vigentes / Ver Todos) ===
  const filterBtns = document.querySelectorAll('.btn-filter-rapido');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const filterType = btn.getAttribute('data-filter');

      // "Ver Todos" o click en botón ya activo → volver al estado original
      if (filterType === 'todos' || btn.classList.contains('active')) {
        filterBtns.forEach(b => b.classList.remove('active'));
        window.location.href = baseUrl;
        return;
      }

      // Marcar el botón activo y desmarcar los demás
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      if (globalSearchInput) globalSearchInput.value = '';

      // esconde paginacion del filtro
      if (paginationBar) paginationBar.style.display = 'none';

      // mostrar visual
      tbody.innerHTML = `
        <tr>
          <td colspan="11" class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Cargando...</span>
            </div>
            <p class="text-muted mt-2">Aplicando filtro...</p>
          </td>
        </tr>
      `;

      try {
        const response = await fetch(`/api/polizas/search?filter=${encodeURIComponent(filterType)}`);
        const data = await response.json();
        const rows = data.rows || [];

        if (rows.length === 0) {
          const label = filterType === 'vigentes' ? 'pólizas vigentes' : 'pólizas que vencen este mes';
          tbody.innerHTML = `
            <tr>
              <td colspan="11" class="text-center text-muted py-5">
                <i class="bi-search display-6 d-block mb-3 opacity-25"></i>
                No se encontraron ${label}
              </td>
            </tr>
          `;
        } else {
          renderTable(rows);
        }
      } catch (error) {
        console.error('Error al aplicar filtro:', error);
        showError('Error de conexión al filtrar');
      }
    });
  });

});
