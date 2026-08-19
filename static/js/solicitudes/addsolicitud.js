// Inicializa el modal "Añadir Solicitud"
(function () {
  const form = document.getElementById('addSolicitudForm');
  if (!form) return;

  const modalEl = document.getElementById('addSolicitudModal');
  const clienteInput = document.getElementById('sol_cliente');
  const clienteList = document.getElementById('sol_clientes_list');
  let clienteSearchTimer = null;

  modalEl.addEventListener('show.bs.modal', () => {
    const el = document.getElementById('sol_fecha_registro_preview');
    if (el) {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, '0');
      el.textContent = `${pad(now.getDate())}/${pad(now.getMonth() + 1)}/${now.getFullYear()} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
    }
  });

  if (clienteInput && clienteList) {
    clienteInput.addEventListener('input', () => {
      clearTimeout(clienteSearchTimer);
      const q = clienteInput.value.trim();
      if (q.length < 2) return;
      clienteSearchTimer = setTimeout(async () => {
        try {
          const resp = await fetch(`/api/clientes/search?q=${encodeURIComponent(q)}`);
          const result = await resp.json();
          clienteList.innerHTML = '';
          (result.rows || []).forEach((row) => {
            const opt = document.createElement('option');
            opt.value = row.razon_social || row.nombre || '';
            clienteList.appendChild(opt);
          });
        } catch (err) {
          console.error('Error buscando clientes:', err);
        }
      }, 300);
    });
  }

  const requiredIds = ['sol_tipo_operacion', 'sol_fecha_solicitud', 'sol_ubicacion', 'sol_prioridad', 'sol_gestor'];

  function validateRequired() {
    let ok = true;
    requiredIds.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (!el.value.trim()) {
        ok = false;
        el.classList.add('is-invalid');
      } else {
        el.classList.remove('is-invalid');
      }
    });
    return ok;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateRequired()) {
      alert('Por favor, completa los campos obligatorios marcados con *.');
      return;
    }

    const submitBtn = document.getElementById('btnGuardarSolicitud');
    submitBtn.disabled = true;

    try {
      const resp = await fetch('/solicitudes/add', {
        method: 'POST',
        body: new FormData(form),
      });
      const result = await resp.json().catch(() => ({}));
      if (!resp.ok || !result.ok) {
        throw new Error((result.errors && result.errors.join(', ')) || 'Error al guardar');
      }

      alert(`Solicitud TI-${result.numero_ti} guardada correctamente.`);
      const modal = bootstrap.Modal.getInstance(modalEl);
      modal && modal.hide();
      form.reset();
      window.location.reload();
    } catch (err) {
      alert(`Ocurrió un error guardando la solicitud: ${err.message}`);
    } finally {
      submitBtn.disabled = false;
    }
  });
})();
