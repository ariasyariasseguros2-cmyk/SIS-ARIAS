let siniestros = [];
let siniestrosFiltrados = [];
let modalSiniestro;

document.addEventListener('DOMContentLoaded', function() {
    modalSiniestro = new bootstrap.Modal(document.getElementById('modalSiniestro'), {
        backdrop: 'static',
        keyboard: false
    });

    cargarSiniestros();

    document.getElementById('formSiniestro').addEventListener('submit', guardarSiniestro);
    document.getElementById('searchInput').addEventListener('input', filtrarSiniestros);

    // Limpiar el modal cuando se oculta
    document.getElementById('modalSiniestro').addEventListener('hidden.bs.modal', function() {
        document.getElementById('formSiniestro').reset();
        document.getElementById('siniestroId').value = '';
        document.getElementById('grupoRamoActual').value = '';
        document.getElementById('formularioDinamico').innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando formulario...</span>
                </div>
                <p class="mt-3 text-muted">Cargando formulario...</p>
            </div>
        `;
    });
});

// Nuevo helper: espera a que exista un elemento con el id dado o hasta timeout (ms)
function waitForElement(id, timeout = 2000) {
    return new Promise((resolve) => {
        const exists = document.getElementById(id);
        if (exists) return resolve(exists);
        const interval = 50;
        let elapsed = 0;
        const handle = setInterval(() => {
            const el = document.getElementById(id);
            if (el) {
                clearInterval(handle);
                return resolve(el);
            }
            elapsed += interval;
            if (elapsed >= timeout) {
                clearInterval(handle);
                return resolve(null);
            }
        }, interval);
    });
}

// Nuevo helper: pausa síncrona via Promise
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Mejorar parseMaybeJSON: intenta JSON.parse; si falla, intenta reemplazar comillas simples por dobles
function parseMaybeJSON(value) {
    if (!value) return null;
    if (typeof value === 'object') return value;
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (trimmed === 'null' || trimmed === 'NULL') return null;
        try {
            return JSON.parse(trimmed);
        } catch (e) {
            try {
                const replaced = trimmed.replace(/'/g, '"');
                return JSON.parse(replaced);
            } catch (e2) {
                console.debug('parseMaybeJSON: no se pudo parsear (incluyendo reemplazo), valor:', value);
                return null;
            }
        }
    }
    return null;
}

async function cargarSiniestros() {
    try {
        const response = await fetch('/api/siniestros');
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
                <td colspan="13" class="text-center text-muted py-4">No tenemos datos disponibles</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = data.map(siniestro => `
        <tr>
            <td>${siniestro.id || ''}</td>
            <td>${siniestro.contratante || ''}</td>
            <td><a href="/menu/siniestros-poliza?poliza=${encodeURIComponent(siniestro.poliza)}" class="text-primary">${siniestro.poliza || ''}</a></td>
            <td>${siniestro.cia || ''}</td>
            <td>${siniestro.fec_stro || ''}</td>
            <td>${siniestro.causa || ''}</td>
            <td>${siniestro.siniestro_no || ''}</td>
            <td class="text-end">${formatNumber(siniestro.monto_siniestro) || '0.00'}</td>
            <td><span class="badge badge-${getEstadoClass(siniestro.estado)}">${siniestro.estado || 'PENDIENTE'}</span></td>
            <td>${siniestro.ejecutivo_cia || ''}</td>
            <td>${siniestro.ramo || ''}</td>
            <td>${siniestro.placa || ''}</td>
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
    document.getElementById('poliza').removeAttribute('readonly');
    document.getElementById('estado').value = 'PENDIENTE';

    modalSiniestro.show();
}

async function editarSiniestro(id) {
    try {
        // Resetear el contenedor antes de mostrar el modal
        const contenedor = document.getElementById('formularioDinamico');
        contenedor.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Cargando formulario...</span>
                </div>
                <p class="mt-3 text-muted">Cargando datos del siniestro...</p>
            </div>
        `;

        // Cargar datos del siniestro
        const response = await fetch(`/api/siniestros/${id}`);
        if (!response.ok) {
            throw new Error('No se pudo cargar el siniestro');
        }

        const siniestro = await response.json();
        console.log('Datos del siniestro a editar:', siniestro);

        // Actualizar título del modal
        document.getElementById('modalTitle').innerHTML = '<i class="bi bi-pencil-square"></i> Editar Siniestro';
        document.getElementById('siniestroId').value = siniestro.id;

        // Guardar el grupo del ramo
        const grupoRamo = siniestro.grupo_ramo || 'GENERICO';
        document.getElementById('grupoRamoActual').value = grupoRamo;

        // Mostrar modal
        modalSiniestro.show();

        // Cargar el formulario correspondiente al grupo
        await cargarFormularioPorGrupo(
            grupoRamo,
            siniestro.poliza,
            siniestro.contratante,
            siniestro.cia,
            siniestro.ramo
        );

        // Esperar explícitamente a que el formulario esté montado
        await waitForElement('poliza', 2500);
        // Esperar un poco adicional para que scripts embebidos terminen de ejecutarse
        await sleep(350);

        // Pre-llenar formulario
        preLlenarFormularioEdicion(siniestro);

    } catch (error) {
        console.error('Error al cargar siniestro:', error);
        mostrarError('Error al cargar el siniestro: ' + error.message);
        modalSiniestro.hide();
    }
}

async function cargarFormularioPorGrupo(grupo, poliza, contratante, cia, ramo) {
    const contenedor = document.getElementById('formularioDinamico');

    try {
        let formUrl = '';

        // Determinar qué formulario cargar según el grupo
        switch(grupo) {
            case 'RRGG':
                formUrl = '/templates/view/siniestros/form_siniestro_rrgg.html';
                break;
            case 'VEHICULOS':
                formUrl = '/templates/view/siniestros/form_siniestro_vehiculos.html';
                break;
            case 'RRHH':
                formUrl = '/templates/view/siniestros/form_siniestro_rrhh.html';
                break;
            case 'OTROS':
                formUrl = '/templates/view/siniestros/form_siniestro_otros.html';
                break;
            default:
                formUrl = '/templates/view/siniestros/form_siniestro_generico.html';
                break;
        }

        console.log(`Cargando formulario ${grupo} desde: ${formUrl}`);

        const response = await fetch(formUrl);
        if (!response.ok) {
            throw new Error(`Error al cargar formulario: ${response.status}`);
        }

        const html = await response.text();
        contenedor.innerHTML = html;

        // Pre-llenar los campos comunes después de cargar el formulario
        setTimeout(() => {
            const polizaInput = document.getElementById('poliza');
            const contratanteInput = document.getElementById('contratante');
            const aseguradoInput = document.getElementById('asegurado');
            const ciaInput = document.getElementById('cia');
            const ramoInput = document.getElementById('ramo');
            const estadoInput = document.getElementById('estado');

            if (polizaInput) polizaInput.value = poliza || '';
            if (contratanteInput) contratanteInput.value = contratante || '';
            if (aseguradoInput) aseguradoInput.value = contratante || '';
            if (ciaInput) ciaInput.value = cia || '';
            if (ramoInput) ramoInput.value = ramo || '';
            if (estadoInput) estadoInput.value = 'PENDIENTE';

            // Ejecutar scripts embebidos en el formulario
            const scripts = contenedor.querySelectorAll('script');
            scripts.forEach(script => {
                const newScript = document.createElement('script');
                newScript.textContent = script.textContent;
                document.body.appendChild(newScript);
                document.body.removeChild(newScript);
            });

            console.log(`Formulario ${grupo} cargado y pre-llenado correctamente`);
        }, 100);

    } catch (error) {
        console.error('Error al cargar formulario:', error);
        contenedor.innerHTML = `
            <div class="alert alert-danger mb-3">
                <i class="bi bi-exclamation-triangle"></i> 
                <strong>Error al cargar formulario:</strong> ${error.message}
                <br><small>Grupo: ${grupo}</small>
            </div>
            <div class="text-center">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
            </div>
        `;
    }
}

function preLlenarFormularioEdicion(siniestro) {
    console.log('Pre-llenando formulario con:', siniestro);

    // Función auxiliar para setear valor si el elemento existe
    const setVal = (id, value) => {
        const elem = document.getElementById(id);
        if (elem) elem.value = value || '';
    };

    // Campos comunes
    setVal('poliza', siniestro.poliza);
    setVal('cia', siniestro.cia);
    setVal('ramo', siniestro.ramo);
    setVal('contratante', siniestro.contratante);
    setVal('asegurado', siniestro.asegurado);
    setVal('fecPresentacionBroker', siniestro.fec_presentacion_broker);
    setVal('fecAvisoCia', siniestro.fec_aviso_cia);
    setVal('fecStro', siniestro.fec_stro);
    setVal('horaSiniestro', siniestro.hora_siniestro);
    setVal('quienReporta', siniestro.quien_reporta);
    setVal('email', siniestro.email);
    setVal('telefonos', siniestro.telefonos);
    setVal('lugarSiniestro', siniestro.lugar_siniestro);
    setVal('causa', siniestro.causa);
    setVal('descripcionHechos', siniestro.descripcion_hechos);
    setVal('siniestroNo', siniestro.siniestro_no);
    setVal('ejecutivoCia', siniestro.ejecutivo_cia);
    setVal('estado', siniestro.estado);

    // Indemnización
    setVal('moneda', siniestro.moneda);
    setVal('montoSiniestro', siniestro.monto_siniestro);
    setVal('deducible', siniestro.deducible);
    setVal('descripcionDeducible', siniestro.descripcion_deducible);
    setVal('totalIndemnizar', siniestro.total_indemnizar);
    setVal('fecPago', siniestro.fec_pago);
    setVal('formaPago', siniestro.forma_pago);
    setVal('numeroCheque', siniestro.numero_cheque);
    setVal('banco', siniestro.banco);

    // Factura
    setVal('numeroFactura', siniestro.numero_factura);
    setVal('montoPagarFactura', siniestro.monto_pagar_factura);
    setVal('fecVencimientoFactura', siniestro.fec_vencimiento_factura);
    setVal('fecPagoFactura', siniestro.fec_pago_factura);

    // Campos específicos RRGG
    if (siniestro.grupo_ramo === 'RRGG') {
        setVal('liquidadorAjustador', siniestro.liquidador_ajustador);
        setVal('conductor', siniestro.conductor);
        setVal('tercero', siniestro.tercero);
        setVal('comisaria', siniestro.comisaria);
        setVal('numeroDenuncia', siniestro.numero_denuncia);
        setVal('fecDenunciaPolicial', siniestro.fec_denuncia_policial);
        setVal('fecEntregaDocAjustador', siniestro.fec_entrega_doc_ajustador);
        setVal('fecEntregaDocCia', siniestro.fec_entrega_doc_cia);
        setVal('fecCiaConsentido', siniestro.fec_cia_consentido);
        setVal('numeroAjuste', siniestro.numero_ajuste);
    }

    // Campos específicos VEHICULOS
    if (siniestro.grupo_ramo === 'VEHICULOS') {
        setVal('fecNotificacionBroker', siniestro.fec_notificacion_broker);
        setVal('horaContacto', siniestro.hora_contacto);
        setVal('horaCulminacion', siniestro.hora_culminacion);
        setVal('tipoAtencion', siniestro.tipo_atencion);
        setVal('fecPresentacionCia', siniestro.fec_presentacion_cia);
        setVal('situacion', siniestro.situacion);
        setVal('vehiculoPlaca', siniestro.placa);

        // Intentar obtener objeto vehiculo desde diferentes campos
        const vehiculo = parseMaybeJSON(siniestro.datos_vehiculo) || parseMaybeJSON(siniestro.vehiculo) || null;
        console.debug('vehiculo detectado para prellenado:', vehiculo);
        if (vehiculo) {
            if (!siniestro.placa && vehiculo.placa) setVal('vehiculoPlaca', vehiculo.placa);
            setVal('vehiculoMarca', vehiculo.marca);
            setVal('vehiculoModelo', vehiculo.modelo);
            setVal('vehiculoMotor', vehiculo.motor);
            setVal('vehiculoAnio', vehiculo.anio);
            setVal('vehiculoColor', vehiculo.color);
            setVal('vehiculoPropietario', vehiculo.propietario);
            setVal('vehiculoSituacionEvento', vehiculo.situacion_evento);
            setVal('vehiculoTaller', vehiculo.taller);
        }

        // Denuncia
        const denuncia = parseMaybeJSON(siniestro.datos_denuncia) || parseMaybeJSON(siniestro.denuncia) || null;
        console.debug('denuncia detectada para prellenado:', denuncia);
        if (denuncia) {
            setVal('denunciaComisaria', denuncia.comisaria);
            setVal('denunciaNumeroDenuncia', denuncia.numero_denuncia || denuncia.numeroDenuncia || '');
            setVal('denunciaDosajeEtilico', denuncia.dosaje_etilico || '');
            setVal('denunciaFecha', formatDateForInput(denuncia.fec_denuncia || denuncia.fec_denuncia));
            setVal('denunciaDepartamento', denuncia.departamento);
            setVal('denunciaProvincia', denuncia.provincia);
            setVal('denunciaDistrito', denuncia.distrito);
        }

        // Conductor
        const conductor = parseMaybeJSON(siniestro.datos_conductor) || parseMaybeJSON(siniestro.conductor) || null;
        console.debug('conductor detectado para prellenado:', conductor);
        if (conductor) {
            setVal('conductorNombre', conductor.nombre);
            setVal('conductorDocumento', conductor.documento_identidad || conductor.documento || '');
            setVal('conductorFecNacimiento', formatDateForInput(conductor.fec_nacimiento));
            setVal('conductorLicencia', conductor.licencia_conducir);
            setVal('conductorCategoriaLicencia', conductor.categoria_licencia);
            setVal('conductorEmail', conductor.email);
            setVal('conductorTelefonos', conductor.telefonos);
        }

        // Copiloto
        const copiloto = parseMaybeJSON(siniestro.datos_copiloto) || parseMaybeJSON(siniestro.copiloto) || null;
        console.debug('copiloto detectado para prellenado:', copiloto);
        if (copiloto) {
            setVal('copilotoNombre', copiloto.nombre);
            setVal('copilotoFecNacimiento', formatDateForInput(copiloto.fec_nacimiento));
            setVal('copilotoLicencia', copiloto.licencia_conducir);
            setVal('copilotoCategoriaLicencia', copiloto.categoria_licencia);
            setVal('copilotoEmail', copiloto.email);
            setVal('copilotoTelefonos', copiloto.telefonos);
        }

        // Tercero
        const tercero = parseMaybeJSON(siniestro.datos_tercero) || parseMaybeJSON(siniestro.tercero) || null;
        if (tercero) {
            setVal('terceroConductor', tercero.conductor);
            setVal('terceroPlaca', tercero.placa);
            setVal('terceroDomicilio', tercero.domicilio);
            setVal('terceroLicencia', tercero.licencia_conducir);
            setVal('terceroPropietario', tercero.propietario);
            setVal('terceroDireccionPropietario', tercero.direccion_propietario);
            setVal('terceroEmail', tercero.email);
            setVal('terceroTelefonos', tercero.telefonos);
        }
    }

    // Campos específicos RRHH
    if (siniestro.grupo_ramo === 'RRHH') {
        setVal('fecAtencionMedica', siniestro.fec_atencion_medica);
        setVal('tipoPersona', siniestro.tipo_persona);
        setVal('titular', siniestro.titular);
        setVal('paciente', siniestro.paciente);
        setVal('diagnostico', siniestro.diagnostico);
        setVal('coaseguro', siniestro.coaseguro);
        setVal('noCubierto', siniestro.no_cubierto);

        // Cargar gastos si existen
        if (siniestro.gastos_presentados && Array.isArray(siniestro.gastos_presentados)) {
            // Aquí deberías tener una función para cargar los gastos en la tabla
            console.log('Gastos a cargar:', siniestro.gastos_presentados);
        }
    }

    console.log('Formulario pre-llenado correctamente');
}

async function guardarSiniestro(event) {
    event.preventDefault();

   try {
        const form = document.getElementById('formSiniestro');
        if (form) {
            const elements = Array.from(form.querySelectorAll('input, select, textarea'));
            elements.forEach(el => {
                const style = window.getComputedStyle(el);
                const isHidden = (el.type === 'hidden') || (!el.offsetParent && style.visibility !== 'visible');
                if (isHidden && el.hasAttribute('required')) {
                    el.removeAttribute('required');
                }
            });
        }
    } catch (cleanupErr) {
        console.debug('Error limpiando atributos required antes de enviar:', cleanupErr);
    }

    const id = document.getElementById('siniestroId').value;
    const grupoRamo = document.getElementById('grupoRamoActual').value;

    // Función auxiliar para obtener valor de campo si existe
    const getVal = (id) => {
        const elem = document.getElementById(id);
        return elem ? elem.value : null;
    };


    const data = {
        grupo_ramo: grupoRamo,
        poliza: getVal('poliza'),
        cia: getVal('cia'),
        ramo: getVal('ramo'),
        contratante: getVal('contratante'),
        asegurado: getVal('asegurado'),
        fec_stro: getVal('fecStro'),
        hora_siniestro: getVal('horaSiniestro'),
        quien_reporta: getVal('quienReporta'),
        email: getVal('email'),
        telefonos: getVal('telefonos'),
        lugar_siniestro: getVal('lugarSiniestro'),
        causa: getVal('causa'),
        descripcion_hechos: getVal('descripcionHechos'),
        siniestro_no: getVal('siniestroNo'),
        ejecutivo_cia: getVal('ejecutivoCia'),
        estado: getVal('estado') || 'PENDIENTE',

        // Indemnización (común)
        moneda: getVal('moneda') || 'US$',
        monto_siniestro: parseFloat(getVal('montoSiniestro')) || 0,
        deducible: parseFloat(getVal('deducible')) || 0,
        descripcion_deducible: getVal('descripcionDeducible'),
        total_indemnizar: parseFloat(getVal('totalIndemnizar')) || 0,
        fec_pago: getVal('fecPago'),
        forma_pago: getVal('formaPago'),
        numero_cheque: getVal('numeroCheque'),
        banco: getVal('banco'),

        // Factura por deducible (común)
        numero_factura: getVal('numeroFactura'),
        monto_pagar_factura: parseFloat(getVal('montoPagarFactura')) || 0,
        fec_vencimiento_factura: getVal('fecVencimientoFactura'),
        fec_pago_factura: getVal('fecPagoFactura')
    };

    // Campos específicos de RRGG
    if (grupoRamo === 'RRGG') {
        data.fec_presentacion_broker = getVal('fecPresentacionBroker');
        data.fec_aviso_cia = getVal('fecAvisoCia');
        data.liquidador_ajustador = getVal('liquidadorAjustador');
        data.conductor = getVal('conductor');
        data.tercero = getVal('tercero');
        data.comisaria = getVal('comisaria');
        data.numero_denuncia = getVal('numeroDenuncia');
        data.fec_denuncia_policial = getVal('fecDenunciaPolicial');
        data.fec_entrega_doc_ajustador = getVal('fecEntregaDocAjustador');
        data.fec_entrega_doc_cia = getVal('fecEntregaDocCia');
        data.fec_cia_consentido = getVal('fecCiaConsentido');
        data.numero_ajuste = getVal('numeroAjuste');
    }

    // Campos específicos de VEHICULOS
    if (grupoRamo === 'VEHICULOS') {
        data.fec_notificacion_broker = getVal('fecNotificacionBroker');
        data.hora_contacto = getVal('horaContacto');
        data.hora_culminacion = getVal('horaCulminacion');
        data.tipo_atencion = getVal('tipoAtencion');
        data.fec_presentacion_cia = getVal('fecPresentacionCia');
        data.situacion = getVal('situacion');
        data.placa = getVal('vehiculoPlaca');

        // Datos del vehículo
        data.vehiculo = {
            placa: getVal('vehiculoPlaca'),
            marca: getVal('vehiculoMarca'),
            modelo: getVal('vehiculoModelo'),
            motor: getVal('vehiculoMotor'),
            anio: getVal('vehiculoAnio'),
            color: getVal('vehiculoColor'),
            propietario: getVal('vehiculoPropietario'),
            situacion_evento: getVal('vehiculoSituacionEvento'),
            taller: getVal('vehiculoTaller')
        };

        // Datos de la denuncia
        data.denuncia = {
            comisaria: getVal('denunciaComisaria'),
            numero_denuncia: getVal('denunciaNumeroDenuncia'),
            dosaje_etilico: getVal('denunciaDosajeEtilico'),
            fec_denuncia: getVal('denunciaFecha'),
            departamento: getVal('denunciaDepartamento'),
            provincia: getVal('denunciaProvincia'),
            distrito: getVal('denunciaDistrito')
        };

        // Datos del conductor
        data.conductor = {
            nombre: getVal('conductorNombre'),
            documento_identidad: getVal('conductorDocumento'),
            fec_nacimiento: getVal('conductorFecNacimiento'),
            licencia_conducir: getVal('conductorLicencia'),
            categoria_licencia: getVal('conductorCategoriaLicencia'),
            email: getVal('conductorEmail'),
            telefonos: getVal('conductorTelefonos')
        };

        // Datos del copiloto
        data.copiloto = {
            nombre: getVal('copilotoNombre'),
            fec_nacimiento: getVal('copilotoFecNacimiento'),
            licencia_conducir: getVal('copilotoLicencia'),
            categoria_licencia: getVal('copilotoCategoriaLicencia'),
            email: getVal('copilotoEmail'),
            telefonos: getVal('copilotoTelefonos')
        };

        // Datos de terceros
        data.tercero = {
            conductor: getVal('terceroConductor'),
            placa: getVal('terceroPlaca'),
            domicilio: getVal('terceroDomicilio'),
            licencia_conducir: getVal('terceroLicencia'),
            propietario: getVal('terceroPropietario'),
            direccion_propietario: getVal('terceroDireccionPropietario'),
            email: getVal('terceroEmail'),
            telefonos: getVal('terceroTelefonos')
        };
    }

    // Campos específicos de RRHH
    if (grupoRamo === 'RRHH') {
        data.fec_presentacion_broker = getVal('fecPresentacionBroker');
        data.fec_atencion_medica = getVal('fecAtencionMedica');
        data.fec_aviso_cia = getVal('fecAvisoCia');
        data.fec_presentacion_cia = getVal('fecPresentacionCia');
        data.fec_cia_consentido = getVal('fecCiaConsentido');
        data.tipo_persona = getVal('tipoPersona');
        data.titular = getVal('titular');
        data.paciente = getVal('paciente');
        data.diagnostico = getVal('diagnostico');
        data.coaseguro = parseFloat(getVal('coaseguro')) || 0;
        data.no_cubierto = parseFloat(getVal('noCubierto')) || 0;

        // Gastos presentados (de los campos ocultos)
        const gastosData = getVal('gastosData');
        data.gastos = gastosData ? JSON.parse(gastosData) : [];

        // Documentos (de los campos ocultos)
        const documentosData = getVal('documentosData');
        data.documentos = documentosData ? JSON.parse(documentosData) : [];

        // Bitácora (de los campos ocultos)
        const bitacoraData = getVal('bitacoraData');
        data.bitacora = bitacoraData ? JSON.parse(bitacoraData) : [];

        // Archivos (de los campos ocultos)
        const archivosData = getVal('archivosData');
        data.archivos = archivosData ? JSON.parse(archivosData) : [];
    }

    console.log('Datos a enviar:', data);

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
        (s.poliza || '').toLowerCase().includes(texto) ||
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

    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
        return str;
    }

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
