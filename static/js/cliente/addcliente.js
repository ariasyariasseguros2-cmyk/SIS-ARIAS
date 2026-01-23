// Inicializa manejadores del modal "Añadir Clientes"
(function () {
  const form = document.getElementById('addClienteForm');
  if (!form) return;

  const modalEl = document.getElementById('addClienteModal');

      // Cargar subagentes
  async function loadSubagentes() {
    const selectSubAgente = document.getElementById('subAgente');
    if (!selectSubAgente) return;

    try {
      const resp = await fetch('/api/subagentes');
      const result = await resp.json();

      if (result.ok && result.subagentes) {
         selectSubAgente.innerHTML = '<option value="">Seleccionar...</option>';

        result.subagentes.forEach(subagente => {
          const option = document.createElement('option');
          option.value = subagente;
          option.textContent = subagente;
          selectSubAgente.appendChild(option);
        });

        console.log('Subagentes cargados:', result.subagentes.length);
      }
    } catch (err) {
      console.error('Error cargando subagentes:', err);
    }
  }


  if (modalEl) {
    modalEl.addEventListener('show.bs.modal', () => {
      loadSubagentes();
      setupRealtimeValidation();
    });
  }

  // Validación en tiempo real
  function setupRealtimeValidation() {
    // Validar número de documento
    const numeroDoc = document.getElementById('numeroDocumento');
    if (numeroDoc) {
      numeroDoc.addEventListener('input', (e) => {
        // Solo permitir números
        e.target.value = e.target.value.replace(/[^0-9]/g, '');

        const val = e.target.value;
        if (val.length >= 8 && val.length <= 11) {
          e.target.classList.remove('is-invalid');
          e.target.classList.add('is-valid');
        } else if (val.length > 0) {
          e.target.classList.remove('is-valid');
        }
      });
    }

    // Validar teléfonos
    const telefono1 = document.getElementById('telefono1');
    if (telefono1) {
      telefono1.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/[^0-9]/g, '');
        if (e.target.value.length === 9) {
          e.target.classList.remove('is-invalid');
          e.target.classList.add('is-valid');
        } else if (e.target.value.length > 0) {
          e.target.classList.remove('is-valid');
        }
      });
    }

    const telefono2 = document.getElementById('telefono2');
    if (telefono2) {
      telefono2.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/[^0-9]/g, '');
        const len = e.target.value.length;
        if (len === 0 || (len >= 7 && len <= 9)) {
          e.target.classList.remove('is-invalid');
          if (len > 0) e.target.classList.add('is-valid');
        } else {
          e.target.classList.remove('is-valid');
        }
      });
    }

    const contactoTel = document.getElementById('contactoTelefono');
    if (contactoTel) {
      contactoTel.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/[^0-9]/g, '');
        const len = e.target.value.length;
        if (len >= 7 && len <= 9) {
          e.target.classList.remove('is-invalid');
          e.target.classList.add('is-valid');
        } else if (len > 0) {
          e.target.classList.remove('is-valid');
        }
      });
    }

    // Validar emails
    const email = document.getElementById('email');
    if (email) {
      email.addEventListener('blur', (e) => {
        const val = e.target.value.trim();
        if (val && /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(val)) {
          e.target.classList.remove('is-invalid');
          e.target.classList.add('is-valid');
        } else if (val) {
          e.target.classList.remove('is-valid');
          e.target.classList.add('is-invalid');
        }
      });
    }

    const contactoEmail = document.getElementById('contactoEmail');
    if (contactoEmail) {
      contactoEmail.addEventListener('blur', (e) => {
        const val = e.target.value.trim();
        if (val && /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(val)) {
          e.target.classList.remove('is-invalid');
          e.target.classList.add('is-valid');
        } else if (val) {
          e.target.classList.remove('is-valid');
          e.target.classList.add('is-invalid');
        }
      });
    }

    // Validar textos requeridos
    const requiredTextFields = ['razonSocial', 'direccion', 'distrito', 'contactoNombre'];
    requiredTextFields.forEach(id => {
      const field = document.getElementById(id);
      if (field) {
        field.addEventListener('blur', (e) => {
          const val = e.target.value.trim();
          if (val.length >= 3) {
            e.target.classList.remove('is-invalid');
            e.target.classList.add('is-valid');
          } else if (val.length > 0) {
            e.target.classList.remove('is-valid');
            e.target.classList.add('is-invalid');
          }
        });
      }
    });

    // Validar select requerido
    const subAgente = document.getElementById('subAgente');
    if (subAgente) {
      subAgente.addEventListener('change', (e) => {
        if (e.target.value) {
          e.target.classList.remove('is-invalid');
          e.target.classList.add('is-valid');
        } else {
          e.target.classList.remove('is-valid');
        }
      });
    }

    // Validar vencimiento de licencia (no puede ser menor a la fecha actual)
    const vencimientoLicencia = document.getElementById('vencimientoLicencia');
    if (vencimientoLicencia) {
      // Establecer fecha mínima como hoy
      const today = new Date().toISOString().split('T')[0];
      vencimientoLicencia.setAttribute('min', today);

      vencimientoLicencia.addEventListener('change', (e) => {
        const selectedDate = e.target.value;
        if (selectedDate) {
          const selected = new Date(selectedDate);
          const now = new Date();
          now.setHours(0, 0, 0, 0); // Resetear horas para comparar solo fechas

          if (selected < now) {
            e.target.classList.remove('is-valid');
            e.target.classList.add('is-invalid');
            e.target.setCustomValidity('La fecha de vencimiento debe ser mayor o igual a la fecha actual');
          } else {
            e.target.classList.remove('is-invalid');
            e.target.classList.add('is-valid');
            e.target.setCustomValidity('');
          }
        }
      });

      vencimientoLicencia.addEventListener('blur', (e) => {
        if (e.target.value) {
          e.target.dispatchEvent(new Event('change'));
        }
      });
    }

    // Agregar feedback visual a campos opcionales cuando se llenan
    const optionalFieldsWithFeedback = [
      'profesion', 'fechaIngreso', 'cumpleanios', 'licenciaConducir',
      'grupoEconomico', 'giroNegocio', 'referencia', 'recomendadoPor'
    ];

    optionalFieldsWithFeedback.forEach(id => {
      const field = document.getElementById(id);
      if (field) {
        const eventType = field.tagName === 'SELECT' ? 'change' : 'input';
        field.addEventListener(eventType, (e) => {
          if (e.target.value && e.target.value.trim() !== '') {
            e.target.classList.add('is-valid');
            e.target.classList.remove('is-invalid');
          } else {
            e.target.classList.remove('is-valid', 'is-invalid');
          }
        });
      }
    });
  }

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
    const payload = {};

    // Procesar todos los campos del formulario
    for (const [key, value] of fd.entries()) {
      payload[key] = value;
    }

    // Normaliza radios booleanos para notificaciones
    payload.recibirNotificaciones = (fd.get('notif') || 'SI') === 'SI';

    // Asegurar que todos los campos del formulario estén incluidos
    // Datos de identificación
    payload.tipoPersona = document.getElementById('tipoPersona')?.value || '';
    payload.razonSocial = document.getElementById('razonSocial')?.value || '';
    payload.tipoDocumento = document.querySelector('input[name="tipoDocumento"]:checked')?.value || '';
    payload.numeroDocumento = document.getElementById('numeroDocumento')?.value || '';

    // Ubicación y contacto
    payload.direccion = document.getElementById('direccion')?.value || '';
    payload.departamento = document.getElementById('departamento')?.value || '';
    payload.provincia = document.getElementById('provincia')?.value || '';
    payload.distrito = document.getElementById('distrito')?.value || '';
    payload.email = document.getElementById('email')?.value || '';
    payload.telefono1 = document.getElementById('telefono1')?.value || '';
    payload.telefono2 = document.getElementById('telefono2')?.value || '';

    // Perfil y clasificación
    payload.profesion = document.getElementById('profesion')?.value || '';
    payload.fechaIngreso = document.getElementById('fechaIngreso')?.value || '';
    payload.cumpleanios = document.getElementById('cumpleanios')?.value || '';
    payload.licenciaConducir = document.getElementById('licenciaConducir')?.value || '';
    payload.vencimientoLicencia = document.getElementById('vencimientoLicencia')?.value || '';
    payload.subAgente = document.getElementById('subAgente')?.value || '';
    payload.grupoEconomico = document.getElementById('grupoEconomico')?.value || '';
    payload.giroNegocio = document.getElementById('giroNegocio')?.value || '';
    payload.referencia = document.getElementById('referencia')?.value || '';
    payload.recomendadoPor = document.getElementById('recomendadoPor')?.value || '';

    // Persona de contacto
    payload.contactoNombre = document.getElementById('contactoNombre')?.value || '';
    payload.contactoEmail = document.getElementById('contactoEmail')?.value || '';
    payload.contactoTelefono = document.getElementById('contactoTelefono')?.value || '';

    // Información adicional - Siniestralidad
    payload.siniestrosReportados = document.getElementById('siniestrosReportados')?.value || '';
    payload.ultimoSiniestro = document.getElementById('ultimoSiniestro')?.value || '';
    payload.detalleSiniestros = document.getElementById('detalleSiniestros')?.value || '';

    payload.referenciasInteres = document.getElementById('referenciasInteres')?.value || '';
    payload.preferencias = document.getElementById('preferencias')?.value || '';
    payload.notasInteres = document.getElementById('notasInteres')?.value || '';

    payload.masInformacion = document.getElementById('masInformacion')?.value || '';

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
    let body;
    let headers = {};

    // Verificar si hay archivo PDF seleccionado
    const file = pdfFileInput && pdfFileInput.files[0];
    if (file) {
      const formData = new FormData();
      // Agregar todos los campos del payload al FormData
      for (const key in payload) {
        if (payload.hasOwnProperty(key)) {
          formData.append(key, payload[key]);
        }
      }
      formData.append('pdf_file', file);
      body = formData;
      // No establecer Content-Type explícitamente para FormData, el navegador lo hace con boundary
    } else {
      body = JSON.stringify(payload);
      headers['Content-Type'] = 'application/json';
    }

    try {
      const resp = await fetch('/clientes/add', {
        method: 'POST',
        headers: headers,
        body: body
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
    let body;
    let headers = {};

    // Verificar si hay archivo PDF seleccionado
    const file = pdfFileInput && pdfFileInput.files[0];
    if (file) {
      const formData = new FormData();
      for (const key in payload) {
        if (payload.hasOwnProperty(key)) {
          formData.append(key, payload[key]);
        }
      }
      formData.append('pdf_file', file);
      body = formData;
    } else {
      body = JSON.stringify(payload);
      headers['Content-Type'] = 'application/json';
    }

    try {
      const resp = await fetch('/clientes/add', {
        method: 'POST',
        headers: headers,
        body: body
      });
      const result = await resp.json().catch(() => ({}));
      if (!resp.ok || !result.ok) {
        const msg = (result.errors && result.errors.join(', ')) || 'Error al guardar';
        throw new Error(msg);
      }
      alert('Cliente guardado. Puedes añadir otro.');
      form.reset();
      form.classList.remove('was-validated');
      form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
      form.querySelectorAll('.is-valid').forEach(el => el.classList.remove('is-valid'));
      if (pdfFileInput) pdfFileInput.value = '';
      if (pdfStatus) pdfStatus.style.display = 'none';
      if (btnClearPDF) btnClearPDF.style.display = 'none';
    } catch (err) {
      console.error(err);
      alert(`Error: ${err.message}`);
    }
  });
})();