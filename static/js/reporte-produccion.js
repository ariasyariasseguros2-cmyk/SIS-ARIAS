function reporteProduccionInit() {
    const form = document.getElementById('formReporteProduccion');
    const tableBodySummary = document.querySelector('#reporteProduccionTableSummary tbody');
    const tableBodyFull = document.querySelector('#reporteProduccionTableFull tbody');
    const btnExport = document.getElementById('btnExportProduccionExcel');
    const btnClear = document.getElementById('btnClearProduccion');

    // Estado de paginación
    let allData = [];
    let currentPage = 1;
    let rowsPerPage = 20;

    // Elementos de paginación
    const paginationContainers = document.querySelectorAll('.pagination-container');
    const rowsPerPageSelects = document.querySelectorAll('.rows-per-page-select');
    const pageInfos = document.querySelectorAll('.page-info');
    const paginationControlsLists = document.querySelectorAll('.pagination-controls');

    if (!form || !tableBodySummary) {
        return;
    }

    function buildQueryFromForm() {
        const params = new URLSearchParams();
        const formData = new FormData(form);
        for (const [key, value] of formData.entries()) {
            if (value && value.toString().trim() !== '') {
                params.append(key, value.toString().trim());
            }
        }
        return params.toString();
    }

    function hasAnyFilter() {
        const formData = new FormData(form);
        for (const [, value] of formData.entries()) {
            if (value && value.toString().trim() !== '') {
                return true;
            }
        }
        return false;
    }

    function renderTable() {
        const totalRows = allData.length;
        if (totalRows === 0) {
            const noData = '<tr><td colspan="30" class="text-center">No se encontraron resultados</td></tr>';
            tableBodySummary.innerHTML = '<tr><td colspan="10" class="text-center">No se encontraron resultados</td></tr>';
            if (tableBodyFull) tableBodyFull.innerHTML = noData;
            updatePaginationUI(0, 0, 0);
            return;
        }

        const totalPages = Math.ceil(totalRows / rowsPerPage);
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;

        const startIdx = (currentPage - 1) * rowsPerPage;
        const endIdx = Math.min(startIdx + rowsPerPage, totalRows);
        const rowsToRender = allData.slice(startIdx, endIdx);

        // Renderizar tabla completa
        const fullRowsHtml = rowsToRender
            .map(function (r) {
                function fmt(val) {
                    return val === null || val === undefined ? '' : val;
                }
                function fmtMoney(val) {
                    if (val === null || val === undefined) return '';
                    var num = parseFloat(val);
                    if (isNaN(num)) return val;
                    return num.toFixed(2);
                }
                return (
                    '<tr>' +
                    '<td>' + fmt(r.ruc) + '</td>' +
                    '<td>' + fmt(r.contratante) + '</td>' +
                    '<td>' + fmt(r.direccion_contratante) + '</td>' +
                    '<td>' + fmt(r.asegurado) + '</td>' +
                    '<td>' + fmt(r.cia) + '</td>' +
                    '<td>' + fmt(r.ram) + '</td>' +
                    '<td>' + fmt(r.prod) + '</td>' +
                    '<td>' + fmt(r.poliza) + '</td>' +
                    '<td>' + fmt(r.td) + '</td>' +
                    '<td>' + fmt(r.aviso_cob) + '</td>' +
                    '<td>' + fmt(r.estado_comision) + '</td>' +
                    '<td>' + fmt(r.ini_vig) + '</td>' +
                    '<td>' + fmt(r.fin_vig) + '</td>' +
                    '<td>' + fmt(r.mon) + '</td>' +
                    '<td class="text-end">' + fmtMoney(r.prim_neta) + '</td>' +
                    '<td class="text-end">' + fmtMoney(r.prim_total) + '</td>' +
                    '<td class="text-end">' + fmtMoney(r.porc_cia) + '</td>' +
                    '<td class="text-end">' + fmtMoney(r.comision_cia) + '</td>' +
                    '<td>' + fmt(r.sagt) + '</td>' +
                    '<td class="text-end">' + fmtMoney(r.porc_sagt) + '</td>' +
                    '<td class="text-end">' + fmtMoney(r.comision_sagt) + '</td>' +
                    '<td>' + fmt(r.fpago_sagt) + '</td>' +
                    '<td>' + fmt(r.comprobante_sagt) + '</td>' +
                    '<td>' + fmt(r.motivo) + '</td>' +
                    '<td>' + fmt(r.ciudad) + '</td>' +
                    '<td>' + fmt(r.factura_comision) + '</td>' +
                    '<td>' + fmt(r.ejecutivo) + '</td>' +
                    '<td>' + fmt(r.breve_descripcion) + '</td>' +
                    '<td>' + fmt(r.usuario) + '</td>' +
                    '<td>' + fmt(r.f_reg) + '</td>' +
                    '</tr>'
                );
            })
            .join('');

        // Renderizar tabla resumen
        const summaryRowsHtml = rowsToRender
            .map(function (r) {
                function fmt(val) {
                    return val === null || val === undefined ? '' : val;
                }
                function fmtMoney(val) {
                    if (val === null || val === undefined) return '';
                    var num = parseFloat(val);
                    if (isNaN(num)) return val;
                    return num.toFixed(2);
                }
                return (
                    '<tr>' +
                    '<td>' + fmt(r.contratante) + '</td>' +
                    '<td>' + fmt(r.cia) + '</td>' +
                    '<td>' + fmt(r.ram) + '</td>' +
                    '<td>' + fmt(r.poliza) + '</td>' +
                    '<td>' + fmt(r.ini_vig) + '</td>' +
                    '<td>' + fmt(r.mon) + '</td>' +
                    '<td class="text-end">' + fmtMoney(r.prim_total) + '</td>' +
                    '<td>' + fmt(r.ejecutivo) + '</td>' +
                    '<td>' + fmt(r.usuario) + '</td>' +
                    '<td>' + fmt(r.f_reg) + '</td>' +
                    '</tr>'
                );
            })
            .join('');

        tableBodySummary.innerHTML = summaryRowsHtml;
        if (tableBodyFull) tableBodyFull.innerHTML = fullRowsHtml;

        updatePaginationUI(startIdx + 1, endIdx, totalRows);
    }

    function updatePaginationUI(start, end, total) {
        // Mostrar contenedores si hay datos
        paginationContainers.forEach(c => c.style.display = total > 0 ? 'flex' : 'none');

        // Actualizar texto info
        const infoText = total > 0 ? `Mostrando ${start} a ${end} de ${total} registros` : '';
        pageInfos.forEach(el => el.textContent = infoText);

        // Actualizar selectores
        rowsPerPageSelects.forEach(sel => sel.value = rowsPerPage);

        // Generar botones
        const totalPages = Math.ceil(total / rowsPerPage);
        let html = '';

        // Botón Previous
        const prevDisabled = currentPage === 1 ? 'disabled' : '';
        html += `<li class="page-item ${prevDisabled}">
                    <a class="page-link" href="#" data-page="${currentPage - 1}">Anterior</a>
                 </li>`;

        // Botones numéricos (lógica simple: mostrar todos si son pocos, o rango)
        // Para simplificar: mostrar siempre rango limitado alrededor de currentPage
        // Ejemplo: 1 ... [curr-1] [curr] [curr+1] ... [last]
        
        const delta = 2;
        const range = [];
        for (let i = Math.max(2, currentPage - delta); i <= Math.min(totalPages - 1, currentPage + delta); i++) {
            range.push(i);
        }

        if (currentPage > 1) range.unshift(1);
        if (currentPage < totalPages) range.push(totalPages);

        let l;
        // Si hay solo 1 pagina, range ya tiene [1]
        // Si totalPages=0, range vacio (pero total>0 aqui)
        
        // Simplemente iterar 1 a totalPages si son pocos (< 7)
        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) {
                const active = i === currentPage ? 'active' : '';
                html += `<li class="page-item ${active}">
                            <a class="page-link" href="#" data-page="${i}">${i}</a>
                         </li>`;
            }
        } else {
             // 1
             const active1 = 1 === currentPage ? 'active' : '';
             html += `<li class="page-item ${active1}"><a class="page-link" href="#" data-page="1">1</a></li>`;
             
             if (currentPage > 4) {
                 html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
             }

             let startPage = Math.max(2, currentPage - 1);
             let endPage = Math.min(totalPages - 1, currentPage + 1);
             
             // Ajustar si estamos cerca de los extremos
             if (currentPage <= 4) { endPage = 5; startPage = 2; }
             if (currentPage >= totalPages - 3) { startPage = totalPages - 4; endPage = totalPages - 1; }

             for (let i = startPage; i <= endPage; i++) {
                const active = i === currentPage ? 'active' : '';
                html += `<li class="page-item ${active}">
                            <a class="page-link" href="#" data-page="${i}">${i}</a>
                         </li>`;
             }

             if (currentPage < totalPages - 3) {
                 html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
             }

             // Last
             const activeLast = totalPages === currentPage ? 'active' : '';
             html += `<li class="page-item ${activeLast}"><a class="page-link" href="#" data-page="${totalPages}">${totalPages}</a></li>`;
        }

        // Botón Next
        const nextDisabled = currentPage === totalPages ? 'disabled' : '';
        html += `<li class="page-item ${nextDisabled}">
                    <a class="page-link" href="#" data-page="${currentPage + 1}">Siguiente</a>
                 </li>`;

        paginationControlsLists.forEach(el => el.innerHTML = html);
    }

    // Eventos de Paginación
    rowsPerPageSelects.forEach(sel => {
        sel.addEventListener('change', function() {
            rowsPerPage = parseInt(this.value);
            currentPage = 1;
            renderTable();
            // Sincronizar otros selectores
            rowsPerPageSelects.forEach(s => s.value = rowsPerPage);
        });
    });

    paginationControlsLists.forEach(list => {
        list.addEventListener('click', function(e) {
            e.preventDefault();
            const target = e.target.closest('.page-link');
            if (!target || target.parentElement.classList.contains('disabled')) return;
            
            const page = parseInt(target.dataset.page);
            if (page && page !== currentPage) {
                currentPage = page;
                renderTable();
            }
        });
    });

    function loadReporte() {
        const loadingHtml = '<tr><td colspan="30" class="text-center">Cargando...</td></tr>';
        tableBodySummary.innerHTML = '<tr><td colspan="10" class="text-center">Cargando...</td></tr>';
        if (tableBodyFull) tableBodyFull.innerHTML = loadingHtml;
        
        // Ocultar paginación mientras carga
        paginationContainers.forEach(c => c.style.display = 'none');

        var query = buildQueryFromForm();
        var url = '/api/reportes/produccion';
        if (query) {
            url += '?' + query;
        }

        fetch(url, {
            method: 'GET',
            headers: { 'Accept': 'application/json' },
        })
            .then(function (r) {
                return r.json();
            })
            .then(function (data) {
                if (!data.ok) {
                    const errorHtml = '<tr><td colspan="30" class="text-center text-danger">Error: ' +
                        (data.error || 'Desconocido') +
                        '</td></tr>';
                    tableBodySummary.innerHTML = '<tr><td colspan="10" class="text-center text-danger">Error: ' + (data.error || 'Desconocido') + '</td></tr>';
                    if (tableBodyFull) tableBodyFull.innerHTML = errorHtml;
                    return;
                }
                
                // Guardar datos y renderizar primera página
                allData = data.rows || [];
                currentPage = 1;
                renderTable();
            })
            .catch(function (err) {
                console.error(err);
                const errorHtml = '<tr><td colspan="30" class="text-center text-danger">Error de conexión</td></tr>';
                tableBodySummary.innerHTML = '<tr><td colspan="10" class="text-center text-danger">Error de conexión</td></tr>';
                if (tableBodyFull) tableBodyFull.innerHTML = errorHtml;
            });
    }

    form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        loadReporte();
    });

    if (btnExport) {
        btnExport.addEventListener('click', function () {
            var query = buildQueryFromForm();
            var url = '/api/reportes/produccion/export';
            if (query) {
                url += '?' + query;
            }
            window.open(url, '_blank');
        });
    }

    if (btnClear) {
        btnClear.addEventListener('click', function () {
            form.reset();
            allData = [];
            currentPage = 1;
            rowsPerPage = 20;
            rowsPerPageSelects.forEach(sel => sel.value = rowsPerPage);
            paginationContainers.forEach(c => c.style.display = 'none');
            tableBodySummary.innerHTML = '<tr><td colspan="10" class="text-center text-muted">Use los filtros y pulse Buscar.</td></tr>';
            if (tableBodyFull) {
                tableBodyFull.innerHTML = '<tr><td colspan="30" class="text-center text-muted">Use los filtros y pulse Buscar.</td></tr>';
            }
            updatePaginationUI(0, 0, 0);
        });
    }

    if (hasAnyFilter()) {
        loadReporte();
    }
}

document.addEventListener('DOMContentLoaded', reporteProduccionInit);
