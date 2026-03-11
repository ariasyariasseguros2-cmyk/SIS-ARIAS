document.addEventListener('DOMContentLoaded', () => {
  // === REFERENCIAS DOM ===
  const globalSearchInput = document.getElementById('polizasSearch');
  const globalSearchBtn = document.getElementById('btnGlobalSearch');
  const searchTabs = document.getElementById('searchTabs');
  const table = document.getElementById('polizasListTable');
  const tbody = document.getElementById('polizasTableBody');
  const paginationBar = document.getElementById('paginationBar');
  
  // URLs base desde atributos data
  // Corrección: Selector actualizado a .table-card
  const cardContainer = document.querySelector('.table-card[data-base-url]');
  const baseUrl = cardContainer?.getAttribute('data-base-url') || window.location.pathname;
  const primasUrlBase = cardContainer?.getAttribute('data-primas-url') || '/menu/primas';
  const cuotasUrlBase = cardContainer?.getAttribute('data-cuotas-url') || '/menu/cuotas';
  const editUrlBase = cardContainer?.getAttribute('data-edit-url') || '/menu/editar-poliza';
  const siniestrosUrlBase = cardContainer?.getAttribute('data-siniestros-url') || '/menu/siniestros-poliza';

  let currentSearchType = 'general';

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
        <td colspan="13" class="text-center py-5">
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
      
    } catch (error) {
      console.error('Error search:', error);
      showError('Error de conexión al buscar');
    }
  }

  function renderTable(rows) {
    if (!tbody) return;
    tbody.innerHTML = '';
    
    if (!rows || rows.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="13" class="text-center text-muted py-5">
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
        <td>${v(r.usuario_registro)}</td>
        <td>${v(r.usuario_edicion)}</td>
        <td class="text-end">
          <div class="action-buttons justify-content-end">
              <!-- Botones Visibles Prioritarios -->
              <button type="button" class="btn-action btn-danger" data-action="anular" title="Anular">
                  Anular
              </button>
              
              <button type="button" class="btn-action btn-success" data-action="renovar" title="Renovar">
                  Renovar
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
             if (!confirm('¿Está seguro de anular esta póliza?')) return;
             try {
                 const resp = await fetch('/api/polizas/anular', {
                     method: 'POST',
                     headers: { 'Content-Type': 'application/json' },
                     body: JSON.stringify({ idPoliza })
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
          <td colspan="13" class="text-center py-5">
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
              <td colspan="13" class="text-center text-muted py-5">
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
