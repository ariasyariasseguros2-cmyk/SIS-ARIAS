// Listado de Solicitudes: acción "Anular"
(function () {
  document.querySelectorAll('.btn-anular-solicitud').forEach(function (btn) {
    btn.addEventListener('click', async function () {
      const id = btn.dataset.id;
      if (!confirm('¿Anular esta solicitud?')) return;

      try {
        const resp = await fetch(`/solicitudes/${id}/anular`, { method: 'POST' });
        const result = await resp.json().catch(() => ({}));
        if (!resp.ok || !result.ok) {
          throw new Error((result.errors && result.errors.join(', ')) || 'Error al anular');
        }
        window.location.reload();
      } catch (err) {
        alert(`No se pudo anular la solicitud: ${err.message}`);
      }
    });
  });
})();
