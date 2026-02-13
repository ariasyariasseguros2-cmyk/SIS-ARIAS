function reporteDiario() {
    const form = document.getElementById('formReporteDiario');
    const tableBody = document.querySelector('#reporteDiarioTable tbody');
    if (!form || !tableBody) return;

    form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        const data = Object.fromEntries(new FormData(form).entries());
        console.log('[Reporte Diario] Filtros seleccionados:', data);
        
        // Show loading state
        tableBody.innerHTML = '<tr><td colspan="13" class="text-center">Cargando...</td></tr>';

        fetch('/api/reporte-diario', { 
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify(data) 
        })
        .then(r => r.json())
        .then(response => {
            if (response.ok) {
                renderTable(response.rows);
            } else {
                tableBody.innerHTML = `<tr><td colspan="13" class="text-center text-danger">Error: ${response.error || 'Desconocido'}</td></tr>`;
            }
        })
        .catch(err => {
            console.error(err);
            tableBody.innerHTML = `<tr><td colspan="13" class="text-center text-danger">Error de conexión</td></tr>`;
        });
    });

    function renderTable(rows) {
        if (!rows || rows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="13" class="text-center">No se encontraron resultados</td></tr>';
            return;
        }

        tableBody.innerHTML = rows.map(r => `
            <tr>
                <td>${formatDate(r.fecha_emision)}</td>
                <td>${r.poliza || ''}</td>
                <td>${r.contratante || ''}</td>
                <td>${r.compania || ''}</td>
                <td>${r.ramo || ''}</td>
                <td class="text-end">${formatMoney(r.prima_neta)}</td>
                <td class="text-end">${formatMoney(r.prima_comercial)}</td>
                <td class="text-end">${formatMoney(r.comision)}</td>
                <td class="text-end">${r.porcentaje_comision || ''}%</td>
                <td>${r.moneda || ''}</td>
                <td>${formatDate(r.vig_desde)} - ${formatDate(r.vig_hasta)}</td>
                <td>${r.estado || ''}</td>
                <td>${r.sub_agente || ''}</td>
            </tr>
        `).join('');
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        // Assuming dateStr is 'YYYY-MM-DD' or ISO
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('es-PE');
    }

    function formatMoney(amount) {
        if (amount === null || amount === undefined) return '';
        return parseFloat(amount).toFixed(2);
    }
}

reporteDiario();
