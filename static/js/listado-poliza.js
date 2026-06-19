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
    try {
      const response = await fetch(`/api/polizas/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(type)}`);
      const data = await response.json();
      const rows = data.rows || [];
      if (!rows.length) {
        searchModalBody.innerHTML = `
          <div class="text-center text-muted py-5">
            <i class="bi-search display-6 d-block mb-3 opacity-25"></i>
            No se encontraron resultados para "${query}"
          </div>
        `;
        return;
      }
      let html = `
        <div class="mb-2 text-muted small">Se encontraron ${rows.length} resultado${rows.length !== 1 ? 's' : ''}</div>
        <div class="table-responsive">
          <table class="table">
            <thead>
              <tr>
                <th>Contratante</th>
                <th>Asegurado</th>
                <th>Cía</th>
                <th>Prod</th>
                <th>Póliza</th>
                <th>Vigencia</th>
                <th class="text-end">Acciones</th>
              </tr>
            </thead>
            <tbody>
      `;
      rows.forEach(r => {
        const vig = `${r.vig_desde || ''} - ${r.vig_hasta || ''}`;
        html += `
          <tr>
            <td>${r.contratante || ''}</td>
            <td>${r.asegurado || ''}</td>
            <td>${r.cia || ''}</td>
            <td>${r.producto || r.ramos_producto || ''}</td>
            <td>${r.poliza || ''}</td>
            <td>${vig}</td>
            <td class="text-end">
              <a href="${primasUrlBase}?poliza=${encodeURIComponent(r.poliza || '')}" class="btn btn-sm btn-primary me-1">Primas</a>
              <a href="${cuotasUrlBase}?poliza=${encodeURIComponent(r.poliza || '')}" class="btn btn-sm btn-outline-secondary me-1">Extracto</a>
              <a href="/menu/detalles-poliza?id=${r.idPoliza}" class="btn btn-sm btn-outline-dark">Detalles</a>
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

    // Helper para nulos
    const v = (val) => val || '';

    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.classList.add('align-middle');
      tr.setAttribute('data-id', r.idPoliza);
      tr.setAttribute('data-emision', r.fecha_emision || '');
      tr.setAttribute('data-poliza', r.poliza || '');

      // Estilo de botones: Usamos el estilo flex de polizas.html pero adaptado.
      // Corrección: Eliminados data-action de enlaces de navegación (Primas, Extracto, Editar)
      
      tr.innerHTML = `
        <td>${v(r.contratante)}</td>
        <td>${v(r.asegurado)}</td>
        <td>${v(r.cia)}</td>
        <td>${v(r.ramo)}</td>
        <td>${v(r.producto)}</td>
        <td>${v(r.poliza)}</td>
        <td>${v(r.vig_desde)}</td>
        <td>${v(r.vig_hasta)}</td>
        <td>${v(r.sub_agente)}</td>
        <td>${v(r.asegurada)}</td>
        <td class="text-end">
          <div class="action-buttons justify-content-end">
              <!-- Botones Visibles Prioritarios -->
              <button type="button" class="btn-action btn-danger" data-action="anular" title="Anular">
                  Anular
              </button>

              <button type="button" class="btn-action btn-success" data-action="renovar" title="Renovar">
                  Renovar
              </button>

              <button type="button" class="btn-action btn-nueva-poliza" data-action="nueva-poliza" title="Agregar nueva póliza para este cliente">
                  <i class="bi-plus-lg"></i>
              </button>

              <a href="${primasUrlBase}?poliza=${encodeURIComponent(r.poliza)}" class="btn-action btn-primary text-decoration-none" title="Primas">
                  Primas
              </a>

              <!-- Dropdown para resto de acciones -->
              <div class="dropdown action-dropdown ms-1">
                  <button class="btn-dropdown dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                      Acción
                  </button>
                  <ul class="dropdown-menu dropdown-menu-end">
                      <li><a class="dropdown-item" href="${cuotasUrlBase}?poliza=${encodeURIComponent(r.poliza)}"><i class="bi-file-text"></i> Extracto</a></li>
                      <li><a class="dropdown-item" href="${siniestrosUrlBase}?poliza=${encodeURIComponent(r.poliza)}"><i class="bi-exclamation-triangle"></i> Siniestros</a></li>
                      <li><a class="dropdown-item" href="#" data-action="solicitudes"><i class="bi-briefcase"></i> Solicitudes</a></li>
                      <li><hr class="dropdown-divider"></li>
                      <li><a class="dropdown-item" href="/menu/detalles-poliza?id=${r.idPoliza}"><i class="bi-info-circle"></i> Detalles</a></li>
                      <li><a class="dropdown-item" href="${editUrlBase}?id=${r.idPoliza}"><i class="bi-pencil-square"></i> Editar</a></li>
                      <li><a class="dropdown-item" href="/menu/detalles-poliza?id=${r.idPoliza}&print=true" target="_blank"><i class="bi-printer"></i> Imprimir</a></li>
                      <li><a class="dropdown-item text-danger" href="#" data-action="eliminar"><i class="bi-trash"></i> Eliminar</a></li>
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
        <td colspan="13" class="text-center text-danger py-5">
          <i class="bi-exclamation-circle display-6 d-block mb-3"></i>
          ${msg}
        </td>
      </tr>
    `;
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
        if (!actionEl) return;

        // Si es un enlace normal (sin data-action), no prevenimos default.
        // Pero aquí hemos filtrado por [data-action], así que se supone que son acciones JS.
        // Si por error queda un data-action en un href, esto prevendrá la navegación.
        // Por eso hemos quitado data-action de los hrefs de navegación.

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
             if (confirm('¿Está seguro de eliminar esta póliza?')) {
                 alert('Funcionalidad de eliminar pendiente');
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
