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
    const formData = new FormData();
    formData.append('file', file);
    
    // Mostrar estado de carga
    if(btnSaveAndAdd) btnSaveAndAdd.disabled = true;
    if(btnSave) btnSave.disabled = true;

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        const filename = data.filename;
        const pdfUrl = `polizas/${filename}`;
        
        // Ahora actualizamos la póliza/aviso con el pdf_url
        // Usamos /primas/update que reutiliza la lógica de pólizas
        return fetch('/primas/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                idPrima: window.avisoId,
                pdf_url: pdfUrl
            })
        }).then(res => res.json().then(r => ({ ...r, filename })));
    })
    .then(result => {
        if (!result.ok) {
            throw new Error(result.error || 'Error al actualizar el registro');
        }
        
        console.log('Archivo guardado y registro actualizado:', result.filename);

        // Actualizar tabla si estaba vacía
        const emptyRow = tableBody.querySelector('tr td[colspan="2"]');
        if (emptyRow) {
            emptyRow.parentElement.remove();
        }

        // URL de descarga
        const downloadUrl = `/uploads/polizas/${result.filename}`;

        // Añadir fila a la tabla
        const newRow = `
            <tr>
              <td class="text-break text-muted small">${file.name}</td>
              <td class="text-end">
                <div class="action-buttons justify-content-end">
                  <a href="#" class="btn-action btn-danger btn-preview" data-url="${downloadUrl}" title="Descargar">Descargar</a>
                  <button class="btn-action btn-primary btn-detalles" data-id="${window.avisoId || ''}" title="Detalles">Detalles</button>
                  <button class="btn-action btn-success btn-editar" data-id="${window.avisoId || ''}" title="Editar">Editar</button>
                  <button class="btn-action btn-warning btn-delete-document" data-id="${window.avisoId || ''}" title="Eliminar">Eliminar</button>
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
  document.addEventListener('click', (e) => {
      const btnPreview = e.target.closest('.btn-preview');
      if (btnPreview) {
          e.preventDefault();
          const url = btnPreview.getAttribute('data-url') || btnPreview.getAttribute('href');
          if (url && url !== '#') {
              const modalEl = document.getElementById('viewDocumentModal');
              const iframe = document.getElementById('documentPreviewFrame');
              if (modalEl && iframe) {
                  iframe.src = url;
                  if (typeof bootstrap !== 'undefined') {
                      let modal = bootstrap.Modal.getInstance(modalEl);
                      if (!modal) modal = new bootstrap.Modal(modalEl);
                      modal.show();
                  }
              }
          }
      }
  });
});