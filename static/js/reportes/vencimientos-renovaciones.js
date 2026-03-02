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
            tableBody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-muted">Cargando datos...</td></tr>`;

            let url = `/api/reportes/vencimientos-renovaciones?usuario=${encodeURIComponent(usuario)}&estado=${encodeURIComponent(estado)}`;
            
            if (fechaDesde) url += `&fecha_desde=${encodeURIComponent(fechaDesde)}`;
            if (fechaHasta) url += `&fecha_hasta=${encodeURIComponent(fechaHasta)}`;
            if (ramo) url += `&ramo=${encodeURIComponent(ramo)}`;

            const response = await fetch(url);
            const data = await response.json();
            renderTable(data);
        } catch (error) {
            console.error('Error loading data:', error);
            tableBody.innerHTML = `<tr><td colspan="14" class="text-center text-danger">Error cargando datos</td></tr>`;
        }
    }

    function renderTable(data) {
        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="14" class="text-center text-muted py-4">No se encontraron resultados</td></tr>`;
            return;
        }

        tableBody.innerHTML = data.map(row => {
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
                    <td>${row.aviso_cobranza || '-'}</td>
                    <td>${row.cupon || '-'}</td>
                    <td>${row.vig_desde || '-'}</td>
                    <td>${row.vig_hasta || '-'}</td>
                    <td>${row.fecha_pago || '-'}</td>
                    <td>${primaNeta}</td>
                    <td>${primaTotal}</td>
                    <td><span class="badge bg-${getStatusColor(row.estado)}">${row.estado || '-'}</span></td>
                    <td>
                        <button type="button"
                                class="btn btn-sm btn-outline-primary expand-cuotas"
                                data-poliza="${row.poliza || ''}"
                                data-aviso="${row.aviso_cobranza || ''}">
                            <span class="me-1">Cuotas</span>
                            <span class="chev">▼</span>
                        </button>
                    </td>
                </tr>
                <tr class="cuotas-detail d-none">
                    <td colspan="16">
                        <div class="py-2 text-muted small">Cargando cuotas...</div>
                    </td>
                </tr>
            `;
        }).join('');

        const expandBtns = tableBody.querySelectorAll('.expand-cuotas');
        expandBtns.forEach((btn) => {
            btn.addEventListener('click', async function() {
                const tr = this.closest('tr');
                const detailRow = tr.nextElementSibling;
                if (!detailRow || !detailRow.classList.contains('cuotas-detail')) return;
                const isHidden = detailRow.classList.contains('d-none');
                if (isHidden) {
                    // Load cuotas
                    const poliza = this.dataset.poliza || '';
                    const aviso = this.dataset.aviso || '';
                    try {
                        const url = `/api/cuotas/list?poliza=${encodeURIComponent(poliza)}${aviso ? `&aviso=${encodeURIComponent(aviso)}` : ''}`;
                        const resp = await fetch(url);
                        const json = await resp.json();
                        const rows = (json && json.rows) ? json.rows : [];
                        detailRow.querySelector('td').innerHTML = renderCuotasRows(rows, poliza);
                    } catch (err) {
                        detailRow.querySelector('td').innerHTML = `<div class="text-danger small">Error cargando cuotas</div>`;
                    }
                    detailRow.classList.remove('d-none');
                    const chev = this.querySelector('.chev');
                    if (chev) chev.textContent = '▲';
                } else {
                    detailRow.classList.add('d-none');
                    const chev = this.querySelector('.chev');
                    if (chev) chev.textContent = '▼';
                }
            });
        });
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
                    <th>CUPÓN</th>
                    <th>VENCIMIENTO</th>
                    <th>MONEDA</th>
                    <th>IMPORTE</th>
                    <th>FECHA DE PAGO</th>
                    <th>FACTURA</th>
                    <th>OBSERVACIÓN</th>
                    <th>ACCIONES</th>
                  </tr>
                </thead>
                <tbody>
        `;
        const body = rows.map(r => {
            const hasPago = !!(r.fecha_pago && String(r.fecha_pago).trim() !== '' && r.fecha_pago !== '-');
            const hasFactura = !!(r.factura && String(r.factura).trim() !== '' && r.factura !== '-');
            const showEdit = !(hasPago || hasFactura);
            return `
            <tr>
                <td>${r.cupon || '-'}</td>
                <td>${r.fecha_vencimiento || '-'}</td>
                <td>${r.moneda || '-'}</td>
                <td>${r.importe || '-'}</td>
                <td>${r.fecha_pago || '-'}</td>
                <td>${r.factura || '-'}</td>
                <td>${r.observacion || '-'}</td>
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
});
