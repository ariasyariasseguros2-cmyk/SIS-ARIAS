document.addEventListener('DOMContentLoaded', () => {
    const filtroMes = document.getElementById('filtro-mes');
    const btnBuscar = document.getElementById('btn-buscar');
    const tbody = document.getElementById('tbody-resultados');

    const meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];

    // Estado inicial: no consultar hasta que el usuario lo solicite.
    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">Seleccione filtros y pulse Buscar</td></tr>';

    async function cargarCumpleanos() {
        // Mostrar spinner o limpiar
        tbody.innerHTML = '<tr><td colspan="9" class="text-center">Cargando...</td></tr>';

        const mes = filtroMes.value;
        let url = window.CUMPLEANOS_API_URL || '/api/reportes/cumpleanos';
        const params = new URLSearchParams();
        if (mes) {
            params.append('mes', mes);
        }
        if ([...params].length > 0) {
            url += '?' + params.toString();
        }

        try {
            const res = await fetch(url);
            const data = await res.json();
            
            tbody.innerHTML = '';
            
            if (!data.ok) {
                console.error(data.error);
                tbody.innerHTML = `<tr><td colspan="9" class="text-danger text-center">Error: ${data.error}</td></tr>`;
                return;
            }

            const rows = data.rows || [];
            if (rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No se encontraron resultados</td></tr>';
                return;
            }

            rows.forEach(r => {
                const tr = document.createElement('tr');
                
                // Formatear mes nombre
                let mesNombre = '';
                if (r.mes && r.mes >= 1 && r.mes <= 12) {
                    mesNombre = meses[r.mes - 1];
                }
                // Badges para día/mes/edad
                const dayHtml = r.dia ? `<span class="day-badge">${r.dia}</span>` : '';
                const monthHtml = mesNombre ? `<span class="month-badge">${mesNombre}</span>` : '';
                const ageHtml = (r.edad !== null && r.edad !== undefined && r.edad !== '') ? `<span class="age-badge">${r.edad}</span>` : '';

                // Resaltar fila si hoy es el cumpleaños
                try {
                    const today = new Date();
                    const todayDay = today.getDate();
                    const todayMonth = today.getMonth() + 1;
                    if (r.dia && r.mes && parseInt(r.dia) === todayDay && parseInt(r.mes) === todayMonth) {
                        tr.classList.add('today-row');
                    }
                } catch (e) {
                    // Ignore
                }

                tr.innerHTML = `
                    <td>${r.idCliente}</td>
                    <td>${r.razon_social || ''}</td>
                    <td>${r.tipo_documento || ''} ${r.numero_documento || ''}</td>
                    <td>${r.fecha_nacimiento || ''}</td>
                    <td class="text-center">${dayHtml}</td>
                    <td class="text-center">${monthHtml}</td>
                    <td class="text-center">${ageHtml}</td>
                    <td>${r.email || ''}</td>
                    <td>${r.telefono || ''}</td>
                `;
                tbody.appendChild(tr);
            });

        } catch (error) {
            console.error(error);
            tbody.innerHTML = `<tr><td colspan="9" class="text-danger text-center">Error de red: ${error.message}</td></tr>`;
        }
    }

    btnBuscar.addEventListener('click', cargarCumpleanos);
});

