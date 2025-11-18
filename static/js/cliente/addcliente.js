// Inicializa manejadores del modal "Añadir Clientes"
(function () {
  const form = document.getElementById('addClienteForm');
  if (!form) return;

  const modalEl = document.getElementById('addClienteModal');

  function collectData() {
    const fd = new FormData(form);
    // Convierte FormData a objeto plano
    const payload = Object.fromEntries(fd.entries());
    // Normaliza radios booleanos
    payload.recibirNotificaciones = (fd.get('notif') || 'SI') === 'SI';
    return payload;
  }

  function validateRequired() {
    const requiredIds = [
      'tipoPersona',
      'razonSocial',
      'numeroDocumento',
      'direccion',
      'distrito',
      'departamento',
      'provincia',
      'telefono1',
      'email',
      'subAgente',
      'contactoNombre',
      'contactoEmail',
      'contactoTelefono'
    ];
    let ok = true;
    requiredIds.forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      const val = (el.value || '').trim();
      if (!val) {
        ok = false;
        el.classList.add('is-invalid');
      } else {
        el.classList.remove('is-invalid');
      }
    });
    return ok;
  }

  // Envío principal
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateRequired()) {
      alert('Por favor, completa los campos obligatorios marcados con *.');
      return;
    }

    const payload = collectData();

    try {
      // Si tienes un endpoint backend, descomenta lo siguiente y ajusta la URL:
      // const resp = await fetch('/clientes/add', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(payload)
      // });
      // if (!resp.ok) throw new Error('Error al guardar');
      // const result = await resp.json();

      console.log('Cliente a guardar:', payload);
      alert('Cliente guardado (demo). Integra el endpoint para persistir.');
      const modal = bootstrap.Modal.getInstance(modalEl);
      modal && modal.hide();
      form.reset();
    } catch (err) {
      console.error(err);
      alert('Ocurrió un error guardando el cliente.');
    }
  });

  // Guardar y añadir otro
  const btnGuardarYAgregarOtro = document.getElementById('btnGuardarYAgregarOtro');
  btnGuardarYAgregarOtro?.addEventListener('click', async () => {
    if (!validateRequired()) {
      alert('Por favor, completa los campos obligatorios marcados con *.');
      return;
    }
    const payload = collectData();
    console.log('Cliente a guardar (añadir otro):', payload);
    alert('Cliente guardado (demo). Continúa con el siguiente.');
    form.reset();
    // Mantener el modal abierto para añadir otro
  });
})();