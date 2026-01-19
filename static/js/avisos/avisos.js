document.addEventListener('DOMContentLoaded', () => {
  window.currentPage = 'avisos';

  const btnSaveAndAdd = document.getElementById('btnSaveAndAdd');
  const btnSave = document.getElementById('btnSave');
  const fileInput = document.getElementById('documentoFile');
  const alertSuccess = document.getElementById('alertSuccess');
  const form = document.getElementById('addAvisoForm');
  
  // Elementos para actualizar la tabla (simulado)
  const tableBody = document.querySelector('.avisos-table-card tbody');

  // Función para obtener la alerta de Bootstrap o inicializarla
  const showAlert = () => {
    alertSuccess.classList.remove('d-none');
    // Scroll to top of modal to ensure alert is visible
    const modalBody = document.querySelector('.modal-body');
    if(modalBody) modalBody.scrollTop = 0;
    
    // Auto ocultar después de 3 segundos
    setTimeout(() => {
        alertSuccess.classList.add('d-none');
    }, 3000);
  };

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
            <div class="d-flex gap-1 justify-content-end">
              <a href="#" class="btn btn-danger btn-sm text-white" title="Descargar"><i class="bi bi-download"></i> Descargar</a>
              <button class="btn btn-primary btn-sm" title="Detalles"><i class="bi bi-eye"></i> Detalles</button>
              <button class="btn btn-success btn-sm" title="Editar"><i class="bi bi-pencil"></i> Editar</button>
              <button class="btn btn-warning btn-sm text-white" title="Eliminar"><i class="bi bi-trash"></i> Eliminar</button>
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
        
        // Mostrar alerta de éxito (opcional, aunque el usuario pidió cerrar y mostrar la tabla)
        // showAlert(); 
      });
    });
  }
});