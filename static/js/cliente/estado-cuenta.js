// Estado de Cuenta - Cliente Search and Filters
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] Estado Cuenta JS cargado');

    const clienteSearchInput = document.getElementById('clienteSearchInput');
    const clienteIdInput = document.getElementById('clienteIdInput');
    const clienteSearchResults = document.getElementById('clienteSearchResults');
    const filtrosForm = document.getElementById('filtrosForm');

    console.log('[DEBUG] Elementos encontrados:', {
        clienteSearchInput: !!clienteSearchInput,
        clienteIdInput: !!clienteIdInput,
        clienteSearchResults: !!clienteSearchResults,
        filtrosForm: !!filtrosForm
    });

    let searchTimeout = null;

    // Verificar que el formulario se envíe correctamente
    if (filtrosForm) {
        filtrosForm.addEventListener('submit', function() {
            console.log('[DEBUG] Formulario enviado');
            const clienteId = clienteIdInput ? clienteIdInput.value : '';
            console.log('[DEBUG] Cliente ID:', clienteId);

            if (!clienteId) {
                console.warn('[DEBUG] No hay cliente seleccionado');
                // No prevenir el envío, dejar que se procese en el servidor
            }
        });
    }

    // Búsqueda automática al escribir
    if (clienteSearchInput) {
        clienteSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            console.log('[DEBUG] Input cambió:', query);

            if (query.length < 2) {
                clienteSearchResults.style.display = 'none';
                clienteSearchResults.innerHTML = '';
                return;
            }

            searchTimeout = setTimeout(() => {
                buscarClientes(query);
            }, 500);
        });

        // Cerrar resultados al hacer clic fuera
        document.addEventListener('click', function(e) {
            if (!clienteSearchInput.contains(e.target) && !clienteSearchResults.contains(e.target)) {
                clienteSearchResults.style.display = 'none';
            }
        });
    }

    // Función para buscar clientes
    function buscarClientes(query) {
        console.log('[DEBUG] Buscando clientes con query:', query);
        fetch(`/api/clientes/buscar?q=${encodeURIComponent(query)}`)
            .then(response => {
                console.log('[DEBUG] Response status:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('[DEBUG] Data recibida:', data);
                if (data.ok && data.clientes && data.clientes.length > 0) {
                    mostrarResultados(data.clientes);
                } else {
                    clienteSearchResults.innerHTML = '<div class="list-group-item text-muted">No se encontraron resultados</div>';
                    clienteSearchResults.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('[ERROR] Error al buscar clientes:', error);
                clienteSearchResults.innerHTML = '<div class="list-group-item text-danger">Error al buscar</div>';
                clienteSearchResults.style.display = 'block';
            });
    }

    // Mostrar resultados de búsqueda
    function mostrarResultados(clientes) {
        console.log('[DEBUG] Mostrando', clientes.length, 'resultados');
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
        console.log('[DEBUG] Cliente seleccionado:', cliente);
        clienteSearchInput.value = cliente.razon_social;
        clienteIdInput.value = cliente.idCliente;

        // También llenar el número de documento si está vacío
        const numeroDocInput = document.querySelector('input[name="numero_documento"]');
        const tipoDocSelect = document.querySelector('select[name="tipo_documento"]');

        if (numeroDocInput && !numeroDocInput.value) {
            numeroDocInput.value = cliente.numero_documento;
        }

        if (tipoDocSelect && !tipoDocSelect.value) {
            tipoDocSelect.value = cliente.tipo_documento;
        }

        clienteSearchResults.style.display = 'none';
        clienteSearchResults.innerHTML = '';

        console.log('[DEBUG] Cliente ID guardado:', clienteIdInput.value);
    }

    // Limpiar cliente_id si se modifica manualmente el campo de búsqueda
    if (clienteSearchInput) {
        clienteSearchInput.addEventListener('keypress', function() {
            if (clienteIdInput.value) {
                // Solo limpiar si el usuario está escribiendo algo diferente
                setTimeout(() => {
                    clienteIdInput.value = '';
                    console.log('[DEBUG] Cliente ID limpiado por edición manual');
                }, 100);
            }
        });
    }
});
