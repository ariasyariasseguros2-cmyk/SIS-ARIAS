window.initEditarPrimasLogic = function(isModal = false) {
    // Cálculo automático: Prima Neta = Prima Comercial / 1.03
    const txtPrimaComercial = document.getElementById('primaComercial');
    const txtPrimaNeta = document.getElementById('primaNeta');

    const getElValue = (el) => {
        if (!el) return '';
        if (el.type === 'checkbox') return el.checked ? '1' : '0';
        return (el.value ?? '').toString();
    };

    const parseNumber = (value) => {
        if (value === null || value === undefined) return null;
        const s = value.toString().replace(/,/g, '').trim();
        if (!s) return null;
        const n = Number(s);
        return Number.isFinite(n) ? n : null;
    };
    
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
             const moneda = (selectMoneda.value || '').trim();
             const monedaNorm = moneda.toUpperCase();
             let symbol = 'US$';
             if (monedaNorm === 'S/' || monedaNorm === 'S/.' || monedaNorm === 'SOLES' || monedaNorm === 'PEN') {
                 symbol = 'S/';
             } else if (monedaNorm === 'US$' || monedaNorm === 'USD' || monedaNorm === 'DOLARES' || monedaNorm === '$') {
                 symbol = 'US$';
             }
             document.querySelectorAll('.currency-symbol').forEach(el => el.textContent = symbol);
        };
        
        if (selectMoneda) {
             selectMoneda.addEventListener('change', updateCurrencySymbols);
             // Llamada inicial
             updateCurrencySymbols();
        }

        // Lógica para filtrar productos por ramo
        const selectRamo = document.getElementById('ramo');
        const selectProducto = document.getElementById('ramosProducto');
        
        if (selectRamo && selectProducto) {
            const sortSelect = (select) => {
                const options = Array.from(select.options);
                const firstOption = options.shift(); // Preservar "Selecciona..."
                options.sort((a, b) => a.text.localeCompare(b.text));
                select.innerHTML = '';
                if (firstOption) select.appendChild(firstOption);
                options.forEach(opt => select.appendChild(opt));
            };

            const filterProducts = () => {
                const selectedRamo = selectRamo.value;
                const options = selectProducto.querySelectorAll('option');
                
                options.forEach(opt => {
                    if (opt.value === "") return;
                    const ramoOpt = opt.getAttribute('data-ramo');
                    if (!selectedRamo || ramoOpt === selectedRamo) {
                        opt.style.display = "";
                    } else {
                        opt.style.display = "none";
                    }
                });
            };
            
            // Si el ramo es un select (no hidden), agregar listener
            if (selectRamo.tagName === 'SELECT') {
                 selectRamo.addEventListener('change', filterProducts);
                 sortSelect(selectRamo);
             }
             
             sortSelect(selectProducto);
             // Ejecutar al inicio por si ya viene con ramo seleccionado
             filterProducts();
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
            if (!isNaN(val)) {
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
            if (!isNaN(val)) {
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

        const btnTextDefault = (newBtn.textContent || '').trim() || 'Guardar';

        const trackedIds = [
            'tipoDoc',
            'contratante',
            'compania',
            'ramo',
            'ramosProducto',
            'vigenciaInicio',
            'vigenciaFin',
            'tipoPago',
            'moneda',
            'primaComercial',
            'primaNeta',
            'primaTotal',
            'comisionCompania',
            'importeComisionCompania',
            'subAgente',
            'comisionSubAgente',
            'importeComisionSubAgente',
            'nroOperacion',
            'numPrimeraCuota',
            'masInformacion'
        ];

        const getSnapshot = () => {
            const snap = {};
            for (const id of trackedIds) {
                const el = document.getElementById(id);
                if (!el) continue;
                snap[id] = getElValue(el).trim();
            }
            return snap;
        };

        const initialSnapshot = getSnapshot();

        const hasChanges = () => {
            const current = getSnapshot();
            const keys = new Set([...Object.keys(initialSnapshot), ...Object.keys(current)]);
            for (const k of keys) {
                const a = (initialSnapshot[k] ?? '').toString().trim();
                const b = (current[k] ?? '').toString().trim();
                if (a !== b) return true;
            }
            return false;
        };

        const primasChanged = () => {
            const a = parseNumber(initialSnapshot.primaComercial);
            const b = parseNumber(document.getElementById('primaComercial')?.value);
            const c = parseNumber(initialSnapshot.primaNeta);
            const d = parseNumber(document.getElementById('primaNeta')?.value);
            const e = parseNumber(initialSnapshot.primaTotal);
            const f = parseNumber(document.getElementById('primaTotal')?.value);

            const tol = 0.005;
            const diff = (x, y) => (x === null || y === null) ? false : Math.abs(x - y) >= tol;
            return diff(a, b) || diff(c, d) || diff(e, f);
        };

        const refreshBtnState = () => {
            const dirty = hasChanges();
            newBtn.disabled = !dirty;
            if (!dirty) {
                newBtn.textContent = btnTextDefault;
            }
        };

        refreshBtnState();

        for (const id of trackedIds) {
            const el = document.getElementById(id);
            if (!el) continue;
            el.addEventListener('input', refreshBtnState);
            el.addEventListener('change', refreshBtnState);
        }
        
        newBtn.addEventListener('click', async (e) => {
            e.preventDefault();

            if (newBtn.disabled) return;
            
            // Collect form data
            const data = {
                idPrima: document.getElementById('idPrima').value,
                poliza: document.getElementById('polizaNumero')?.value || '',
                tipo_doc: document.getElementById('tipoDoc').value,
                cliente_id: document.getElementById('contratante').value,
                contratante: document.getElementById('contratante').options[document.getElementById('contratante').selectedIndex]?.text || '',
                cia: document.getElementById('compania').value,
                ramo: document.getElementById('ramo').value,
                ramos_producto: document.getElementById('ramosProducto').value,
                vig_desde: document.getElementById('vigenciaInicio').value,
                vig_hasta: document.getElementById('vigenciaFin').value,
                tipo_pago: document.getElementById('tipoPago').value,
                moneda: document.getElementById('moneda').value,
                prima_comercial: document.getElementById('primaComercial').value,
                prima_neta: document.getElementById('primaNeta').value,
                prima_comercial_igv: document.getElementById('primaTotal').value,
                // motivo: document.getElementById('motivo').value, // comentado por solicitud
                porc_compania: document.getElementById('comisionCompania').value,
                imp_compania: document.getElementById('importeComisionCompania').value,
                sub_agente: document.getElementById('subAgente').value,
                porc_subagente: document.getElementById('comisionSubAgente').value,
                imp_subagente: document.getElementById('importeComisionSubAgente').value,
                recibo: document.getElementById('numPrimeraCuota').value,
                mas_informacion: document.getElementById('masInformacion').value
            };
            const nroOperacion = document.getElementById('nroOperacion')?.value?.trim();
            if (nroOperacion) { 
                data.nro_operacion = nroOperacion;
            }

            data.update_cuotas = primasChanged();

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
                    newBtn.textContent = btnTextDefault;
                    refreshBtnState();
                }
            } catch (e) {
                console.error(e);
                Swal.fire('Error', 'Error de red o endpoint no encontrado', 'error');
                newBtn.textContent = btnTextDefault;
                refreshBtnState();
            }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    // Auto-init for standalone page (non-modal)
    window.initEditarPrimasLogic(false);
});
