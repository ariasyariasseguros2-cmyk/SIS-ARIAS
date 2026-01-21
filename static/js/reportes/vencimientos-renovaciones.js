document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.getElementById('filterForm');
    const tableBody = document.querySelector('#resultsTable tbody');

    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const fechaInicio = document.getElementById('fechaInicio').value;
        const fechaFin = document.getElementById('fechaFin').value;

        if (!fechaInicio || !fechaFin) {
            alert('Por favor seleccione ambas fechas.');
            return;
        }

        fetchData(fechaInicio, fechaFin);
    });

    async function fetchData(inicio, fin) {
        try {
            // Show loading state
            // colspan matches header count (14)
            tableBody.innerHTML = `<tr><td colspan="14" class="text-center py-4 text-muted">Cargando datos...</td></tr>`;

            const url = `/api/reportes/vencimientos-renovaciones?fecha_inicio=${inicio}&fecha_fin=${fin}`;
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
                        <a href="/menu/cuotas?poliza=${encodeURIComponent(row.poliza || '')}" target="_blank" class="btn btn-sm btn-info text-white">
                            Cuotas
                        </a>
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
