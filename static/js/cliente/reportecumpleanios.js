document.addEventListener('DOMContentLoaded', () => {
    const filtroMes = document.getElementById('filtro-mes');
    const filtroDias = document.getElementById('filtro-dias');
    const filtroOrden = document.getElementById('filtro-orden');
    const btnBuscar = document.getElementById('btn-buscar');
    const tbody = document.getElementById('tbody-resultados');
    const chipsEstado = Array.from(document.querySelectorAll('.estado-chip'));

    const countHoy = document.getElementById('count-hoy');
    const countProximos = document.getElementById('count-proximos');
    const countMesActual = document.getElementById('count-mes-actual');
    const countTotal = document.getElementById('count-total');

    let estadoActual = 'todos';

    const meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ];

    // Estado inicial: no consultar hasta que el usuario lo solicite.
    tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">Seleccione filtros y pulse Buscar</td></tr>';

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function updateEstadoChip() {
        chipsEstado.forEach((chip) => {
            chip.classList.toggle('active', chip.dataset.estado === estadoActual);
        });
    }

    function actualizarResumen(rows) {
        const hoy = rows.filter((r) => r.estado_cumple === 'hoy').length;
        const proximos = rows.filter((r) => r.estado_cumple === 'proximo').length;
        const mesActual = rows.filter((r) => r.mes && Number(r.mes) === (new Date().getMonth() + 1)).length;

        countHoy.textContent = String(hoy);
        countProximos.textContent = String(proximos);
        countMesActual.textContent = String(mesActual);
        countTotal.textContent = String(rows.length);
    }

    function estadoBadge(estado, dias) {
        if (estado === 'hoy') {
            return '<span class="metric-pill estado-badge estado-hoy">Hoy</span>';
        }
        if (estado === 'proximo') {
            return '<span class="metric-pill estado-badge estado-proximo">Próximo</span>';
        }
        if (estado === 'mes_actual') {
            return '<span class="metric-pill estado-badge estado-mes">Este mes</span>';
        }
        return '<span class="metric-pill estado-badge estado-futuro">Futuro</span>';
    }

    function contactoRapido(telefonoRaw) {
        const telefono = String(telefonoRaw || '').trim();
        if (!telefono) {
            return '<span class="text-muted">-</span>';
        }

        const digitos = telefono.replace(/\D/g, '');
        const telHref = `tel:${digitos || telefono}`;
        const telBtn = `
            <a href="${telHref}" class="btn btn-sm btn-outline-secondary contacto-btn" title="Llamar">
                <i class="bi bi-telephone-fill" aria-hidden="true"></i>
                <span>Llamar</span>
            </a>
        `;

        if (digitos.length >= 9) {
            const waHref = `https://wa.me/51${digitos}`;
            const waBtn = `
                <a href="${waHref}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-success contacto-btn" title="WhatsApp">
                    <i class="bi bi-whatsapp" aria-hidden="true"></i>
                    <span>WhatsApp</span>
                </a>
            `;
            return `<div class="contacto-actions">${telBtn}${waBtn}</div>`;
        }

        return `<div class="contacto-actions">${telBtn}</div>`;
    }

    async function cargarCumpleanos() {
        // Mostrar spinner o limpiar
        tbody.innerHTML = '<tr><td colspan="12" class="text-center">Cargando...</td></tr>';

        const mes = filtroMes.value;
        const dias = filtroDias.value;
        const orden = filtroOrden.value;
        let url = window.CUMPLEANOS_API_URL || '/api/reportes/cumpleanos';
        const params = new URLSearchParams();
        if (mes) {
            params.append('mes', mes);
        }
        if (estadoActual) {
            params.append('estado', estadoActual);
        }
        if (dias) {
            params.append('dias', dias);
        }
        if (orden) {
            params.append('orden', orden);
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
                tbody.innerHTML = `<tr><td colspan="12" class="text-danger text-center">Error: ${escapeHtml(data.error)}</td></tr>`;
                return;
            }

            const rows = data.rows || [];
            actualizarResumen(rows);

            if (rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">No se encontraron resultados</td></tr>';
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
                const dayHtml = r.dia ? `<span class="metric-pill day-value">${r.dia}</span>` : '';
                const monthHtml = mesNombre ? `<span class="metric-pill month-value">${mesNombre}</span>` : '';
                const ageHtml = (r.edad !== null && r.edad !== undefined && r.edad !== '') ? `<span class="metric-pill age-badge">${r.edad}</span>` : '';
                const diasFaltan = Number.isInteger(r.dias_para_cumple) ? r.dias_para_cumple : parseInt(r.dias_para_cumple, 10);
                const faltanHtml = Number.isInteger(diasFaltan)
                    ? `<span class="metric-pill faltan-badge">${diasFaltan} día${diasFaltan === 1 ? '' : 's'}</span>`
                    : '-';

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

                if (r.estado_cumple) {
                    tr.classList.add(`estado-row-${r.estado_cumple}`);
                }

                const telefono = r.telefono || '';
                const documento = `${r.tipo_documento || ''} ${r.numero_documento || ''}`.trim();

                tr.innerHTML = `
                    <td>${escapeHtml(r.idCliente)}</td>
                    <td>${escapeHtml(r.razon_social || '')}</td>
                    <td>${escapeHtml(documento)}</td>
                    <td>${escapeHtml(r.fecha_nacimiento || '')}</td>
                    <td class="text-center">${dayHtml}</td>
                    <td class="text-center">${monthHtml}</td>
                    <td class="text-center">${ageHtml}</td>
                    <td class="text-center">${faltanHtml}</td>
                    <td class="text-center">${estadoBadge(r.estado_cumple, diasFaltan)}</td>
                    <td>${escapeHtml(r.email || '')}</td>
                    <td>${escapeHtml(telefono)}</td>
                    <td class="text-center">${contactoRapido(telefono)}</td>
                `;
                tbody.appendChild(tr);
            });

        } catch (error) {
            console.error(error);
            tbody.innerHTML = `<tr><td colspan="12" class="text-danger text-center">Error de red: ${escapeHtml(error.message)}</td></tr>`;
        }
    }

    chipsEstado.forEach((chip) => {
        chip.addEventListener('click', () => {
            estadoActual = chip.dataset.estado || 'todos';
            updateEstadoChip();
        });
    });

    btnBuscar.addEventListener('click', cargarCumpleanos);
    updateEstadoChip();
});

