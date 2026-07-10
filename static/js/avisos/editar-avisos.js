
document.addEventListener('DOMContentLoaded', () => {
    console.log('Editar Avisos JS loaded');

    // Event Delegation para abrir el modal de edición y acciones dentro del modal
    document.addEventListener('click', async function(e) {
        
        // --- Abrir Modal de Edición ---
        const btnEditar = e.target.closest('.btn-editar');
        if (btnEditar) {
            const id = btnEditar.getAttribute('data-id');
            if (id) {
                const modalEl = document.getElementById('editarAvisosModal');
                if (typeof bootstrap !== 'undefined') {
                    let modal = bootstrap.Modal.getInstance(modalEl);
                    if (!modal) modal = new bootstrap.Modal(modalEl);
                    modal.show();

                    const modalBody = document.getElementById('editarAvisosModalBody');
                    modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div></div>';

                    fetch(`/menu/avisos-editar-form?id=${id}`)
                        .then(res => res.text())
                        .then(html => {
                            modalBody.innerHTML = html;
                        })
                        .catch(err => {
                            console.error(err);
                            modalBody.innerHTML = '<div class="alert alert-danger">Error al cargar el formulario</div>';
                        });
                }
            }
        }

        // --- Guardar Aviso (Upload/Update) ---
        const btnGuardar = e.target.closest('#btnGuardarAviso');
        if (btnGuardar) {
            e.preventDefault();
            const form = document.getElementById('editAvisosForm');
            if (!form) return;

            const fileInput = form.querySelector('input[type="file"]');
            const idInput = form.querySelector('input[name="id"]');
            const modalEl = document.getElementById('editarAvisosModal');
            
            // Caso 1: Se seleccionó un archivo nuevo
            if (fileInput && fileInput.files.length > 0) {
                 const file = fileInput.files[0];
                 const n = (file && file.name) ? String(file.name).toLowerCase() : '';
                 const isConvenio = (n.includes('convenio') || n.includes('cuponera') || n.includes('cronograma') || n.includes('plan_pago') || n.includes('plan de pago'));
                 const tipoDocumento = isConvenio ? 'CONVENIO_PAGO' : 'ARCHIVO_EXTRA';
                 const formData = new FormData();
                 formData.append('archivo', file);
                 formData.append('poliza_id', idInput ? idInput.value : '');
                 formData.append('tipo_documento', tipoDocumento);
                 formData.append('nombre_documento', file.name);
                 
                 // UI Loading state
                 const originalText = btnGuardar.innerHTML;
                 btnGuardar.disabled = true;
                 btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Guardando...';

                 fetch('/api/polizas/upload-archivo', { method: 'POST', body: formData, credentials: 'same-origin' })
                    .then(r => r.json())
                    .then(data => {
                        if (!data || data.ok !== true) throw new Error((data && data.error) || 'Error al guardar');
                        
                        // Success
                        alert('Aviso actualizado correctamente');
                        if(modalEl) {
                            const modal = bootstrap.Modal.getInstance(modalEl);
                            if(modal) modal.hide();
                        }
                        location.reload(); // Recargar para ver cambios
                    })
                    .catch(err => {
                        console.error(err);
                        alert('Error: ' + err.message);
                    })
                    .finally(() => {
                        btnGuardar.disabled = false;
                        btnGuardar.innerHTML = originalText;
                    });
            } else {
                // Caso 2: Solo guardar datos (si hubiera otros campos)
                // Por ahora solo hay archivo, así que si no hay archivo y no se borró, no hacemos nada o avisamos
                // Verificamos si hay intención de guardar cambios sin archivo (no aplica mucho aquí aun)
                alert('No se ha seleccionado ningún archivo nuevo.');
            }
        }

    });
});
