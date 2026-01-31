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
                <td colspan="13" class="text-center text-muted py-4">No tenemos datos disponibles</td>
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

async function abrirModalNuevo() {
    document.getElementById('modalTitle').innerHTML = '<i class="bi bi-file-earmark-plus"></i> Añadir Siniestro';
    document.getElementById('formSiniestro').reset();
    document.getElementById('siniestroId').value = '';

    const poliza = document.getElementById('polizaCertif').textContent.trim();
    const contratante = document.getElementById('asegurado').textContent.trim();
    const cia = document.getElementById('compania').textContent.trim();
    const ramo = document.getElementById('materiaAsegurada').textContent.trim();

    // Mostrar modal con loader
    modalSiniestro.show();

    // Detectar el grupo del ramo de la póliza
    try {
        const response = await fetch(`/api/siniestros/grupo-ramo?poliza=${encodeURIComponent(poliza)}`);
        if (response.ok) {
            const data = await response.json();
            console.log('Grupo del ramo detectado:', data);
            console.log('Póliza:', data.poliza);
            console.log('Ramo:', data.ramo);
            console.log('Grupo:', data.grupo);

            // Guardar el grupo en un campo oculto
            document.getElementById('grupoRamoActual').value = data.grupo;

            // Cargar el formulario correspondiente
            await cargarFormularioPorGrupo(data.grupo, poliza, contratante, cia, ramo);

        } else {
            console.error('Error al obtener grupo del ramo');
            mostrarError('No se pudo detectar el grupo del ramo');
            document.getElementById('formularioDinamico').innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i> 
                    No se pudo detectar el grupo del ramo. Por favor, contacte al administrador.
                </div>
            `;
        }
    } catch (error) {
        console.error('Error al detectar grupo del ramo:', error);
        mostrarError('Error al detectar el grupo del ramo');
        document.getElementById('formularioDinamico').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> 
                Error al cargar el formulario. Por favor, intente nuevamente.
            </div>
        `;
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
                // Formulario genérico para grupos no definidos
                formUrl = '/templates/view/siniestros/form_siniestro_generico.html';
                break;
        }

        console.log(`Cargando formulario desde: ${formUrl}`);

        const response = await fetch(formUrl);
        if (response.ok) {
            const html = await response.text();
            contenedor.innerHTML = html;

            // Pre-llenar los campos comunes
            setTimeout(() => {
                const polizaInput = document.getElementById('poliza');
                const contratanteInput = document.getElementById('contratante');
                const aseguradoInput = document.getElementById('asegurado');
                const ciaInput = document.getElementById('cia');
                const ramoInput = document.getElementById('ramo');
                const estadoInput = document.getElementById('estado');

                if (polizaInput) polizaInput.value = poliza;
                if (contratanteInput) contratanteInput.value = contratante;
                if (aseguradoInput) aseguradoInput.value = contratante; // Usualmente son iguales
                if (ciaInput) ciaInput.value = cia;
                if (ramoInput) ramoInput.value = ramo;
                if (estadoInput) estadoInput.value = 'PENDIENTE';

                // Ejecutar scripts embebidos en el formulario cargado
                const scripts = contenedor.querySelectorAll('script');
                scripts.forEach(script => {
                    const newScript = document.createElement('script');
                    newScript.textContent = script.textContent;
                    document.body.appendChild(newScript);
                    document.body.removeChild(newScript);
                });

                console.log(`Formulario ${grupo} cargado correctamente`);
                mostrarExito(`Formulario para ${grupo} cargado`);
            }, 100);

        } else {
            throw new Error('No se pudo cargar el formulario');
        }

    } catch (error) {
        console.error('Error al cargar formulario:', error);

        // Cargar formulario genérico como fallback
        contenedor.innerHTML = `
            <div class="alert alert-warning mb-3">
                <i class="bi bi-exclamation-circle"></i> 
                Formulario específico no disponible. Usando formulario genérico para grupo: <strong>${grupo}</strong>
            </div>
            <div class="row g-3">
                <div class="col-md-6">
                    <h6 class="border-bottom pb-2 mb-3">Información General</h6>
                    <div class="mb-3">
                        <label for="poliza" class="form-label">Póliza *</label>
                        <input type="text" class="form-control" id="poliza" readonly required>
                    </div>
                    <div class="mb-3">
                        <label for="contratante" class="form-label">Contratante *</label>
                        <input type="text" class="form-control" id="contratante" required>
                    </div>
                    <div class="mb-3">
                        <label for="asegurado" class="form-label">Asegurado *</label>
                        <input type="text" class="form-control" id="asegurado" required>
                    </div>
                    <div class="mb-3">
                        <label for="cia" class="form-label">Compañía *</label>
                        <input type="text" class="form-control" id="cia" required>
                    </div>
                    <div class="mb-3">
                        <label for="ramo" class="form-label">Ramo</label>
                        <input type="text" class="form-control" id="ramo">
                    </div>
                </div>
                <div class="col-md-6">
                    <h6 class="border-bottom pb-2 mb-3">Detalles del Siniestro</h6>
                    <div class="mb-3">
                        <label for="fecStro" class="form-label">Fecha Siniestro *</label>
                        <input type="date" class="form-control" id="fecStro" required>
                    </div>
                    <div class="mb-3">
                        <label for="siniestroNo" class="form-label">Número Siniestro</label>
                        <input type="text" class="form-control" id="siniestroNo">
                    </div>
                    <div class="mb-3">
                        <label for="causa" class="form-label">Causa</label>
                        <textarea class="form-control" id="causa" rows="3"></textarea>
                    </div>
                    <div class="mb-3">
                        <label for="estado" class="form-label">Estado</label>
                        <select class="form-select" id="estado">
                            <option value="PENDIENTE">PENDIENTE</option>
                            <option value="EN_PROCESO">EN PROCESO</option>
                            <option value="CERRADO">CERRADO</option>
                        </select>
                    </div>
                </div>
            </div>
        `;

        // Pre-llenar campos del formulario genérico
        setTimeout(() => {
            document.getElementById('poliza').value = poliza;
            document.getElementById('contratante').value = contratante;
            document.getElementById('asegurado').value = contratante;
            document.getElementById('cia').value = cia;
            document.getElementById('ramo').value = ramo;
            document.getElementById('estado').value = 'PENDIENTE';
        }, 100);
    }
}

async function editarSiniestro(id) {
    try {
        // Cargar datos del siniestro
        const response = await fetch(`/api/siniestros/${id}`);
        const siniestro = await response.json();

        console.log('Datos del siniestro a editar:', siniestro);

        // Actualizar título del modal
        document.getElementById('modalTitle').innerHTML = '<i class="bi bi-pencil-square"></i> Editar Siniestro';
        document.getElementById('siniestroId').value = siniestro.id;

        // Guardar el grupo del ramo
        const grupoRamo = siniestro.grupo_ramo || 'GENERICO';
        document.getElementById('grupoRamoActual').value = grupoRamo;

        // Mostrar modal con loader
        modalSiniestro.show();

        // Cargar el formulario correspondiente al grupo
        await cargarFormularioPorGrupo(
            grupoRamo,
            siniestro.poliza,
            siniestro.contratante,
            siniestro.cia,
            siniestro.ramo
        );

        // Esperar a que el formulario se cargue y entonces llenar los campos
        setTimeout(() => {
            preLlenarFormularioEdicion(siniestro);
        }, 500);

    } catch (error) {
        console.error('Error al cargar siniestro:', error);
        mostrarError('Error al cargar el siniestro');
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
    }

    console.log('Formulario pre-llenado correctamente');
}

async function guardarSiniestro(event) {
    event.preventDefault();

    const id = document.getElementById('siniestroId').value;
    const grupoRamo = document.getElementById('grupoRamoActual').value;

    // Función auxiliar para obtener valor de campo si existe
    const getVal = (id) => {
        const elem = document.getElementById(id);
        return elem ? elem.value : null;
    };

    // Datos comunes para todos los formularios
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
