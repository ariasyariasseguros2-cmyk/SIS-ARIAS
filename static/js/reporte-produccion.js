function reporteProduccionInit() {
    const form = document.getElementById('formReporteProduccion');
    const tableBody = document.querySelector('#reporteProduccionTable tbody');
    const btnExport = document.getElementById('btnExportProduccionExcel');

    if (!form || !tableBody) {
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

    function renderRows(rows) {
        if (!rows || rows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="30" class="text-center">No se encontraron resultados</td></tr>';
            return;
        }

        tableBody.innerHTML = rows
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
    }

    function loadReporte() {
        tableBody.innerHTML = '<tr><td colspan="30" class="text-center">Cargando...</td></tr>';

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
                    tableBody.innerHTML =
                        '<tr><td colspan="30" class="text-center text-danger">Error: ' +
                        (data.error || 'Desconocido') +
                        '</td></tr>';
                    return;
                }
                renderRows(data.rows || []);
            })
            .catch(function (err) {
                console.error(err);
                tableBody.innerHTML =
                    '<tr><td colspan="30" class="text-center text-danger">Error de conexión</td></tr>';
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

    if (hasAnyFilter()) {
        loadReporte();
    }
}

document.addEventListener('DOMContentLoaded', reporteProduccionInit);
