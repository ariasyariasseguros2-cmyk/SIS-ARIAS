let polizaActual = '';
let siniestros = [];
let siniestrosFiltrados = [];
let modalSiniestro;

document.addEventListener('DOMContentLoaded', function() {
    polizaActual = document.getElementById('polizaCertif').textContent;

    modalSiniestro = new bootstrap.Modal(document.getElementById('modalSiniestro'));

    cargarSiniestros();

    document.getElementById('btnAnadirSiniestro').addEventListener('click', abrirModalNuevo);
    document.getElementById('formSiniestro').addEventListener('submit', guardarSiniestro);
    document.getElementById('searchInput').addEventListener('input', filtrarSiniestros);
});

async function cargarSiniestros() {
    try {
        const response = await fetch(`/api/siniestros/poliza?poliza=${encodeURIComponent(polizaActual)}`);
        const data = await response.json();
        siniestros = data || [];
        siniestrosFiltrados = siniestros;
        renderizarTabla(siniestrosFiltrados);
        actualizarContador();
    } catch (error) {
        console.error('Error al cargar siniestros:', error);
        mostrarError('Error al cargar los siniestros');
    }
}

function renderizarTabla(data) {
    const tbody = document.getElementById('siniestrosTableBody');

    if (data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="15" class="text-center text-muted py-4">No tenemos datos disponibles</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = data.map(siniestro => `
        <tr>
            <td>${siniestro.id || ''}</td>
            <td>${siniestro.contratante || ''}</td>
            <td>${siniestro.poliza || ''}</td>
            <td>${siniestro.cia || ''}</td>
            <td>${siniestro.fec_stro || ''}</td>
            <td>${siniestro.causa || ''}</td>
            <td>${siniestro.siniestro_no || ''}</td>
            <td class="text-end">${formatNumber(siniestro.provision) || '0.00'}</td>
            <td><span class="badge badge-${getEstadoClass(siniestro.estado)}">${siniestro.estado || 'PENDIENTE'}</span></td>
            <td>${siniestro.ejec || ''}</td>
            <td>${siniestro.ramo || ''}</td>
            <td>${siniestro.placa || ''}</td>
            <td>${siniestro.fec_gestion || ''}</td>
            <td>${siniestro.prox_gestion || ''}</td>
            <td class="text-end">
                <div class="chips-row">
                    <span class="chip chip-primary" role="button" onclick="editarSiniestro(${siniestro.id})" title="Editar">EDITAR</span>
                    <span class="chip chip-danger" role="button" onclick="eliminarSiniestro(${siniestro.id})" title="Eliminar">ELIMINAR</span>
                </div>
            </td>
        </tr>
    `).join('');
}

function getEstadoClass(estado) {
    const clases = {
        'PENDIENTE': 'warning',
        'EN_PROCESO': 'info',
        'CERRADO': 'success',
        'RECHAZADO': 'danger'
    };
    return clases[estado] || 'secondary';
}

function formatNumber(num) {
    if (!num) return '0.00';
    return parseFloat(num).toFixed(2);
}

function abrirModalNuevo() {
    document.getElementById('modalTitle').textContent = 'Añadir Siniestro';
    document.getElementById('formSiniestro').reset();
    document.getElementById('siniestroId').value = '';

    document.getElementById('poliza').value = document.getElementById('polizaCertif').textContent.trim();
    document.getElementById('contratante').value = document.getElementById('asegurado').textContent.trim();
    document.getElementById('cia').value = document.getElementById('compania').textContent.trim();
    document.getElementById('ramo').value = document.getElementById('materiaAsegurada').textContent.trim();
    document.getElementById('estado').value = 'PENDIENTE';

    modalSiniestro.show();
}

async function editarSiniestro(id) {
    try {
        const response = await fetch(`/api/siniestros/${id}`);
        const siniestro = await response.json();

        console.log('Datos del siniestro:', siniestro);
        console.log('fec_stro:', siniestro.fec_stro, 'tipo:', typeof siniestro.fec_stro);
        console.log('fec_gestion:', siniestro.fec_gestion, 'tipo:', typeof siniestro.fec_gestion);
        console.log('prox_gestion:', siniestro.prox_gestion, 'tipo:', typeof siniestro.prox_gestion);

        document.getElementById('modalTitle').textContent = 'Editar Siniestro';
        document.getElementById('siniestroId').value = siniestro.id;
        document.getElementById('contratante').value = siniestro.contratante || '';
        document.getElementById('poliza').value = siniestro.poliza || '';
        document.getElementById('cia').value = siniestro.cia || '';
        document.getElementById('ramo').value = siniestro.ramo || '';

        const fecStroFormatted = formatDateForInput(siniestro.fec_stro);
        const fecGestionFormatted = formatDateForInput(siniestro.fec_gestion);
        const proxGestionFormatted = formatDateForInput(siniestro.prox_gestion);

        console.log('Fechas formateadas:');
        console.log('fecStro formatted:', fecStroFormatted);
        console.log('fecGestion formatted:', fecGestionFormatted);
        console.log('proxGestion formatted:', proxGestionFormatted);

        document.getElementById('fecStro').value = fecStroFormatted;
        document.getElementById('siniestroNo').value = siniestro.siniestro_no || '';
        document.getElementById('causa').value = siniestro.causa || '';
        document.getElementById('provision').value = siniestro.provision || '0.00';
        document.getElementById('estado').value = siniestro.estado || 'PENDIENTE';
        document.getElementById('placa').value = siniestro.placa || '';
        document.getElementById('ejec').value = siniestro.ejec || '';
        document.getElementById('fecGestion').value = fecGestionFormatted;
        document.getElementById('proxGestion').value = proxGestionFormatted;

        modalSiniestro.show();
    } catch (error) {
        console.error('Error al cargar siniestro:', error);
        mostrarError('Error al cargar el siniestro');
    }
}

async function guardarSiniestro(event) {
    event.preventDefault();

    const id = document.getElementById('siniestroId').value;
    const data = {
        contratante: document.getElementById('contratante').value,
        poliza: document.getElementById('poliza').value,
        cia: document.getElementById('cia').value,
        ramo: document.getElementById('ramo').value,
        fec_stro: document.getElementById('fecStro').value,
        siniestro_no: document.getElementById('siniestroNo').value,
        causa: document.getElementById('causa').value,
        provision: parseFloat(document.getElementById('provision').value) || 0.00,
        estado: document.getElementById('estado').value,
        placa: document.getElementById('placa').value,
        ejec: document.getElementById('ejec').value,
        fec_gestion: document.getElementById('fecGestion').value || null,
        prox_gestion: document.getElementById('proxGestion').value || null
    };

    try {
        const url = id ? `/api/siniestros/${id}` : '/api/siniestros';
        const method = id ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            modalSiniestro.hide();
            cargarSiniestros();
            mostrarExito(id ? 'Siniestro actualizado exitosamente' : 'Siniestro creado exitosamente');
        } else {
            const error = await response.json();
            mostrarError(error.error || 'Error al guardar');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al guardar el siniestro');
    }
}

async function eliminarSiniestro(id) {
    if (!confirm('¿Está seguro de eliminar este siniestro?')) {
        return;
    }

    try {
        const response = await fetch(`/api/siniestros/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            cargarSiniestros();
            mostrarExito('Siniestro eliminado exitosamente');
        } else {
            const error = await response.json();
            mostrarError(error.error || 'Error al eliminar');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al eliminar el siniestro');
    }
}

function filtrarSiniestros() {
    const texto = document.getElementById('searchInput').value.toLowerCase();
    siniestrosFiltrados = siniestros.filter(s =>
        (s.contratante || '').toLowerCase().includes(texto) ||
        (s.siniestro_no || '').toLowerCase().includes(texto) ||
        (s.placa || '').toLowerCase().includes(texto) ||
        (s.causa || '').toLowerCase().includes(texto)
    );
    renderizarTabla(siniestrosFiltrados);
    actualizarContador();
}

function actualizarContador() {
    const total = siniestrosFiltrados.length;
    document.getElementById('totalRegistros').textContent =
        `Total de registros: 0 a ${total} de ${total}`;
}

function formatDateForInput(dateStr) {
    if (!dateStr || dateStr === 'null' || dateStr === 'NULL') return '';

    const str = dateStr.trim();

    // Si ya está en formato YYYY-MM-DD (formato ISO), retornarlo directamente
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
        return str;
    }

    // Si está en formato DD/MM/YYYY
    if (str.includes('/')) {
        const parts = str.split('/');
        if (parts.length === 3) {
            const day = parts[0].padStart(2, '0');
            const month = parts[1].padStart(2, '0');
            const year = parts[2];
            return `${year}-${month}-${day}`;
        }
    }

    return '';
}

function mostrarExito(mensaje) {
    alert(mensaje);
}

function mostrarError(mensaje) {
    alert(mensaje);
}
