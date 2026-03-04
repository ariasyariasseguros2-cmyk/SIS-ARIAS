document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.getElementById('filterForm');
    const tableBody = document.querySelector('#resultsTable tbody');
    
    // Custom Dropdown Elements (Usuarios)
    const usuarioDropdownMenu = document.getElementById('usuarioDropdownMenu');
    const usuarioDropdownBtn = document.getElementById('usuarioDropdownBtn');
    const usuarioValue = document.getElementById('usuarioValue');

    // Custom Dropdown Elements (Ramos)
    const ramoDropdownMenu = document.getElementById('ramoDropdownMenu');
    const ramoDropdownBtn = document.getElementById('ramoDropdownBtn');
    const ramoValue = document.getElementById('ramoValue');

    // Load users and ramos on init
    loadUsuarios();
    loadRamos();

    // Listen for Cuota Saved event (from Modal)
    document.addEventListener('cuota:saved', function(e) {
        // Refresh the table maintaining current filters
        if (filterForm) {
            filterForm.dispatchEvent(new Event('submit'));
        }
    });

    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get selected value (comma separated from hidden input)
            const usuarios = usuarioValue ? usuarioValue.value : '';
            const ramos = ramoValue ? ramoValue.value : '';
            
            const estado = document.getElementById('estadoSelect').value;
            const fechaDesde = document.getElementById('fechaDesde').value;
            const fechaHasta = document.getElementById('fechaHasta').value;

            fetchData(usuarios, estado, fechaDesde, fechaHasta, ramos);
        });
    }

    // --- USUARIOS LOGIC ---
    async function loadUsuarios() {
        if (!usuarioDropdownMenu) return;
        try {
            const response = await fetch('/api/reportes/usuarios');
            const users = await response.json();
            
            usuarioDropdownMenu.innerHTML = '';

            // Search Input
            const liSearch = document.createElement('li');
            liSearch.className = 'dropdown-search-container';
            liSearch.innerHTML = `
                <input type="text" class="form-control form-control-sm" id="usuarioSearchInput" placeholder="Buscar usuario...">
            `;
            usuarioDropdownMenu.appendChild(liSearch);
            
            // "Todos" option
            const liTodos = document.createElement('li');
            liTodos.innerHTML = `
                <div class="dropdown-item">
                    <div class="form-check">
                        <input class="form-check-input usuario-checkbox" type="checkbox" value="" id="user_todos">
                        <label class="form-check-label w-100 fw-bold" style="cursor: pointer;" for="user_todos">Todos</label>
                    </div>
                </div>
            `;
            usuarioDropdownMenu.appendChild(liTodos);

            // Divider
            const liDivider = document.createElement('li');
            liDivider.innerHTML = '<hr class="dropdown-divider">';
            usuarioDropdownMenu.appendChild(liDivider);

            // Get current user from data attribute
            let currentUser = filterForm.getAttribute('data-current-user') || '';
            currentUser = currentUser.trim().toLowerCase();

            users.forEach(u => {
                const li = document.createElement('li');
                const isChecked = currentUser && u.username.toLowerCase() === currentUser;
                li.innerHTML = `
                    <div class="dropdown-item">
                        <div class="form-check">
                            <input class="form-check-input usuario-checkbox" type="checkbox" value="${u.username}" id="user_${u.username}" ${isChecked ? 'checked' : ''}>
                            <label class="form-check-label w-100" style="cursor: pointer;" for="user_${u.username}">${u.username}</label>
                        </div>
                    </div>
                `;
                usuarioDropdownMenu.appendChild(li);
            });

            // Add event listeners to all checkboxes
            const checkboxes = usuarioDropdownMenu.querySelectorAll('.usuario-checkbox');
            checkboxes.forEach(chk => {
                chk.addEventListener('change', handleUsuarioCheckboxChange);
                chk.closest('.dropdown-item').addEventListener('click', (e) => e.stopPropagation());
            });

            // Search functionality
            const searchInput = liSearch.querySelector('input');
            searchInput.addEventListener('click', (e) => e.stopPropagation()); // Prevent close
            searchInput.addEventListener('input', function(e) {
                const filter = e.target.value.toLowerCase();
                const items = usuarioDropdownMenu.querySelectorAll('li:not(.dropdown-search-container)');
                
                items.forEach(item => {
                    const label = item.querySelector('label');
                    if (label) {
                        const text = label.textContent.toLowerCase();
                        if (text.includes('Todos') || text.includes(filter)) {
                             item.style.display = '';
                        } else {
                             item.style.display = 'none';
                        }
                    }
                    // Keep dividers visible? Or hide if previous hidden? 
                    // Simplifying: keep dividers always visible or hide if they are adjacent to hidden?
                    // Let's just filter items with labels. Dividers might look weird if everything filtered.
                    // But "Todos" is always visible by the logic above (includes 'Todos').
                });
            });

            updateUsuarioDropdownState();

        } catch (error) {
            console.error('Error loading users:', error);
            if (usuarioDropdownBtn) usuarioDropdownBtn.textContent = 'Error cargando';
        }
    }

    function handleUsuarioCheckboxChange(e) {
        const target = e.target;
        const checkboxes = usuarioDropdownMenu.querySelectorAll('.usuario-checkbox');
        const todosCheckbox = document.getElementById('user_todos');

        if (target === todosCheckbox) {
            if (target.checked) {
                checkboxes.forEach(chk => { if (chk !== todosCheckbox) chk.checked = false; });
            }
        } else {
            if (target.checked && todosCheckbox) todosCheckbox.checked = false;
        }
        updateUsuarioDropdownState();
    }

    function updateUsuarioDropdownState() {
        const checkboxes = usuarioDropdownMenu.querySelectorAll('.usuario-checkbox:checked');
        const selectedValues = [];
        let todosChecked = false;

        checkboxes.forEach(chk => {
            if (chk.value === "") todosChecked = true;
            else selectedValues.push(chk.value);
        });

        // If nothing selected, revert to "Todos"
        const todosCheckbox = document.getElementById('user_todos');
        if (!todosChecked && selectedValues.length === 0) {
             if (todosCheckbox) todosCheckbox.checked = true;
             todosChecked = true;
        }

        if (todosChecked) usuarioValue.value = "";
        else usuarioValue.value = selectedValues.join(',');

        if (todosChecked) {
            usuarioDropdownBtn.textContent = "Todos";
            usuarioDropdownBtn.classList.remove('text-primary', 'fw-bold');
        } else {
            usuarioDropdownBtn.classList.add('text-primary', 'fw-bold');
            usuarioDropdownBtn.textContent = selectedValues.length === 1 ? selectedValues[0] : `${selectedValues.length} seleccionados`;
        }
    }

    // --- RAMOS LOGIC ---
    async function loadRamos() {
        if (!ramoDropdownMenu) return;
        try {
            const response = await fetch('/api/reportes/ramos');
            const ramos = await response.json();
            
            ramoDropdownMenu.innerHTML = '';
            
            // Search Input
            const liSearch = document.createElement('li');
            liSearch.className = 'dropdown-search-container';
            liSearch.innerHTML = `
                <input type="text" class="form-control form-control-sm" id="ramoSearchInput" placeholder="Buscar ramo...">
            `;
            ramoDropdownMenu.appendChild(liSearch);

            // "Todos" option
            const liTodos = document.createElement('li');
            liTodos.innerHTML = `
                <div class="dropdown-item">
                    <div class="form-check">
                        <input class="form-check-input ramo-checkbox" type="checkbox" value="" id="ramo_todos" checked>
                        <label class="form-check-label w-100 fw-bold" style="cursor: pointer;" for="ramo_todos">Todos los ramos</label>
                    </div>
                </div>
            `;
            ramoDropdownMenu.appendChild(liTodos);

            const liDivider = document.createElement('li');
            liDivider.innerHTML = '<hr class="dropdown-divider">';
            ramoDropdownMenu.appendChild(liDivider);

            ramos.forEach((r, index) => {
                const nombreRamo = r.nombre || r.abreviacion;
                const safeId = `ramo_${index}`; // Use index to avoid issues with spaces/special chars in IDs
                const li = document.createElement('li');
                li.innerHTML = `
                    <div class="dropdown-item">
                        <div class="form-check">
                            <input class="form-check-input ramo-checkbox" type="checkbox" value="${nombreRamo}" id="${safeId}">
                            <label class="form-check-label w-100" style="cursor: pointer;" for="${safeId}">${nombreRamo}</label>
                        </div>
                    </div>
                `;
                ramoDropdownMenu.appendChild(li);
            });

            const checkboxes = ramoDropdownMenu.querySelectorAll('.ramo-checkbox');
            checkboxes.forEach(chk => {
                chk.addEventListener('change', handleRamoCheckboxChange);
                chk.closest('.dropdown-item').addEventListener('click', (e) => e.stopPropagation());
            });

            // Search functionality
            const searchInput = liSearch.querySelector('input');
            searchInput.addEventListener('click', (e) => e.stopPropagation()); // Prevent close
            searchInput.addEventListener('input', function(e) {
                const filter = e.target.value.toLowerCase();
                const items = ramoDropdownMenu.querySelectorAll('li:not(.dropdown-search-container)');
                
                items.forEach(item => {
                    const label = item.querySelector('label');
                    if (label) {
                        const text = label.textContent.toLowerCase();
                        if (text.includes('todos') || text.includes(filter)) {
                             item.style.display = '';
                        } else {
                             item.style.display = 'none';
                        }
                    }
                });
            });

            updateRamoDropdownState();

        } catch (error) {
            console.error('Error loading ramos:', error);
            if (ramoDropdownBtn) ramoDropdownBtn.textContent = 'Error cargando';
        }
    }

    function handleRamoCheckboxChange(e) {
        const target = e.target;
        const checkboxes = ramoDropdownMenu.querySelectorAll('.ramo-checkbox');
        const todosCheckbox = document.getElementById('ramo_todos');

        if (target === todosCheckbox) {
            if (target.checked) {
                checkboxes.forEach(chk => { if (chk !== todosCheckbox) chk.checked = false; });
            }
        } else {
            if (target.checked && todosCheckbox) todosCheckbox.checked = false;
        }
        updateRamoDropdownState();
    }

    function updateRamoDropdownState() {
        const checkboxes = ramoDropdownMenu.querySelectorAll('.ramo-checkbox:checked');
        const selectedValues = [];
        let todosChecked = false;

        checkboxes.forEach(chk => {
            if (chk.value === "") todosChecked = true;
            else selectedValues.push(chk.value);
        });

        const todosCheckbox = document.getElementById('ramo_todos');
        if (!todosChecked && selectedValues.length === 0) {
             if (todosCheckbox) todosCheckbox.checked = true;
             todosChecked = true;
        }

        if (todosChecked) ramoValue.value = "";
        else ramoValue.value = selectedValues.join(',');

        if (todosChecked) {
            ramoDropdownBtn.textContent = "Todos los ramos";
            ramoDropdownBtn.classList.remove('text-primary', 'fw-bold');
        } else {
            ramoDropdownBtn.classList.add('text-primary', 'fw-bold');
            ramoDropdownBtn.textContent = selectedValues.length === 1 ? selectedValues[0] : `${selectedValues.length} seleccionados`;
        }
    }

    async function fetchData(usuario, estado, fechaDesde, fechaHasta, ramo) {
        try {
            tableBody.innerHTML = `<tr><td colspan="13" class="text-center py-4 text-muted">Cargando datos...</td></tr>`;

            let url = `/api/reportes/vencimientos-renovaciones?usuario=${encodeURIComponent(usuario)}&estado=${encodeURIComponent(estado)}`;
            
            if (fechaDesde) url += `&fecha_desde=${encodeURIComponent(fechaDesde)}`;
            if (fechaHasta) url += `&fecha_hasta=${encodeURIComponent(fechaHasta)}`;
            if (ramo) url += `&ramo=${encodeURIComponent(ramo)}`;

            const response = await fetch(url);
            const data = await response.json();
            renderTable(data);
        } catch (error) {
            console.error('Error loading data:', error);
            tableBody.innerHTML = `<tr><td colspan="13" class="text-center text-danger">Error cargando datos</td></tr>`;
        }
    }

    function renderTable(data) {
        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="13" class="text-center text-muted py-4">No se encontraron resultados</td></tr>`;
            return;
        }

        // Agrupar por póliza y acumular primas por recibo
        const grouped = groupByPoliza(data);

        tableBody.innerHTML = grouped.map(row => {
            const moneda = row.moneda || '';
            const primaNeta = row.prima_neta ? parseFloat(row.prima_neta).toFixed(2) : '0.00';
            const primaTotal = row.prima_total ? parseFloat(row.prima_total).toFixed(2) : '0.00';

            return `
                <tr>
                    <td>${row.compania || '-'}</td>
                    <td>${row.ramo || '-'}</td>
                    <td>${row.producto || '-'}</td>
                    <td>${row.tipo_documento || '-'}</td>
                    <td>${row.numero_documento || '-'}</td>
                    <td>${row.contratante || '-'}</td>
                    <td>${row.poliza || '-'}</td>
                    <td>${row.vig_desde || '-'}</td>
                    <td>${row.vig_hasta || '-'}</td>
                    <td>${primaNeta}</td>
                    <td>${primaTotal}</td>
                    <td><span class="badge bg-${getStatusColor(row.estado)}">${row.estado || '-'}</span></td>
                    <td class="text-end">
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="toggleCuotasRow('${row.poliza || ''}', '${row.idPoliza || ''}')">
                            Ver recibos
                        </button>
                    </td>
                </tr>
                <tr id="cuotas_${row.poliza || ''}_${row.idPoliza || ''}" class="d-none">
                    <td colspan="13">
                        <div id="cuotas_container_${row.poliza || ''}_${row.idPoliza || ''}" class="py-2"></div>
                    </td>
                </tr>
            `;
        }).join('');

        // Se elimina el detalle expandible de cuotas
    }

    // Helper: agrupar por póliza (o idPoliza si existe) y sumar primas neta y total
    function groupByPoliza(rows) {
        const map = new Map();
        rows.forEach(r => {
            // Group by policy number string to merge renewals
            const key = r.poliza || '';
            if (!map.has(key)) {
                map.set(key, {
                    // Usar el idPoliza del registro actual (si hay filtro de fecha, será el único visible)
                    idPoliza: r.idPoliza, 
                    compania: r.compania,
                    ramo: r.ramo,
                    producto: r.producto,
                    tipo_documento: r.tipo_documento,
                    numero_documento: r.numero_documento,
                    contratante: r.contratante,
                    poliza: r.poliza,
                    vig_desde: r.vig_desde,
                    vig_hasta: r.vig_hasta,
                    estado: r.estado,
                    moneda: r.moneda,
                    prima_neta: 0,
                    prima_total: 0
                });
            }
            const acc = map.get(key);
            
            // Actualizar fechas para mostrar el rango completo (min vig_desde, max vig_hasta)
            const newDesde = parseDate(r.vig_desde);
            if (newDesde) {
                const currentDesde = parseDate(acc.vig_desde);
                if (!currentDesde || newDesde < currentDesde) {
                    acc.vig_desde = r.vig_desde;
                }
            }

            const newHasta = parseDate(r.vig_hasta);
            if (newHasta) {
                const currentHasta = parseDate(acc.vig_hasta);
                if (!currentHasta || newHasta > currentHasta) {
                    acc.vig_hasta = r.vig_hasta;
                }
            }

            const pn = r.prima_neta ? parseFloat(r.prima_neta) : 0;
            const pt = r.prima_total ? parseFloat(r.prima_total) : 0;
            acc.prima_neta += isNaN(pn) ? 0 : pn;
            acc.prima_total += isNaN(pt) ? 0 : pt;
        });
        return Array.from(map.values());
    }

    // Helper to parse DD/MM/YYYY to Date object
    function parseDate(dateStr) {
        if (!dateStr || dateStr === '-' || dateStr === '') return null;
        const parts = dateStr.split('/');
        if (parts.length !== 3) return null;
        // DD/MM/YYYY -> YYYY, MM-1, DD
        const d = new Date(parts[2], parts[1] - 1, parts[0]);
        return isNaN(d.getTime()) ? null : d;
    }

    function getStatusColor(status) {
        if (!status) return 'secondary';
        const s = status.toLowerCase();
        if (s.includes('vigente') || s.includes('activo')) return 'success';
        if (s.includes('pendiente')) return 'warning';
        if (s.includes('anulado') || s.includes('cancelado')) return 'danger';
        if (s.includes('sin prima')) return 'dark';
        return 'secondary';
    }

    function renderCuotasRows(rows, polizaCtx) {
        if (!rows || rows.length === 0) {
            return `<div class="text-muted small">No hay cuotas registradas</div>`;
        }
        const header = `
            <div class="table-responsive">
              <table class="table table-sm mb-0">
                <thead class="table-light">
                  <tr>
                    <th>PROFORMA</th>
                    <th>TIPO</th>
                    <th>CUPÓN</th>
                    <th>FECHA VENCIMIENTO</th>
                    <th>FECHA DE PAGO</th>
                    <th>IMPORTE</th>
                    <th>FACTURA</th>
                    <th>ACCIONES</th>
                  </tr>
                </thead>
                <tbody>
        `;
        const body = rows.map(r => {
            const hasFactura = !!(r.factura && String(r.factura).trim() !== '' && r.factura !== '-');
            // User requested to show edit button even if it has factura ("le falta pagar")
            // and explicitly mentioned "que tenga 2 ambos" (both rows should have actions).
            // So we enable the edit button always.
            const showEdit = true; 
            return `
            <tr>
                <td>${r.aviso_cobranza || String(r.cupon || '').replace(/-\d+$/,'') || '-'}</td>
                <td>${r.tipo_doc || '-'}</td>
                <td>${r.cupon || '-'}</td>
                <td>${r.fecha_vencimiento || '-'}</td>
                <td>${r.fecha_pago || '-'}</td>
                <td>${r.importe || '-'}</td>
                <td>${r.factura || '-'}</td>
                <td>
                    ${showEdit
                        ? `<button type="button"
                                   class="btn btn-sm btn-outline-secondary"
                                   title="Agregar/Actualizar pago"
                                   onclick="CuotaModal.open('${polizaCtx || ''}', '', '${r.cupon || ''}')">
                               <i class="bi bi-pencil"></i>
                           </button>`
                        : ''
                    }
                </td>
            </tr>
        `;
        }).join('');
        const footer = `
                </tbody>
              </table>
            </div>
        `;
        return header + body + footer;
    }

    window.toggleCuotasRow = async function(poliza, idPoliza) {
        const rowId = `cuotas_${poliza || ''}_${idPoliza || ''}`;
        const containerId = `cuotas_container_${poliza || ''}_${idPoliza || ''}`;
        const row = document.getElementById(rowId);
        const container = document.getElementById(containerId);
        
        if (!row || !container) return;
        const isHidden = row.classList.contains('d-none');
        if (isHidden) {
            container.innerHTML = `<div class="text-muted small px-2">Cargando recibos...</div>`;
            try {
                let url = `/api/cuotas/list?poliza=${encodeURIComponent(poliza)}`;
                
                // Get date filters from the main form
                const fechaDesde = document.getElementById('fechaDesde').value;
                const fechaHasta = document.getElementById('fechaHasta').value;
                
                if (fechaDesde) url += `&fecha_desde=${encodeURIComponent(fechaDesde)}`;
                if (fechaHasta) url += `&fecha_hasta=${encodeURIComponent(fechaHasta)}`;

                // if (idPoliza) {
                //     url += `&poliza_id=${encodeURIComponent(idPoliza)}`;
                // }
                const resp = await fetch(url);
                const json = await resp.json();
                const rows = (json && json.rows) ? json.rows : [];
                container.innerHTML = renderCuotasRows(rows, poliza);
            } catch (err) {
                container.innerHTML = `<div class="text-danger small px-2">Error cargando recibos</div>`;
            }
            row.classList.remove('d-none');
        } else {
            row.classList.add('d-none');
        }
    }
});
