(function () {
  document.addEventListener('DOMContentLoaded', function () {
    // === REFERENCIAS DOM ===
    const globalSearchInput = document.getElementById('polizasSearch');
    const globalSearchBtn = document.querySelector('.btn-search'); // Asumiendo que es el botón "Buscar" junto al input
    const tableSearchInput = document.getElementById('tableSearch');
    const searchTabs = document.getElementById('searchTabs');
    const table = document.getElementById('polizasTable');
    const tbody = table ? table.querySelector('tbody') : null;
    const totalRegistrosEl = document.querySelector('.pagination-container .text-muted');

    const confirmModalEl = document.getElementById('actionConfirmModal');
    const confirmModalTitleEl = document.getElementById('actionConfirmModalLabel');
    const confirmModalBodyEl = document.getElementById('actionConfirmModalBody');
    const confirmModalCancelBtn = document.getElementById('actionConfirmCancel');
    const confirmModalOkBtn = document.getElementById('actionConfirmOk');
    const confirmModalInstance = (confirmModalEl && window.bootstrap)
      ? bootstrap.Modal.getOrCreateInstance(confirmModalEl, { backdrop: 'static' })
      : null;

    function openActionModal(opts) {
      const title = (opts?.title ?? 'Aviso').toString();
      const message = (opts?.message ?? '').toString();
      const okText = (opts?.okText ?? 'Aceptar').toString();
      const cancelText = (opts?.cancelText ?? 'Cancelar').toString();
      const okClass = (opts?.okClass ?? 'btn-primary').toString();
      const showCancel = Boolean(opts?.showCancel);

      if (!confirmModalEl || !confirmModalInstance || !confirmModalOkBtn) {
        if (showCancel) {
          return Promise.resolve(window.confirm(message || title));
        }
        window.alert(message || title);
        return Promise.resolve(false);
      }

      if (confirmModalTitleEl) confirmModalTitleEl.textContent = title;
      if (confirmModalBodyEl) confirmModalBodyEl.textContent = message;
      confirmModalOkBtn.textContent = okText;
      confirmModalOkBtn.className = `btn ${okClass} rounded-pill px-4`;

      if (confirmModalCancelBtn) {
        confirmModalCancelBtn.textContent = cancelText;
        confirmModalCancelBtn.style.display = showCancel ? '' : 'none';
      }

      return new Promise((resolve) => {
        let decided = false;

        const cleanup = () => {
          confirmModalOkBtn.removeEventListener('click', onOk);
          confirmModalCancelBtn?.removeEventListener('click', onCancel);
          confirmModalEl.removeEventListener('hidden.bs.modal', onHidden);
        };

        const onOk = () => {
          decided = true;
          cleanup();
          confirmModalInstance.hide();
          resolve(true);
        };

        const onCancel = () => {
          decided = true;
          cleanup();
          confirmModalInstance.hide();
          resolve(false);
        };

        const onHidden = () => {
          if (decided) return;
          cleanup();
          resolve(false);
        };

        confirmModalOkBtn.addEventListener('click', onOk);
        confirmModalCancelBtn?.addEventListener('click', onCancel);
        confirmModalEl.addEventListener('hidden.bs.modal', onHidden);

        confirmModalInstance.show();
      });
    }

    function showInfoModal(message, title) {
      return openActionModal({
        title: title || 'Aviso',
        message: message || '',
        okText: 'Aceptar',
        okClass: 'btn-primary',
        showCancel: false
      });
    }

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
          
          // Opcional: Ejecutar búsqueda si hay texto
          // if (globalSearchInput && globalSearchInput.value.trim()) {
          //   performGlobalSearch();
          // }
        }
      });
    }

    // === 2. LÓGICA DE BÚSQUEDA GLOBAL ===
    async function performGlobalSearch() {
      if (!globalSearchInput || !tbody) return;
      
      const query = globalSearchInput.value.trim();
      const type = currentSearchType;
      
      // Mostrar estado de carga
      tbody.innerHTML = `
        <tr>
          <td colspan="12" class="text-center py-5">
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
        
        if (data.ok) {
          renderTable(data.rows);
        } else {
          showError('Error al realizar la búsqueda');
        }
      } catch (error) {
        console.error('Error search:', error);
        showError('Error de conexión');
      }
    }

    function renderTable(rows) {
      if (!tbody) return;
      tbody.innerHTML = '';
      
      if (!rows || rows.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="12" class="text-center text-muted py-5">
              <i class="bi-search display-6 d-block mb-3 opacity-25"></i>
              No se encontraron resultados para "${globalSearchInput.value}"
            </td>
          </tr>
        `;
        if (totalRegistrosEl) totalRegistrosEl.textContent = 'Total de registros: 0';
        return;
      }

      if (totalRegistrosEl) totalRegistrosEl.textContent = `Total de registros: ${rows.length}`;

      // Obtener URL base para primas desde el atributo data (si existe) o fallback
      const primasUrlBase = table.getAttribute('data-primas-url') || '/menu/primas';

      rows.forEach(r => {
        const tr = document.createElement('tr');
        tr.setAttribute('data-id', r.idPoliza);
        tr.setAttribute('data-emision', r.fecha_emision || '');
        tr.className = 'poliza-row';

        const v = (val) => val || '';

        const cia = v(r.cia);
        const ciaLower = cia.toLowerCase().replace(/\s+/g, '-').replace(/\./g, '');
        let ciaClass = 'company-default';
        if (ciaLower.includes('positiva') || ciaLower.includes('la-positiva')) ciaClass = 'company-la-positiva';
        else if (ciaLower.includes('crecer')) ciaClass = 'company-crecer';
        else if (ciaLower.includes('rimac')) ciaClass = 'company-rimac';
        else if (ciaLower.includes('pacifico')) ciaClass = 'company-pacifico';
        else if (ciaLower.includes('mapfre')) ciaClass = 'company-mapfre';
        else if (ciaLower.includes('hdi')) ciaClass = 'company-hdi';

        const prod = v(r.producto);
        const prodLower = prod.toLowerCase().replace(/\s+/g, '-').replace(/\./g, '');
        let prodClass = 'prod-chip--default';
        if (prodLower.includes('soat')) prodClass = 'prod-chip--soat';
        else if (prodLower.includes('particular')) prodClass = 'prod-chip--particular';
        else if (prodLower.includes('empresa') || prodLower.includes('empresarial')) prodClass = 'prod-chip--empresarial';

        const vigDesde = v(r.ren_vig_desde || r.vig_desde);
        const vigHasta = v(r.ren_vig_hasta || r.vig_hasta);
        const primasHref = `${primasUrlBase}?poliza=${encodeURIComponent(v(r.poliza))}&return=polizas`;
        const extractoHref = `/menu/cuotas?poliza=${encodeURIComponent(v(r.poliza))}`;
        const detallesHref = `/menu/detalles-poliza?id=${r.idPoliza}`;
        const editarHref = `/menu/editar-poliza?id=${r.idPoliza}`;

        tr.innerHTML = `
          <td class="col-contratante"><span class="cell-nombre">${v(r.contratante)}</span></td>
          <td class="col-asegurado"><span class="cell-nombre">${v(r.asegurado)}</span></td>
          <td class="col-cia"><span class="company-pill ${ciaClass}">${cia}</span></td>
          <td class="col-ramo"><span class="cell-ramo">${v(r.ramo)}</span></td>
          <td class="col-prod"><span class="prod-chip ${prodClass}">${prod}</span></td>
          <td class="col-poliza"><span class="cell-poliza">${v(r.poliza)}</span></td>
          <td class="col-moneda"><span class="moneda-badge">${v(r.moneda)}</span></td>
          <td class="col-vig-i"><span class="date-cell">${vigDesde}</span></td>
          <td class="col-vig-f"><span class="date-cell">${vigHasta}</span></td>
          <td class="col-subagente"><span class="cell-subagente">${v(r.sub_agente)}</span></td>
          <td class="col-maseg"><span class="cell-maseg">${v(r.asegurada)}</span></td>
          <td class="col-accion">
              <div class="action-buttons-col">
                  <button type="button" class="btn-action btn-danger" data-action="anular">
                      <i class="bi-x-circle-fill"></i><span>ANULAR</span>
                  </button>

                  <a href="${primasHref}" class="btn-action btn-primary text-decoration-none" data-action="primas">
                      <i class="bi-file-earmark-check-fill"></i><span>PRIMAS</span>
                  </a>

                  <a href="${extractoHref}" class="btn-action btn-teal text-decoration-none" data-action="extracto">
                      <i class="bi-file-earmark-lock"></i><span>EXTRACTO</span>
                  </a>

                  <a href="${detallesHref}" class="btn-action btn-gray text-decoration-none" data-action="detalles">
                      <i class="bi-info-circle"></i><span>DETALLES</span>
                  </a>

                  <a href="${editarHref}" class="btn-action btn-success text-decoration-none" data-action="editar">
                      <i class="bi-pencil-square"></i><span>EDITAR</span>
                  </a>

                  <a href="#" class="btn-action btn-violet text-decoration-none" data-action="siniestros">
                      <i class="bi-exclamation-triangle"></i><span>SINIESTROS</span>
                  </a>
              </div>
          </td>
        `;
        tbody.appendChild(tr);
      });
      
      // Actualizar referencias para el filtro local
      updateLocalRows();
    }

    function showError(msg) {
      if (!tbody) return;
      tbody.innerHTML = `
        <tr>
          <td colspan="12" class="text-center text-danger py-5">
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

    // === 3. LÓGICA DE FILTRO LOCAL (EN TABLA) ===
    let localRows = table ? Array.from(table.querySelectorAll('tbody tr')) : [];

    function updateLocalRows() {
      if (table) {
        localRows = Array.from(table.querySelectorAll('tbody tr'));
      }
    }

    function filterLocalRows(term) {
      const q = term.trim().toLowerCase();
      localRows.forEach(tr => {
        // Ignorar filas de mensaje/loading
        if (tr.cells.length < 2) return; 
        
        const text = tr.textContent.toLowerCase();
        tr.style.display = text.includes(q) ? '' : 'none';
      });
    }

    // Vincular filtro local al input de la tabla (no al global)
    if (tableSearchInput) {
      tableSearchInput.addEventListener('input', (e) => filterLocalRows(e.target.value));
    }

    // === 4. DELEGACIÓN DE ACCIONES (Lógica Original Preservada) ===
    table?.addEventListener('click', async (e) => {
      const actionEl = e.target.closest('[data-action]');
      if (!actionEl) return;
      
      if (actionEl.tagName === 'A' && actionEl.getAttribute('href') && actionEl.getAttribute('href') !== '#' && !['detalles', 'editar'].includes(actionEl.dataset.action)) {
        return;
      }

      e.preventDefault();

      const action = actionEl.dataset.action;
      const row = actionEl.closest('tr');
      if (!row) return;

      // Helper para extraer datos de la fila (índices basados en columnas)
      const pick = (n) => row.querySelector(`td:nth-child(${n})`)?.textContent?.trim() || '';

      const data = {
        contratante: pick(1),
        asegurado: pick(2),
        cia: pick(3),
        ramo: pick(4),
        producto: pick(5),
        poliza: pick(6),
        materiaAsegurada: pick(11),
        vig_inicio: pick(8),
        vig_fin: pick(9),
        idPoliza: row.getAttribute('data-id')
      };

      console.log(`Ejecutando acción: ${action}`, data);

      switch (action) {
        case 'primas':
          const primasUrl = table.getAttribute('data-primas-url');
          if (primasUrl && data.poliza) {
            window.location.href = `${primasUrl}?poliza=${encodeURIComponent(data.poliza)}&return=polizas`;
          }
          break;

        case 'renovar':
          if (typeof window.openRenovarPolizaModal === 'function') {
            window.openRenovarPolizaModal(data);
          } else {
            showInfoModal('El modal de renovación no está cargado correctamente.');
          }
          break;

        case 'extracto':
            window.location.href = `/menu/cuotas?poliza=${encodeURIComponent(data.poliza)}`;
            break;

        case 'siniestros':
          window.location.href = `/menu/siniestros-poliza?poliza=${encodeURIComponent(data.poliza)}`;
          break;

        case 'detalles':
          const modalEl = document.getElementById('detallesPolizaModal');
          const modalBody = document.getElementById('detallesPolizaModalBody');
          // Use existing instance if any, or create new
          let bsModal = bootstrap.Modal.getInstance(modalEl);
          if (!bsModal) {
            bsModal = new bootstrap.Modal(modalEl);
          }
          
          // Show modal with loading state
          modalBody.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando...</span>
                </div>
            </div>`;
          bsModal.show();
          
          // Construct URL
          let url = actionEl.getAttribute('href');
          if (url.includes('?')) {
              url += '&partial=true';
          } else {
              url += '?partial=true';
          }
          
          fetch(url)
            .then(res => res.text())
            .then(html => {
                modalBody.innerHTML = html;
            })
            .catch(err => {
                console.error(err);
                modalBody.innerHTML = '<div class="alert alert-danger m-3">Error al cargar detalles</div>';
            });
          break;
          
        case 'editar':
          {
            const modalEl = document.getElementById('editarPolizaModal');
            const modalBody = document.getElementById('editarPolizaModalBody');
            const btnGuardarModal = document.getElementById('editarPolizaModalGuardar');
            if (!modalEl || !modalBody) {
              if (data.idPoliza) window.location.href = `/menu/editar-poliza?id=${data.idPoliza}`;
              break;
            }

            let bsModal = bootstrap.Modal.getInstance(modalEl);
            if (!bsModal) bsModal = new bootstrap.Modal(modalEl);

            const ensureStylesheet = (href) => {
              const existing = Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
                .some(l => (l.getAttribute('href') || '').includes(href));
              if (existing) return;
              const link = document.createElement('link');
              link.rel = 'stylesheet';
              link.href = href;
              document.head.appendChild(link);
            };

            const ensureScript = (src) => {
              return new Promise((resolve, reject) => {
                const existing = Array.from(document.querySelectorAll('script'))
                  .some(s => (s.getAttribute('src') || '') === src);
                if (existing) return resolve();
                const script = document.createElement('script');
                script.src = src;
                script.onload = () => resolve();
                script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
                document.body.appendChild(script);
              });
            };

            modalBody.innerHTML = `
              <div class="text-center py-5 rounded-3" style="background: var(--card-bg); border: 1px solid var(--card-border);">
                <div class="spinner-border text-primary" role="status">
                  <span class="visually-hidden">Cargando...</span>
                </div>
              </div>`;
            bsModal.show();

            try {
              ensureStylesheet('/static/css/editar-poliza.css');
              await ensureScript('https://cdn.jsdelivr.net/npm/sweetalert2@11');
              await ensureScript('/static/js/editar-poliza.js');
            } catch (e) {
              console.error(e);
            }

            let url = actionEl.getAttribute('href') || '';
            if (!url && data.idPoliza) url = `/menu/editar-poliza?id=${data.idPoliza}`;
            if (url.includes('?')) url += '&partial=true';
            else url += '?partial=true';

            fetch(url)
              .then(res => res.text())
              .then(html => {
                modalBody.innerHTML = html;
                if (typeof window.initEditarPoliza === 'function') {
                  window.initEditarPoliza(modalBody);
                }
              })
              .catch(err => {
                console.error(err);
                modalBody.innerHTML = '<div class="alert alert-danger m-3">Error al cargar formulario de edición</div>';
              });

            if (btnGuardarModal) {
              btnGuardarModal.onclick = () => {
                const btnGuardar = modalBody.querySelector('#btnGuardar');
                if (btnGuardar) btnGuardar.click();
              };
            }

            break;
          }

        case 'anular':
           (async () => {
             try {
               if (!data.idPoliza) {
                 showInfoModal('ID de póliza no encontrado');
                 return;
               }

               const modalResult = await openAnularPolizaModal(data);
               if (!modalResult) return;

               const resp = await fetch('/api/polizas/anular', {
                 method: 'POST',
                 headers: {
                   'Content-Type': 'application/json'
                 },
                 body: JSON.stringify({
                   idPoliza: data.idPoliza,
                   motivo: modalResult.motivo,
                   fechaAnulacion: modalResult.fechaAnulacion
                 })
               });
               const json = await resp.json();
               if (json.ok) {
                 row.style.opacity = '0.5';
                 row.classList.add('table-warning');
               } else {
                 showInfoModal(json.error || 'No se pudo anular la póliza');
               }
             } catch (e) {
               console.error(e);
               showInfoModal('Error de conexión al anular la póliza');
             }
           })();
           break;

        default:
          showInfoModal(`Acción "${action.toUpperCase()}" para la póliza ${data.poliza}`);
          break;
      }
    });
  });
})();
