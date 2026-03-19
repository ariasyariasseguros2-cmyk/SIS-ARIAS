window.initEditarPrimasLogic = function(isModal = false) {
    // Cálculo automático: Prima Neta = Prima Comercial / 1.03
    const txtPrimaComercial = document.getElementById('primaComercial');
    const txtPrimaNeta = document.getElementById('primaNeta');
    
    if (txtPrimaComercial && txtPrimaNeta) {
        // Obtenemos referencia al campo Prima Total / IGV si existe
        const txtPrimaTotal = document.getElementById('primaTotal');
        // Referencias para Comisión Compañía
        const txtPorcCompania = document.getElementById('comisionCompania');
        const txtImpCompania = document.getElementById('importeComisionCompania');
        // Referencias para Comisión Sub Agente
        const txtPorcSubAgente = document.getElementById('comisionSubAgente');
        const txtImpSubAgente = document.getElementById('importeComisionSubAgente');

        // Lógica para cambio de símbolo de moneda
        const selectMoneda = document.getElementById('moneda');
        const updateCurrencySymbols = () => {
             if (!selectMoneda) return;
             const moneda = selectMoneda.value;
             let symbol = '$';
             if (moneda === 'S/.' || moneda === 'SOLES' || moneda === 'PEN') {
                 symbol = 'S/.';
             }
             document.querySelectorAll('.currency-symbol').forEach(el => el.textContent = symbol);
        };
        
        if (selectMoneda) {
             selectMoneda.addEventListener('change', updateCurrencySymbols);
             // Llamada inicial
             updateCurrencySymbols();
        }

        // Función auxiliar para calcular importe comisión sub agente
        const updateImporteSubAgente = () => {
            if (!txtPorcSubAgente || !txtImpSubAgente || !txtImpCompania) return;
            const impCia = parseFloat(txtImpCompania.value);
            const porc = parseFloat(txtPorcSubAgente.value);
            if (!isNaN(impCia) && !isNaN(porc)) {
                // Imp. Comisión Sub Agente = Imp. Comisión Cía * (% SubAgente / 100)
                txtImpSubAgente.value = (impCia * (porc / 100)).toFixed(2);
            } else {
                txtImpSubAgente.value = '';
            }
        };

        // Función auxiliar para calcular importe comisión cía
        const updateImporteCompania = () => {
            if (!txtPorcCompania || !txtImpCompania) return;
            const neta = parseFloat(txtPrimaNeta.value);
            const porc = parseFloat(txtPorcCompania.value);
            if (!isNaN(neta) && !isNaN(porc)) {
                txtImpCompania.value = (neta * (porc / 100)).toFixed(2);
                // Si cambia importe Cía, recalcular sub agente
                updateImporteSubAgente();
            } else {
                txtImpCompania.value = '';
                if (txtImpSubAgente) txtImpSubAgente.value = '';
            }
        };

        // Función para actualizar TODO basado en Prima Comercial
        const updateFromComercial = () => {
            if (document.activeElement !== txtPrimaComercial) return;
            const val = parseFloat(txtPrimaComercial.value);
            if (!isNaN(val) && val !== 0) {
                // Prima Neta = Comercial / 1.03
                txtPrimaNeta.value = (val / 1.03).toFixed(2);
                // Prima Total = Comercial * 1.18
                if (txtPrimaTotal) txtPrimaTotal.value = (val * 1.18).toFixed(2);
                // Actualizar comisión
                updateImporteCompania();
            } else {
                txtPrimaNeta.value = '';
                if (txtPrimaTotal) txtPrimaTotal.value = '';
                if (txtImpCompania) txtImpCompania.value = '';
                if (txtImpSubAgente) txtImpSubAgente.value = '';
            }
        };

        // Función para actualizar TODO basado en Prima Neta
        const updateFromNeta = () => {
            if (document.activeElement !== txtPrimaNeta) return;
            const val = parseFloat(txtPrimaNeta.value);
            if (!isNaN(val) && val !== 0) {
                // Prima Comercial = Neta * 1.03
                const comercial = val * 1.03;
                txtPrimaComercial.value = comercial.toFixed(2);
                // Prima Total = Comercial * 1.18
                if (txtPrimaTotal) txtPrimaTotal.value = (comercial * 1.18).toFixed(2);
                // Actualizar comisión
                updateImporteCompania();
            } else {
                txtPrimaComercial.value = '';
                if (txtPrimaTotal) txtPrimaTotal.value = '';
                if (txtImpCompania) txtImpCompania.value = '';
                if (txtImpSubAgente) txtImpSubAgente.value = '';
            }
        };

        // Asignar eventos a AMBOS inputs
        txtPrimaComercial.addEventListener('input', updateFromComercial);
        txtPrimaNeta.addEventListener('input', updateFromNeta);
        
        if (txtPorcCompania) {
            txtPorcCompania.addEventListener('input', updateImporteCompania);
        }
        
        if (txtPorcSubAgente) {
            txtPorcSubAgente.addEventListener('input', updateImporteSubAgente);
        }

        // Limpieza bidireccional (cuando se borra manualmente)
        txtPrimaComercial.addEventListener('keyup', function() {
             if (this.value.trim() === '') {    
                 txtPrimaNeta.value = '';
                 if (txtPrimaTotal) txtPrimaTotal.value = '';
                 if (txtImpCompania) txtImpCompania.value = '';
                 if (txtImpSubAgente) txtImpSubAgente.value = '';
             }
        });
        txtPrimaNeta.addEventListener('keyup', function() {
             if (this.value.trim() === '') {
                 txtPrimaComercial.value = '';
                 if (txtPrimaTotal) txtPrimaTotal.value = '';
                 if (txtImpCompania) txtImpCompania.value = '';
                 if (txtImpSubAgente) txtImpSubAgente.value = '';
             }
        });
    }

    const btnGuardar = document.getElementById('btnGuardar');
    if (btnGuardar) {
        // Remove existing listeners to avoid duplicates if re-initialized?
        // Cloning the node is a trick to remove listeners
        const newBtn = btnGuardar.cloneNode(true);
        btnGuardar.parentNode.replaceChild(newBtn, btnGuardar);
        
        newBtn.addEventListener('click', async (e) => {
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
                // motivo: document.getElementById('motivo').value, // comentado por solicitud
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
                newBtn.disabled = true;
                newBtn.textContent = 'Guardando...';

                // Assuming /primas/update endpoint exists
                const resp = await fetch('/primas/update', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                const res = await resp.json();
                
                if (resp.ok && res.ok) {
                    Swal.fire('Guardado', 'Prima actualizada correctamente', 'success').then(() => {
                        if (isModal) {
                            location.reload(); // Reload to see changes in table
                        } else {
                            window.location.href = '/menu/primas';
                        }
                    });
                } else {
                    Swal.fire('Error', res.error || 'No se pudo actualizar', 'error');
                    newBtn.disabled = false;
                    newBtn.textContent = 'Guardar';
                }
            } catch (e) {
                console.error(e);
                Swal.fire('Error', 'Error de red o endpoint no encontrado', 'error');
                newBtn.disabled = false;
                newBtn.textContent = 'Guardar';
            }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Auto-init for standalone page (non-modal)
    window.initEditarPrimasLogic(false);
});
