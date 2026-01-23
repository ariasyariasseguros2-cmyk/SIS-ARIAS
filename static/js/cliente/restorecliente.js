document.addEventListener('DOMContentLoaded', function() {
    function postRestore(id) {
        console.log('[restorecliente] iniciando fetch /clientes/restore id=', id);
        return fetch('/clientes/restore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            body: JSON.stringify({ idCliente: id })
        });
    }

    document.querySelectorAll('.btn-restore-cliente').forEach(function(btn) {
        btn.addEventListener('click', function(event) {
            console.log('[restorecliente] click handler fired for element', this);
            event.preventDefault();
            // Evitar que otros handlers sean ejecutados
            if (event.stopImmediatePropagation) event.stopImmediatePropagation();
            event.stopPropagation();

            var id = this.getAttribute('data-id');
            var nombreEl = this.closest('tr').querySelector('td:nth-child(2)');
            var nombre = nombreEl ? nombreEl.innerText.trim() : '';
            if (!confirm('¿Restaurar cliente "' + nombre + '"?')) return;

            this.disabled = true;
            var oldHtml = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Restaurando...';
            var el = this;

            postRestore(id).then(function(response) {
                // Si el servidor devuelve 401 -> redirigir a login
                if (response.status === 401) {
                    window.location.href = '/login';
                    return null;
                }
                // Intentar parsear JSON; si falla, leer texto para depuración
                return response.text().then(function(text) {
                    try {
                        var json = JSON.parse(text || '{}');
                        return { status: response.status, body: json };
                    } catch (e) {
                        console.warn('restorecliente: respuesta no JSON', text);
                        return { status: response.status, body: null, text: text };
                    }
                });
            }).then(function(res) {
                if (!res) return; // ya redirigió

                if (res.status >= 200 && res.status < 300 && res.body && res.body.ok) {
                    el.closest('tr').remove();
                    alert('Cliente restaurado correctamente');
                } else {
                    var msg = 'Error al restaurar';
                    if (res.body && res.body.errors) msg = res.body.errors.join('\n');
                    else if (res.text) msg = res.text;
                    alert(msg);
                    el.disabled = false;
                    el.innerHTML = oldHtml;
                }
            }).catch(function(err) {
                console.error('restorecliente fetch error:', err);
                var msg = 'Error de red: ' + (err && err.message ? err.message : err);
                if (typeof navigator !== 'undefined' && !navigator.onLine) {
                    msg = 'No hay conexión de red. Verifica tu conexión e intenta nuevamente.';
                }
                alert(msg);
                el.disabled = false;
                el.innerHTML = oldHtml;
            });
        });
    });
});
