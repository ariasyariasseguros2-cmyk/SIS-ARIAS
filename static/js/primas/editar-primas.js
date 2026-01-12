document.addEventListener('DOMContentLoaded', () => {
    const btnGuardar = document.getElementById('btnGuardar');
    if (btnGuardar) {
        btnGuardar.addEventListener('click', async (e) => {
            e.preventDefault();
            
            // Collect form data
            const data = {
                idPrima: document.getElementById('idPrima').value,
                tipo_doc: document.getElementById('tipoDoc').value,
                contratante: document.getElementById('contratante').value,
                cia: document.getElementById('compania').value,
                ramo: document.getElementById('ramoProducto').value,
                vig_desde: document.getElementById('vigenciaInicio').value,
                vig_hasta: document.getElementById('vigenciaFin').value,
                tipo_pago: document.getElementById('tipoPago').value,
                moneda: document.getElementById('moneda').value,
                prima_comercial: document.getElementById('primaComercial').value,
                prima_neta: document.getElementById('primaNeta').value,
                prima_comercial_igv: document.getElementById('primaTotal').value,
                motivo: document.getElementById('motivo').value,
                nro_operacion: document.getElementById('nroOperacion').value,
                porc_compania: document.getElementById('comisionCompania').value,
                imp_compania: document.getElementById('importeComisionCompania').value,
                sub_agente: document.getElementById('subAgente').value,
                porc_subagente: document.getElementById('comisionSubAgente').value,
                imp_subagente: document.getElementById('importeComisionSubAgente').value,
                recibo: document.getElementById('numPrimeraCuota').value,
                mas_informacion: document.getElementById('masInformacion').value
            };

            // Basic validation
            if (!data.prima_neta || !data.prima_comercial_igv) {
                Swal.fire('Atención', 'Por favor complete los campos obligatorios (Primas)', 'warning');
                return;
            }

            try {
                // Show loading state
                btnGuardar.disabled = true;
                btnGuardar.textContent = 'Guardando...';

                // Assuming /primas/update endpoint exists
                const resp = await fetch('/primas/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const res = await resp.json();
                
                if (resp.ok && res.ok) {
                    Swal.fire('Guardado', 'Prima actualizada correctamente', 'success').then(() => {
                        window.location.href = '/menu/primas';
                    });
                } else {
                    Swal.fire('Error', res.error || 'No se pudo actualizar', 'error');
                    btnGuardar.disabled = false;
                    btnGuardar.textContent = 'Guardar';
                }
            } catch (e) {
                console.error(e);
                Swal.fire('Error', 'Error de red o endpoint no encontrado', 'error');
                btnGuardar.disabled = false;
                btnGuardar.textContent = 'Guardar';
            }
        });
    }
});
