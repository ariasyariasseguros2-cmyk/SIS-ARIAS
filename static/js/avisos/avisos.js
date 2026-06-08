document.addEventListener('DOMContentLoaded', () => {
  window.currentPage = 'avisos';

  const btnSaveAndAdd = document.getElementById('btnSaveAndAdd');
  const btnSave = document.getElementById('btnSave');
  const fileInput = document.getElementById('documentoFile');
  const alertSuccess = document.getElementById('alertSuccess');
  const form = document.getElementById('addAvisoForm');
  
  const alertPageSuccess = document.getElementById('alertPageSuccess');
  
  // Elementos para actualizar la tabla (simulado)
  const tableBody = document.querySelector('.table-card tbody');

  function confirmModal(message) {
    return new Promise((resolve) => {
      const modalEl = document.getElementById('avisoConfirmModal');
      const msgEl = document.getElementById('avisoConfirmMessage');
      const okBtn = document.getElementById('btnAvisoConfirmOk');
      const cancelBtn = document.getElementById('btnAvisoConfirmCancel');
      if (!modalEl || !msgEl || !okBtn || !cancelBtn || typeof bootstrap === 'undefined') {
        resolve(window.confirm(message));
        return;
      }

      msgEl.textContent = message;
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

      const cleanup = () => {
        okBtn.removeEventListener('click', onOk);
        cancelBtn.removeEventListener('click', onCancel);
        modalEl.removeEventListener('hidden.bs.modal', onHidden);
      };

      const onOk = () => {
        cleanup();
        try { modal.hide(); } catch (_) {}
        resolve(true);
      };

      const onCancel = () => {
        cleanup();
        resolve(false);
      };

      const onHidden = () => {
        cleanup();
        resolve(false);
      };

      okBtn.addEventListener('click', onOk, { once: true });
      cancelBtn.addEventListener('click', onCancel, { once: true });
      modalEl.addEventListener('hidden.bs.modal', onHidden, { once: true });
      modal.show();
    });
  }

  // Función para obtener la alerta de Bootstrap o inicializarla (MODAL)
  const showAlert = () => {
    alertSuccess.classList.remove('d-none');
    // Scroll to top of modal to ensure alert is visible
    const modalBody = document.querySelector('.modal-body');
    if(modalBody) modalBody.scrollTop = 0;
  };

  // Función para mostrar la alerta de página
  const showPageAlert = () => {
      if (alertPageSuccess) {
          alertPageSuccess.classList.remove('d-none');
          window.scrollTo(0, 0); // Scroll to top
      }
  };

  // Manejar cierre manual de la alerta DEL MODAL
  const btnCloseAlert = alertSuccess.querySelector('.btn-close');
  if (btnCloseAlert) {
      btnCloseAlert.addEventListener('click', () => {
          alertSuccess.classList.add('d-none');
      });
  }

  // Manejar cierre manual de la alerta DE LA PÁGINA
  if (alertPageSuccess) {
      const btnClosePageAlert = alertPageSuccess.querySelector('.btn-close');
      if (btnClosePageAlert) {
          btnClosePageAlert.addEventListener('click', () => {
              alertPageSuccess.classList.add('d-none');
          });
      }
  }

  // Resetear modal al abrirse
  const addAvisoModal = document.getElementById('addAvisoModal');
  if (addAvisoModal) {
      addAvisoModal.addEventListener('show.bs.modal', () => {
          // Ocultar alerta del modal
          alertSuccess.classList.add('d-none');
          // Resetear formulario
          if(form) form.reset();
          // Ocultar alerta de página si estuviera visible (opcional, pero limpio)
          if(alertPageSuccess) alertPageSuccess.classList.add('d-none');
      });
  }

  // Función real de guardado
  const saveDocument = (callback) => {
    if (!fileInput.files.length) {
      alert('Por favor selecciona un archivo.');
      return;
    }

    const file = fileInput.files[0];
    const n = (file && file.name) ? String(file.name).toLowerCase() : '';
    const detectCupon = (name) => {
      const s = String(name || '');
      let m = s.match(/\bC[-_ ]?(\d{6,20})\b/i);
      if (m) return m[1];
      m = s.match(/\bCUPON[-_ ]?(\d{6,20})\b/i);
      if (m) return m[1];
      return '';
    };
    const cupon = detectCupon(file.name);
    const isConvenio = (n.includes('convenio') || n.includes('cuponera') || n.includes('cronograma') || n.includes('plan_pago') || n.includes('plan de pago'));
    const isFactura = (n.includes('factura') || n.includes('recibo') || n.includes('boleta'));
    const tipoDocumento = isConvenio ? 'CONVENIO_PAGO' : (isFactura ? 'CUOTA' : 'ARCHIVO_EXTRA');
    const formData = new FormData();
    formData.append('archivo', file);
    formData.append('poliza_id', window.avisoId || '');
    formData.append('tipo_documento', tipoDocumento);
    if (tipoDocumento === 'CUOTA' && cupon) {
      formData.append('cupon', cupon);
    }
    formData.append('nombre_documento', file.name);
    
    // Mostrar estado de carga
    if(btnSaveAndAdd) btnSaveAndAdd.disabled = true;
    if(btnSave) btnSave.disabled = true;

    fetch('/api/polizas/upload-archivo', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (!data || data.ok !== true) {
            throw new Error((data && (data.error || data.errors?.[0])) || 'Error al subir el archivo');
        }
        return data;
    })
    .then(result => {
        console.log('Archivo guardado:', result.ruta);

        // Actualizar tabla si estaba vacía
        const emptyRow = tableBody.querySelector('tr td[colspan="2"]');
        if (emptyRow) {
            emptyRow.parentElement.remove();
        }

        // URL para ver/descargar (sirve el PDF desde uploads/)
        const downloadUrl = `/uploads/${result.ruta}`;

        // Añadir fila a la tabla
        const nombreUi = (result.nombre || file.name);
        const safeName = (nombreUi || '').replace(/"/g, '&quot;');
        const newRow = `
            <tr>
              <td class="text-break text-muted small">${nombreUi}</td>
              <td class="text-end">
                <div class="action-buttons justify-content-end">
                  <a href="#" class="btn-action btn-danger btn-preview" data-url="${downloadUrl}" data-name="${safeName}" title="Ver">Ver</a>
                  <button class="btn-action btn-primary btn-detalles" data-id="${window.avisoId || ''}" title="Detalles">Detalles</button>
                  <button class="btn-action btn-success btn-editar" data-id="${window.avisoId || ''}" title="Editar">Editar</button>
                  <button class="btn-action btn-danger btn-delete-document" data-archivo-id="${result.idArchivo || ''}" title="Eliminar">Eliminar</button>
                </div>
              </td>
            </tr>
        `;
        tableBody.insertAdjacentHTML('beforeend', newRow);

        // Actualizar contador
        const totalCountEl = document.getElementById('totalRecordsCount');
        if (totalCountEl) {
             const rowCount = tableBody.querySelectorAll('tr').length;
             totalCountEl.innerText = `Total de registros: ${rowCount}`;
        }

        // Limpiar formulario
        form.reset();
        
        if (callback) callback();
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al guardar: ' + error.message);
    })
    .finally(() => {
        if(btnSaveAndAdd) btnSaveAndAdd.disabled = false;
        if(btnSave) btnSave.disabled = false;
    });
  };

  if (btnSaveAndAdd) {
    btnSaveAndAdd.addEventListener('click', () => {
      saveDocument(() => {
        // Mostrar alerta de éxito
        showAlert();
        // El modal permanece abierto
      });
    });
  }

  if (btnSave) {
    btnSave.addEventListener('click', () => {
      saveDocument(() => {
        // Cerrar modal
        const modalEl = document.getElementById('addAvisoModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        modal.hide();
        
        // Mostrar alerta de éxito en la página
        showPageAlert();
      });
    });
  }

  // Event Delegation para Previsualizar Documento
  document.addEventListener('click', async (e) => {
      const btnPreview = e.target.closest('.btn-preview');
      if (btnPreview) {
          e.preventDefault();
          const url = btnPreview.getAttribute('data-url') || btnPreview.getAttribute('href');
          const name = btnPreview.getAttribute('data-name') || '';
          if (url && url !== '#') {
              const modalEl = document.getElementById('viewDocumentModal');
              const iframe = document.getElementById('documentPreviewFrame');
              const nameEl = document.getElementById('documentPreviewName');
              try {
                  const resp = await fetch(url, { headers: { Range: 'bytes=0-0' } });
                  if (!resp.ok) throw new Error('Archivo no encontrado');
                  const ct = (resp.headers.get('content-type') || '').toLowerCase();
                  if (!ct.includes('pdf') && !ct.startsWith('image/')) throw new Error('Formato no soportado');
                  if (modalEl && iframe) {
                      if (nameEl) nameEl.textContent = name;
                      const viewerUrl = ct.includes('pdf') && !url.includes('#')
                        ? `${url}#toolbar=1&navpanes=1&scrollbar=1`
                        : url;
                      iframe.src = viewerUrl;
                      if (typeof bootstrap !== 'undefined') {
                          let modal = bootstrap.Modal.getInstance(modalEl);
                          if (!modal) modal = new bootstrap.Modal(modalEl);
                          modal.show();
                      }
                  }
              } catch (err) {
                  alert((err && err.message) ? err.message : 'No se pudo abrir el documento');
              }
          }
      }

      const btnDelete = e.target.closest('.btn-delete-document');
      if (btnDelete) {
        e.preventDefault();
        const archivoId = btnDelete.getAttribute('data-archivo-id');
        if (!archivoId) return;
        const ok = await confirmModal('¿Estás seguro de eliminar este documento permanentemente?');
        if (!ok) return;

        const originalHtml = btnDelete.innerHTML;
        btnDelete.disabled = true;
        btnDelete.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        try {
          const resp = await fetch(`/api/polizas/archivos/delete/${archivoId}`, { method: 'DELETE', credentials: 'same-origin' });
          const data = await resp.json().catch(() => ({}));
          if (!resp.ok || !data.ok) throw new Error(data.error || 'Error al eliminar');

          const row = btnDelete.closest('tr');
          if (row) row.remove();
          const item = btnDelete.closest('.mb-2');
          if (!row && item) item.remove();

          const tb = document.querySelector('.table-card tbody');
          if (tb) {
            const rows = tb.querySelectorAll('tr');
            const empty = tb.querySelector('tr td[colspan="2"]');
            const count = empty ? 0 : rows.length;
            const totalCountEl = document.getElementById('totalRecordsCount');
            if (totalCountEl) totalCountEl.innerText = `Total de registros: ${count}`;
            if (count === 0 && !empty) {
              tb.innerHTML = '<tr><td colspan="2" class="text-center text-muted py-4">Sin documentos</td></tr>';
            }
          }
        } catch (err) {
          alert((err && err.message) ? err.message : 'Error al eliminar');
          btnDelete.disabled = false;
          btnDelete.innerHTML = originalHtml;
        }
      }
  });

  const viewDocumentModal = document.getElementById('viewDocumentModal');
  if (viewDocumentModal) {
      viewDocumentModal.addEventListener('hidden.bs.modal', () => {
          const iframe = document.getElementById('documentPreviewFrame');
          if (iframe) iframe.src = '';
          const nameEl = document.getElementById('documentPreviewName');
          if (nameEl) nameEl.textContent = '';
      });
  }
});
