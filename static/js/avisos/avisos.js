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

  // Función simulada de guardado
  const saveDocument = (callback) => {
    if (!fileInput.files.length) {
      alert('Por favor selecciona un archivo.');
      return;
    }

    const file = fileInput.files[0];
    
    // Aquí iría la lógica AJAX real para subir el archivo
    // Simulamos éxito
    console.log('Guardando archivo:', file.name);

    // Actualizar tabla si estaba vacía
    const emptyRow = tableBody.querySelector('tr td[colspan="2"]');
    if (emptyRow) {
        emptyRow.parentElement.remove();
    }

    // Añadir fila a la tabla (simulación visual)
    const newRow = `
        <tr>
          <td class="text-break text-muted small">${file.name}</td>
          <td class="text-end">
            <div class="action-buttons justify-content-end">
              <a href="#" class="btn-action btn-danger" title="Descargar">Descargar</a>
              <button class="btn-action btn-primary" title="Detalles">Detalles</button>
              <button class="btn-action btn-success" title="Editar">Editar</button>
              <button class="btn-action btn-warning" title="Eliminar">Eliminar</button>
            </div>
          </td>
        </tr>
    `;
    tableBody.insertAdjacentHTML('beforeend', newRow);

    // Limpiar formulario
    form.reset();
    
    if (callback) callback();
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
});