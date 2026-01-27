// Estado de Cuenta - Cliente Search and Filters
document.addEventListener('DOMContentLoaded', function() {

    const clienteSearchInput = document.getElementById('clienteSearchInput');
    const clienteIdInput = document.getElementById('clienteIdInput');
    const clienteSearchResults = document.getElementById('clienteSearchResults');
    const filtrosForm = document.getElementById('filtrosForm');

    const btnExportPdf = document.getElementById('btnExportPdf');
    const btnExportXlsx = document.getElementById('btnExportXlsx');

    let searchTimeout = null;

    // Serializa el formulario a query string
    function serializeFormToQuery() {
        const params = new URLSearchParams();
        if (!filtrosForm) return '';

        Array.from(filtrosForm.elements).forEach(el => {
            if (!el.name) return;
            if ((el.type === 'checkbox' || el.type === 'radio') && !el.checked) return;
            // Solo agregar si tiene valor
            if (el.value && el.value.trim() !== '') {
                params.append(el.name, el.value);
            }
        });

        return params.toString();
    }

    // Función de descarga
    function downloadExport(format) {
        try {
            const queryString = serializeFormToQuery();
            const url = `/clientes/estado-cuenta/export?format=${encodeURIComponent(format)}&${queryString}`;

            // Intentar abrir en nueva pestaña
            const newWindow = window.open(url, '_blank');

            if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
                console.warn('[WARN] Popup bloqueado, intentando descarga directa');
                // Fallback: usar un iframe oculto o redirigir
                window.location.href = url;
            } else {
            }
        } catch (err) {
            console.error('[ERROR] Error en downloadExport:', err);
            alert('Error al iniciar la descarga: ' + err.message);
        }
    }

    // Conectar botones de exportación
    if (btnExportPdf) {
        btnExportPdf.addEventListener('click', function(e) {
            e.preventDefault();
            downloadExport('pdf');
        });
    } else {
        console.warn('[WARN] No se encontró btnExportPdf');
    }

    if (btnExportXlsx) {
        btnExportXlsx.addEventListener('click', function(e) {
            e.preventDefault();
            downloadExport('xlsx');
        });
    } else {
        console.warn('[WARN] No se encontró btnExportXlsx');
    }

    // Verificar que el formulario se envíe correctamente
    if (filtrosForm) {
        filtrosForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Obtener el número de documento para la URL limpia
            const numeroDocInput = document.querySelector('input[name="numero_documento"]');
            const numeroDoc = numeroDocInput && numeroDocInput.value ? numeroDocInput.value.trim() : '';

            // Construir URL limpia (solo con número de documento, si existe)
            const cleanUrl = numeroDoc
                ? `${this.action}?numero_documento=${encodeURIComponent(numeroDoc)}`
                : this.action;


            // Enviar formulario vía POST usando fetch
            const formData = new FormData(this);

            fetch(this.action, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }
                return response.text();
            })
            .then(html => {
                // Reemplazar el contenido de la página con la respuesta
                document.open();
                document.write(html);
                document.close();

                // Cambiar la URL sin recargar (solo muestra número de documento)
                window.history.replaceState({}, '', cleanUrl);

            })
            .catch(error => {
                console.error('[ERROR] Error al enviar filtros:', error);
                alert('Error al aplicar filtros. Por favor, intenta nuevamente.');
            });
        });
    }

    // Búsqueda automática al escribir
    if (clienteSearchInput) {
        clienteSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length < 2) {
                if (clienteSearchResults) {
                    clienteSearchResults.style.display = 'none';
                    clienteSearchResults.innerHTML = '';
                }
                return;
            }

            searchTimeout = setTimeout(() => {
                buscarClientes(query);
            }, 500);
        });

        // Cerrar resultados al hacer clic fuera
        document.addEventListener('click', function(e) {
            if (clienteSearchResults && !clienteSearchInput.contains(e.target) && !clienteSearchResults.contains(e.target)) {
                clienteSearchResults.style.display = 'none';
            }
        });
    }

    // Función para buscar clientes
    function buscarClientes(query) {
        fetch(`/api/clientes/buscar?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.ok && data.clientes && data.clientes.length > 0) {
                    mostrarResultados(data.clientes);
                } else if (clienteSearchResults) {
                    clienteSearchResults.innerHTML = '<div class="list-group-item text-muted">No se encontraron resultados</div>';
                    clienteSearchResults.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('[ERROR] Error al buscar clientes:', error);
                if (clienteSearchResults) {
                    clienteSearchResults.innerHTML = '<div class="list-group-item text-danger">Error al buscar</div>';
                    clienteSearchResults.style.display = 'block';
                }
            });
    }

    // Mostrar resultados de búsqueda
    function mostrarResultados(clientes) {
        if (!clienteSearchResults) return;
        clienteSearchResults.innerHTML = '';

        clientes.forEach(cliente => {
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${cliente.razon_social}</h6>
                    <small>${cliente.tipo_documento}: ${cliente.numero_documento}</small>
                </div>
                ${cliente.email ? `<small class="text-muted">${cliente.email}</small>` : ''}
            `;

            item.addEventListener('click', function(e) {
                e.preventDefault();
                seleccionarCliente(cliente);
            });

            clienteSearchResults.appendChild(item);
        });

        clienteSearchResults.style.display = 'block';
    }

    // Seleccionar un cliente de los resultados
    function seleccionarCliente(cliente) {
        if (clienteSearchInput) clienteSearchInput.value = cliente.razon_social;
        if (clienteIdInput) clienteIdInput.value = cliente.idCliente;

        const numeroDocInput = document.querySelector('input[name="numero_documento"]');
        const tipoDocSelect = document.querySelector('select[name="tipo_documento"]');

        if (numeroDocInput && !numeroDocInput.value) numeroDocInput.value = cliente.numero_documento || '';
        if (tipoDocSelect && !tipoDocSelect.value) tipoDocSelect.value = cliente.tipo_documento || '';

        if (clienteSearchResults) {
            clienteSearchResults.style.display = 'none';
            clienteSearchResults.innerHTML = '';
        }

    }

    // Limpiar cliente_id si se modifica manualmente el campo de búsqueda
    if (clienteSearchInput) {
        clienteSearchInput.addEventListener('keypress', function() {
            if (clienteIdInput && clienteIdInput.value) {
                setTimeout(() => {
                    clienteIdInput.value = '';
                }, 100);
            }
        });
    }

});

