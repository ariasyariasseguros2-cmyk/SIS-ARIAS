document.addEventListener('DOMContentLoaded', function () {
    const btnNuevo = document.getElementById('btnNuevoAjustador');
    const form = document.getElementById('ajustadorForm');
    const btnGuardar = document.getElementById('btnGuardarAjustador');
    const btnCancelar = document.getElementById('btnCancelarAjustador');

    if (btnNuevo) btnNuevo.addEventListener('click', () => { form.style.display = 'block'; form.scrollIntoView({behavior:'smooth'}); });
    if (btnCancelar) btnCancelar.addEventListener('click', () => { form.style.display = 'none'; });
    if (btnGuardar) btnGuardar.addEventListener('click', submitAjustador);

    loadAjustadores();
});

function loadAjustadores() {
    fetch('/ajustadores/list')
        .then(r => r.json())
        .then(data => {
            if (!data) return;
            const tbody = document.querySelector('#ajustadoresTable tbody');
            tbody.innerHTML = '';
            // La API devuelve { ok: true, rows: [...] }
            const rows = (data.rows && Array.isArray(data.rows)) ? data.rows : (Array.isArray(data) ? data : []);
            rows.forEach(r => {
                const codigo = (r.codigo && String(r.codigo).trim()) ? r.codigo : (r.abreviacion || '');
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${escapeHtml(r.nombre || '')}</td><td>${escapeHtml(r.abreviacion || '')}</td><td>${escapeHtml(codigo || '')}</td>`;
                tbody.appendChild(tr);
            });
        })
        .catch(e => console.error('Error cargando ajustadores', e));
}

function submitAjustador() {
    const nombre = document.getElementById('nombre').value.trim();
    const abreviacion = document.getElementById('abreviacion').value.trim();
    const codigo = document.getElementById('codigo').value.trim();

    const payload = { nombre, abreviacion, codigo };

    fetch('/ajustadores/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(resp => {
            if (resp.ok) {
                console.log('Ajustador guardado:', resp);
                document.getElementById('ajustadorForm').style.display = 'none';
                // limpiar
                document.getElementById('nombre').value = '';
                document.getElementById('abreviacion').value = '';
                document.getElementById('codigo').value = '';
                loadAjustadores();
            } else {
                if (resp.errors) {
                    console.error('Errores al guardar ajustador:', resp.errors);
                } else if (resp.error) {
                    console.error('Error al guardar ajustador:', resp.error);
                } else {
                    console.error('Error desconocido al guardar ajustador');
                }
            }
        })
        .catch(e => { console.error('Error al guardar ajustador', e); });
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&"'<>]/g, function (a) {
        return { '&': '&amp;', '"': '&quot;', "'": '&#39;', '<': '&lt;', '>': '&gt;' }[a];
    });
}
