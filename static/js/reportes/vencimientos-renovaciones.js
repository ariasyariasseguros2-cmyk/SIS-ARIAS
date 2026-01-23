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
                    <td>${row.poliza || '-'}</td>
                    <td>${row.aviso_cobranza || '-'}</td>
                    <td>${row.vig_desde || '-'}</td>
                    <td>${row.vig_hasta || '-'}</td>
                    <td>${row.fecha_pago || '-'}</td>
                    <td>${primaNeta}</td>
                    <td>${primaTotal}</td>
                    <td><span class="badge bg-${getStatusColor(row.estado)}">${row.estado || '-'}</span></td>
                    <td>
                        <button type="button" onclick="CuotaModal.open('${row.poliza || ''}')" class="btn btn-sm btn-info text-white">
                            Cuotas
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
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
});
