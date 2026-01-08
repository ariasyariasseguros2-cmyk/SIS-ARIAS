document.addEventListener('DOMContentLoaded', () => {
    console.log('editar-poliza.js loaded');
    const btnGuardar = document.getElementById('btnGuardar');
    if (btnGuardar) {
        console.log('Button btnGuardar found');
        btnGuardar.addEventListener('click', async (e) => {
            e.preventDefault();
            console.log('Button Guardar clicked');
            
            // Collect form data
            const data = {
                idPoliza: document.getElementById('idPoliza').value,
                poliza: document.getElementById('poliza').value,
                asegurado: document.getElementById('asegurado').value,
                sub_agente: document.getElementById('subAgente').value,
                cia: document.getElementById('compania').value,
                ramo: document.getElementById('ramo').value,
                ramos_producto: document.getElementById('producto').value,
                porc_compania: document.getElementById('comisionCompania').value,
                porc_subagente: document.getElementById('comisionSubAgente').value,
                motivo: document.getElementById('tipoVigencia').value,
                vig_desde: document.getElementById('vigenciaInicio').value,
                vig_hasta: document.getElementById('vigenciaFin').value,
                moneda: document.getElementById('moneda').value,
                asegurada: document.getElementById('descripcion').value,
                ejecutivo: document.getElementById('ejecutivoCuenta').value,
                observacion: document.getElementById('masInformacion').value
            };

            // Basic validation
            if (!data.poliza || !data.cia || !data.ramo) {
                Swal.fire('Atención', 'Por favor complete los campos obligatorios (Póliza, Compañía, Ramo)', 'warning');
                return;
            }

            try {
                // Show loading state
                btnGuardar.disabled = true;
                btnGuardar.textContent = 'Guardando...';

                const resp = await fetch('/polizas/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const res = await resp.json();
                
                if (resp.ok && res.ok) {
                    Swal.fire('Guardado', 'Póliza actualizada correctamente', 'success').then(() => {
                        window.location.href = '/menu/listado-poliza';
                    });
                } else {
                    Swal.fire('Error', res.error || 'No se pudo actualizar', 'error');
                    btnGuardar.disabled = false;
                    btnGuardar.textContent = 'Guardar';
                }
            } catch (e) {
                console.error(e);
                Swal.fire('Error', 'Error de red', 'error');
                btnGuardar.disabled = false;
                btnGuardar.textContent = 'Guardar';
            }
        });
    }
});
