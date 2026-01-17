// Inicializa manejadores del modal "Añadir Clientes"
(function () {
  const form = document.getElementById('addClienteForm');
  if (!form) return;

  const modalEl = document.getElementById('addClienteModal');

  // extractor de pdf
  const pdfFileInput = document.getElementById('pdfFileInput');
  const btnExtractPDF = document.getElementById('btnExtractPDF');
  const btnClearPDF = document.getElementById('btnClearPDF');
  const pdfStatus = document.getElementById('pdfExtractionStatus');

  if (btnExtractPDF && pdfFileInput) {
    btnExtractPDF.addEventListener('click', async () => {
      const file = pdfFileInput.files[0];
      if (!file) {
        alert('Por favor, selecciona un archivo PDF.');
        return;
      }

      if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('El archivo debe ser un PDF.');
        return;
      }

      // Mostrar estado de carga
      pdfStatus.style.display = 'block';
      pdfStatus.innerHTML = '<span class="text-info"><i class="bi-hourglass-split"></i> Procesando PDF...</span>';
      btnExtractPDF.disabled = true;

      try {
        const formData = new FormData();
        formData.append('pdf_file', file);

        const resp = await fetch('/clientes/extract-pdf', {
          method: 'POST',
          body: formData
        });

        const result = await resp.json().catch(() => ({}));

        if (!resp.ok || !result.ok) {
          const msg = (result.errors && result.errors.join(', ')) || 'Error al procesar PDF';
          throw new Error(msg);
        }


        // Rellenar los campos del formulario con los datos extraídos
        const data = result.data || {};
        fillFormWithData(data);

        pdfStatus.innerHTML = '<span class="text-success"><i class="bi-check-circle"></i> Datos extraídos correctamente. Revisa y completa los campos faltantes.</span>';
        btnClearPDF.style.display = 'inline-block';

        // Ocultar mensaje después de 5 segundos
        setTimeout(() => {
          pdfStatus.style.display = 'none';
        }, 5000);

      } catch (err) {
        console.error('Error extrayendo PDF:', err);
        pdfStatus.innerHTML = `<span class="text-danger"><i class="bi-exclamation-triangle"></i> ${err.message}</span>`;
      } finally {
        btnExtractPDF.disabled = false;
      }
    });

    // Botón para limpiar el PDF seleccionado
    if (btnClearPDF) {
      btnClearPDF.addEventListener('click', () => {
        pdfFileInput.value = '';
        pdfStatus.style.display = 'none';
        btnClearPDF.style.display = 'none';
      });
    }
  }

  // Rellenar Datos del formulario automaticamente con los datos extraidos del PDF
  function fillFormWithData(data) {

    clearAllFormFields();

    // Tipo de Persona
    if (data.tipoPersona) {
      const tipoSelect = document.getElementById('tipoPersona');
      if (tipoSelect) {
        tipoSelect.value = data.tipoPersona.toUpperCase();
      }
    }

    // Razón Social / Nombre
    if (data.razonSocial) {
      const razonInput = document.getElementById('razonSocial');
      if (razonInput) razonInput.value = data.razonSocial;
    }

    // Tipo de Documento (radio buttons)
    if (data.tipoDocumento) {
      const tipoDoc = data.tipoDocumento.toUpperCase();
      if (tipoDoc.includes('RUC')) {
        document.getElementById('docRUC')?.click();
      } else if (tipoDoc.includes('CEX') || tipoDoc.includes('CE')) {
        document.getElementById('docCEX')?.click();
      } else if (tipoDoc.includes('PAS')) {
        document.getElementById('docPAS')?.click();
      } else {
        document.getElementById('docDNI')?.click();
      }
    }

    // Número de Documento
    if (data.numeroDocumento) {
      const numDocInput = document.getElementById('numeroDocumento');
      if (numDocInput) numDocInput.value = data.numeroDocumento;
    }

    // Dirección
    if (data.direccion) {
      const dirInput = document.getElementById('direccion');
      if (dirInput) dirInput.value = data.direccion;
    }

    // Distrito
    if (data.distrito) {
      const distInput = document.getElementById('distrito');
      if (distInput) distInput.value = data.distrito;
    }

    // Provincia
    if (data.provincia) {
      const provInput = document.getElementById('provincia');
      if (provInput) provInput.value = data.provincia;
    }

    // Departamento
    if (data.departamento) {
      const deptInput = document.getElementById('departamento');
      if (deptInput) deptInput.value = data.departamento;
    }

    // Email
    if (data.email) {
      const emailInput = document.getElementById('email');
      if (emailInput) emailInput.value = data.email;
    }

    // Teléfonos
    if (data.telefono1) {
      const tel1Input = document.getElementById('telefono1');
      if (tel1Input) tel1Input.value = data.telefono1;
    }
    if (data.telefono2) {
      const tel2Input = document.getElementById('telefono2');
      if (tel2Input) tel2Input.value = data.telefono2;
    }

    // Resaltar campos rellenados
    highlightFilledFields();
  }


  function clearAllFormFields() {
    const textInputs = form.querySelectorAll('input[type="text"], input[type="email"], input[type="date"], textarea');
    textInputs.forEach(input => {
      input.value = '';
      input.classList.remove('is-invalid', 'border-success', 'border-2');
    });

    // Resetear selects a su valor por defecto
    const selects = form.querySelectorAll('select');
    selects.forEach(select => {
      if (select.id === 'tipoPersona') {
        select.value = 'NATURAL'; // Valor por defecto
      } else if (select.id === 'departamento') {
        select.value = 'LIMA';
      } else if (select.id === 'provincia') {
        select.value = 'LIMA';
      } else {
        select.selectedIndex = 0; // Primera opción
      }
    });

    // Resetear radio buttons a valores por defecto
    const docDNI = document.getElementById('docDNI');
    if (docDNI) docDNI.checked = true;

    const notifSi = document.getElementById('notifSi');
    if (notifSi) notifSi.checked = true;

    // Limpiar campos numéricos
    const numberInputs = form.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
      input.value = '';
    });
  }

  // Función para resaltar visualmente campos que fueron rellenados
  function highlightFilledFields() {
    const fields = [
      'tipoPersona', 'razonSocial', 'numeroDocumento', 'direccion',
      'distrito', 'provincia', 'departamento', 'email', 'telefono1', 'telefono2'
    ];
    fields.forEach(id => {
      const el = document.getElementById(id);
      if (el && el.value && el.value.trim() !== '') {
        el.classList.add('border-success', 'border-2');
        setTimeout(() => {
          el.classList.remove('border-success', 'border-2');
        }, 3000);
      }
    });
  }

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
      const resp = await fetch('/clientes/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await resp.json().catch(() => ({}));
      if (!resp.ok || !result.ok) {
        const msg = (result.errors && result.errors.join(', ')) || 'Error al guardar';
        throw new Error(msg);
      }

      alert('Cliente guardado correctamente.');
      const modal = bootstrap.Modal.getInstance(modalEl);
      modal && modal.hide();
      form.reset();
      // Limpiar estado del PDF
      if (pdfFileInput) pdfFileInput.value = '';
      if (pdfStatus) pdfStatus.style.display = 'none';
      if (btnClearPDF) btnClearPDF.style.display = 'none';
      // Recargar página para actualizar listado
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert(`Ocurrió un error guardando el cliente: ${err.message}`);
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
    try {
      const resp = await fetch('/clientes/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await resp.json().catch(() => ({}));
      if (!resp.ok || !result.ok) {
        const msg = (result.errors && result.errors.join(', ')) || 'Error al guardar';
        throw new Error(msg);
      }
      alert('Cliente guardado. Puedes añadir otro.');
      form.reset();
      // Limpiar estado del PDF
      if (pdfFileInput) pdfFileInput.value = '';
      if (pdfStatus) pdfStatus.style.display = 'none';
      if (btnClearPDF) btnClearPDF.style.display = 'none';
    } catch (err) {
      console.error(err);
      alert(`Error: ${err.message}`);
    }
  });
})();