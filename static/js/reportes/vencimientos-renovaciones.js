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

    // Pagination state
    let allData = [];
    let currentPage = 1;
    let rowsPerPage = 15;

    const rowsPerPageSelect = document.getElementById('rowsPerPage');
    const paginationControls = document.getElementById('paginationControls');
    const pageInfo = document.getElementById('pageInfo');
    const paginationContainer = document.getElementById('paginationContainer');

    const cuotasOffcanvasEl = document.getElementById('cuotasOffcanvas');
    const cuotasOffcanvasContent = document.getElementById('cuotasOffcanvasContent');
    const cuotasOffcanvasSubtitle = document.getElementById('cuotasOffcanvasSubtitle');
    let cuotasOffcanvasInstance = null;

    if (rowsPerPageSelect) {
        rowsPerPageSelect.addEventListener('change', function() {
            rowsPerPage = parseInt(this.value);
            currentPage = 1;
            renderPaginatedTable();
        });
    }

    // Load users and ramos on init
    loadUsuarios();
    loadRamos();

    // Trigger initial load automatically
    if (filterForm) {
        // Small delay to ensure dropdowns might be ready (though not strictly necessary for default 'all' filter)
        setTimeout(() => {
            filterForm.dispatchEvent(new Event('submit'));
        }, 100);
    }

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
                const displayName = (u.nombre || u.username || '').toString();
                const isChecked = currentUser && (u.username || '').toLowerCase() === currentUser;
                li.innerHTML = `
                    <div class="dropdown-item">
                        <div class="form-check">
                            <input class="form-check-input usuario-checkbox" type="checkbox" value="${u.username}" data-display="${displayName}" id="user_${u.username}" ${isChecked ? 'checked' : ''}>
                            <label class="form-check-label w-100" style="cursor: pointer;" for="user_${u.username}">${displayName}</label>
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
        const selectedLabels = [];
        let todosChecked = false;

        checkboxes.forEach(chk => {
            if (chk.value === "") todosChecked = true;
            else {
                selectedValues.push(chk.value);
                selectedLabels.push((chk.dataset.display || chk.value).toString());
            }
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
            usuarioDropdownBtn.textContent = selectedValues.length === 1 ? selectedLabels[0] : `${selectedValues.length} seleccionados`;
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
            tableBody.innerHTML = `<tr><td colspan="11" class="text-center py-4 text-muted">Cargando datos...</td></tr>`;
            if (paginationContainer) paginationContainer.style.display = 'none';

            let url = `/api/reportes/vencimientos-renovaciones?usuario=${encodeURIComponent(usuario)}&estado=${encodeURIComponent(estado)}`;
            
            if (fechaDesde) url += `&fecha_desde=${encodeURIComponent(fechaDesde)}`;
            if (fechaHasta) url += `&fecha_hasta=${encodeURIComponent(fechaHasta)}`;
            if (ramo) url += `&ramo=${encodeURIComponent(ramo)}`;

            const response = await fetch(url);
            const data = await response.json();
            
            if (!data || data.length === 0) {
                allData = [];
                renderPaginatedTable();
                return;
            }

            // Group data first
            allData = groupByPoliza(data);
            currentPage = 1;
            renderPaginatedTable();
        } catch (error) {
            console.error('Error loading data:', error);
            tableBody.innerHTML = `<tr><td colspan="11" class="text-center text-danger">Error cargando datos</td></tr>`;
        }
    }

    function renderPaginatedTable() {
        if (!allData || allData.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="11" class="text-center text-muted py-4">No se encontraron resultados</td></tr>`;
            if (paginationContainer) paginationContainer.style.display = 'none';
            return;
        }

        if (paginationContainer) paginationContainer.style.display = 'flex';

        if (rowsPerPageSelect) rowsPerPage = parseInt(rowsPerPageSelect.value);

        const startIndex = (currentPage - 1) * rowsPerPage;
        const endIndex = startIndex + rowsPerPage;
        const slicedData = allData.slice(startIndex, endIndex);

        renderTableRows(slicedData);
        renderPaginationControls();
    }

    function renderTableRows(rows) {
        tableBody.innerHTML = rows.map(row => {
            const moneda = row.moneda || '';
            const primaNeta = row.prima_neta ? parseFloat(row.prima_neta).toFixed(2) : '0.00';
            const primaTotal = row.prima_total ? parseFloat(row.prima_total).toFixed(2) : '0.00';
            const poliza = (row.poliza || '').toString();
            const idPoliza = (row.idPoliza || '').toString();
            const safePoliza = poliza.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            const safeIdPoliza = idPoliza.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

            return `
                <tr>
                    <td>${row.compania || '-'}</td>
                    <td>${row.ramo || '-'}</td>
                    <td>${row.producto || '-'}</td>
                    <td>${row.numero_documento || '-'}</td>
                    <td>${row.contratante || '-'}</td>
                    <td>${row.poliza || '-'}</td>
                    <td>${row.vig_desde || '-'}</td>
                    <td>${row.vig_hasta || '-'}</td>
                    <td>${primaNeta}</td>
                    <td>${primaTotal}</td>
                    <td class="text-end">
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="openCuotasPanel('${safePoliza}', '${safeIdPoliza}')">
                            Ver recibos
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    function renderPaginationControls() {
        if (!paginationControls) return;
        
        const totalPages = Math.ceil(allData.length / rowsPerPage);
        let html = '';

        // Previous
        html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                    <a class="page-link" href="#" onclick="changePage(${currentPage - 1}); return false;">Anterior</a>
                 </li>`;

        // Page numbers
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, currentPage + 2);

        if (currentPage <= 3) {
            endPage = Math.min(totalPages, 5);
        }
        if (currentPage >= totalPages - 2) {
            startPage = Math.max(1, totalPages - 4);
        }

        if (startPage > 1) {
             html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(1); return false;">1</a></li>`;
             if (startPage > 2) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="changePage(${i}); return false;">${i}</a>
                     </li>`;
        }

        if (endPage < totalPages) {
             if (endPage < totalPages - 1) html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
             html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${totalPages}); return false;">${totalPages}</a></li>`;
        }

        // Next
        html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                    <a class="page-link" href="#" onclick="changePage(${currentPage + 1}); return false;">Siguiente</a>
                 </li>`;

        paginationControls.innerHTML = html;

        if (pageInfo) {
            const start = (currentPage - 1) * rowsPerPage + 1;
            const end = Math.min(currentPage * rowsPerPage, allData.length);
            pageInfo.textContent = `${start}-${end} de ${allData.length}`;
        }
    }

    window.changePage = function(page) {
        const totalPages = Math.ceil(allData.length / rowsPerPage);
        if (page < 1 || page > totalPages) return;
        currentPage = page;
        renderPaginatedTable();
    };

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
            
            if ((!acc.idPoliza || String(acc.idPoliza).trim() === '') && r.idPoliza) {
                acc.idPoliza = r.idPoliza;
            }

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
                    if (r.idPoliza) acc.idPoliza = r.idPoliza;
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

    window.cuotasCache = {};

    function ensureOffcanvasInstance() {
        if (!cuotasOffcanvasEl) return null;
        if (cuotasOffcanvasInstance) return cuotasOffcanvasInstance;
        if (window.bootstrap && window.bootstrap.Offcanvas) {
            cuotasOffcanvasInstance = window.bootstrap.Offcanvas.getOrCreateInstance(cuotasOffcanvasEl);
            return cuotasOffcanvasInstance;
        }
        return null;
    }

    function getCurrencyPrefix(moneda) {
        const m = (moneda || '').toString().toLowerCase();
        if (m.includes('usd') || m.includes('dolar') || m.includes('dólar') || m.includes('$')) return '$';
        return 'S/';
    }

    function formatAmount(value, moneda) {
        const raw = (value ?? '').toString().replace(/,/g, '').trim();
        const num = parseFloat(raw);
        const prefix = getCurrencyPrefix(moneda);
        if (!isFinite(num)) return `${prefix} —`;
        return `${prefix} ${num.toFixed(2)}`;
    }

    function isCuotaPagada(r) {
        const hasFactura = !!(r.factura && String(r.factura).trim() !== '' && r.factura !== '-');
        const hasFechaPago = !!(r.fecha_pago && String(r.fecha_pago).trim() !== '' && r.fecha_pago !== '-');
        return hasFactura && hasFechaPago;
    }

    function findPolizaRow(poliza) {
        const key = (poliza || '').toString();
        return (allData || []).find(r => String(r.poliza || '') === key) || null;
    }

    function renderCuotasPanel(polizaRow, cuotas, poliza, idPoliza) {
        const total = cuotas.length;
        const pagadas = cuotas.reduce((acc, r) => acc + (isCuotaPagada(r) ? 1 : 0), 0);
        const pendientes = Math.max(0, total - pagadas);
        const moneda = (polizaRow && polizaRow.moneda) ? polizaRow.moneda : '';

        const resumen = `
            <div class="poliza-resumen-card p-3 mb-3">
                <div class="d-flex justify-content-between align-items-start gap-2">
                    <div>
                        <div class="fw-bold">${(polizaRow && polizaRow.compania) ? polizaRow.compania : '—'}${(polizaRow && polizaRow.ramo) ? ` - ${polizaRow.ramo}` : ''}</div>
                        <div class="text-muted small">${(polizaRow && polizaRow.contratante) ? polizaRow.contratante : '—'}</div>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-secondary" data-bs-dismiss="offcanvas">Ocultar</button>
                </div>
                <div class="poliza-resumen-grid mt-3">
                    <div class="small"><span class="text-muted">Póliza:</span> <span class="fw-semibold">${poliza || '—'}</span></div>
                    <div class="small"><span class="text-muted">Producto:</span> <span class="fw-semibold">${(polizaRow && polizaRow.producto) ? polizaRow.producto : '—'}</span></div>
                    <div class="small"><span class="text-muted">Vigencia:</span> <span class="fw-semibold">${(polizaRow && polizaRow.vig_desde) ? polizaRow.vig_desde : '—'} - ${(polizaRow && polizaRow.vig_hasta) ? polizaRow.vig_hasta : '—'}</span></div>
                </div>
            </div>
        `;

        const kpis = `
            <div class="kpi-grid mb-3">
                <div class="kpi-card p-3">
                    <div class="kpi-label">Total cuotas</div>
                    <div class="kpi-value">${total}</div>
                </div>
                <div class="kpi-card p-3">
                    <div class="kpi-label">Pagadas</div>
                    <div class="kpi-value text-success">${pagadas}</div>
                </div>
                <div class="kpi-card p-3">
                    <div class="kpi-label">Pendientes</div>
                    <div class="kpi-value text-warning">${pendientes}</div>
                </div>
            </div>
        `;

        const list = total === 0
            ? `<div class="text-muted small">No hay cuotas registradas.</div>`
            : cuotas.map((r, index) => {
                const pagada = isCuotaPagada(r);
                const statusClass = pagada ? 'status-paid' : 'status-pending';
                const statusLabel = pagada ? 'Pagado' : 'Pendiente';
                const numero = r.numero_cuota || r.secuencia || (index + 1);
                const proforma = r.aviso_cobranza || String(r.cupon || '').replace(/-\d+$/, '') || '-';
                const cupon = r.cupon || '-';
                const vence = r.fecha_vencimiento || '-';
                const fechaPago = r.fecha_pago || '-';
                const factura = r.factura || '-';
                const importe = formatAmount(r.importe, moneda);

                const actions = pagada
                    ? `
                        <div class="cuota-actions d-flex justify-content-end gap-2">
                            <button type="button" class="btn btn-sm btn-outline-primary" onclick="openCuotaPdf('${String(idPoliza || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')">PDF</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="CuotaEditModal.open(window.cuotasCache['${String(poliza || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'][${index}], '${String(poliza || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')">
                                <i class="bi bi-pencil"></i>
                            </button>
                        </div>
                    `
                    : `
                        <div class="cuota-actions d-flex justify-content-end gap-2">
                            <button type="button" class="btn btn-sm btn-success" onclick="CuotaEditModal.open(window.cuotasCache['${String(poliza || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'][${index}], '${String(poliza || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')">Pagar</button>
                            <button type="button" class="btn btn-sm btn-outline-primary" onclick="openCuotaPdf('${String(idPoliza || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')">PDF</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="CuotaEditModal.open(window.cuotasCache['${String(poliza || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'][${index}], '${String(poliza || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'")}')">
                                <i class="bi bi-pencil"></i>
                            </button>
                        </div>
                    `;

                return `
                    <div class="cuota-card p-3 mb-3">
                        <div class="d-flex justify-content-between align-items-start gap-2">
                            <div class="cuota-title">Cuota #${numero}</div>
                            <span class="status-pill ${statusClass}">
                                <span class="status-dot"></span>
                                ${statusLabel}
                            </span>
                        </div>
                        <div class="row mt-2 g-2">
                            <div class="col-12 col-sm-6">
                                <div class="cuota-meta">Proforma</div>
                                <div class="fw-semibold">${proforma}</div>
                            </div>
                            <div class="col-12 col-sm-6">
                                <div class="cuota-meta">Cupón</div>
                                <div class="fw-semibold">${cupon}</div>
                            </div>
                            <div class="col-12 col-sm-6">
                                <div class="cuota-meta">Vence</div>
                                <div class="fw-semibold">${vence}</div>
                            </div>
                            <div class="col-12 col-sm-6">
                                <div class="cuota-meta">Importe</div>
                                <div class="fw-semibold">${importe}</div>
                            </div>
                            <div class="col-12 col-sm-6">
                                <div class="cuota-meta">Fecha pago</div>
                                <div class="fw-semibold">${fechaPago}</div>
                            </div>
                            <div class="col-12 col-sm-6">
                                <div class="cuota-meta">Factura</div>
                                <div class="fw-semibold">${factura}</div>
                            </div>
                        </div>
                        <div class="mt-3">
                            ${actions}
                        </div>
                    </div>
                `;
            }).join('');

        return resumen + kpis + list;
    }

    async function fetchCuotas(poliza) {
        let url = `/api/cuotas/list?poliza=${encodeURIComponent(poliza || '')}`;

        const fechaDesde = document.getElementById('fechaDesde').value;
        const fechaHasta = document.getElementById('fechaHasta').value;

        if (fechaDesde) url += `&fecha_desde=${encodeURIComponent(fechaDesde)}`;
        if (fechaHasta) url += `&fecha_hasta=${encodeURIComponent(fechaHasta)}`;

        const resp = await fetch(url);
        const json = await resp.json();
        return (json && json.rows) ? json.rows : [];
    }

    function showInlineAlert(message) {
        if (window.Swal && typeof window.Swal.fire === 'function') {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            window.Swal.fire({
                icon: 'info',
                title: 'Aviso',
                text: message,
                confirmButtonText: 'Aceptar',
                confirmButtonColor: '#3b82f6',
                background: isDark ? '#1a1a1a' : '#ffffff',
                color: isDark ? '#ffffff' : '#333333',
                customClass: { popup: 'rounded-4', confirmButton: 'rounded-pill px-4' }
            });
        } else {
            alert(message);
        }
    }

    window.openCuotaPdf = async function(polizaId) {
        const id = (polizaId || '').toString().trim();
        if (!id) {
            showInlineAlert('No hay documento asociado a esta póliza.');
            return;
        }
        try {
            const res = await fetch(`/api/cuotas/archivos/${encodeURIComponent(id)}`);
            const json = await res.json();
            if (!json || !json.ok || !json.archivos || json.archivos.length === 0) {
                showInlineAlert('No hay archivos PDF guardados para esta póliza.');
                return;
            }
            const archivo = json.archivos[0];
            const url = `/uploads/${archivo.ruta_archivo}`;
            window.open(url, '_blank');
        } catch (e) {
            console.error(e);
            showInlineAlert('Error al intentar cargar el documento.');
        }
    };

    window.openCuotasPanel = async function(poliza, idPoliza) {
        const inst = ensureOffcanvasInstance();
        if (!cuotasOffcanvasContent) return;

        const polizaRow = findPolizaRow(poliza);
        window.currentPoliza = poliza || '';
        window.currentPolizaId = idPoliza || '';

        if (cuotasOffcanvasSubtitle) {
            const compania = polizaRow ? (polizaRow.compania || '') : '';
            const contratante = polizaRow ? (polizaRow.contratante || '') : '';
            cuotasOffcanvasSubtitle.textContent = [compania, contratante].filter(Boolean).join(' • ');
        }

        cuotasOffcanvasContent.innerHTML = `<div class="text-muted small">Cargando recibos...</div>`;
        if (inst) inst.show();

        try {
            const rows = await fetchCuotas(poliza);
            window.cuotasCache[poliza] = rows;
            cuotasOffcanvasContent.innerHTML = renderCuotasPanel(polizaRow, rows, poliza, idPoliza);
        } catch (err) {
            console.error(err);
            cuotasOffcanvasContent.innerHTML = `<div class="text-danger small">Error cargando recibos</div>`;
        }
    };
});
