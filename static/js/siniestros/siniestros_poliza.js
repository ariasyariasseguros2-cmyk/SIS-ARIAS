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
                <td colspan="12" class="text-center text-muted py-4">No tenemos datos disponibles</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = data.map(siniestro => {
        return `
        <tr>
            <td>${siniestro.id || ''}</td>
            <td title="${(siniestro.contratante||'').replace(/"/g,'\"')}">${siniestro.contratante || ''}</td>
            <td>${siniestro.poliza || ''}</td>
            <td>${siniestro.cia || ''}</td>
            <td>${siniestro.fec_stro || ''}</td>
            <td>${siniestro.causa || ''}</td>
            <td>${siniestro.siniestro_no || ''}</td>
            <td class="text-end">${formatNumber(siniestro.monto_siniestro) || '0.00'}</td>
            <td><span class="badge badge-${getEstadoClass(siniestro.estado)}">${siniestro.estado || 'PENDIENTE'}</span></td>
            <td>${siniestro.ejecutivo_cia || ''}</td>
            <td>${siniestro.ramo || ''}</td>
            <td class="text-end">
                <div class="chips-row">
                    <span class="chip chip-info" role="button" onclick="descargarPDF(${siniestro.id})" title="Descargar PDF">
                        <i class="bi bi-file-pdf"></i> PDF
                    </span>
                    <span class="chip chip-primary" role="button" onclick="editarSiniestro(${siniestro.id})" title="Editar">EDITAR</span>
                    <span class="chip chip-danger" role="button" onclick="eliminarSiniestro(${siniestro.id})" title="Eliminar">ELIMINAR</span>
                </div>
            </td>
        </tr>
    `}).join('');
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


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


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
                return null;
            }
        }
    }
    return null;
}

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

function attachAutoCalculoIndemnizacion() {
    try {
        const montoEl = document.getElementById('montoSiniestro');
        const deducibleEl = document.getElementById('deducible');
        const totalEl = document.getElementById('totalIndemnizar');
        if (!montoEl && !deducibleEl) return;

        const compute = () => {
            const monto = parseFloat(montoEl ? montoEl.value : (montoEl && montoEl.textContent) || 0) || 0;
            const ded = parseFloat(deducibleEl ? deducibleEl.value : (deducibleEl && deducibleEl.textContent) || 0) || 0;
            let total = monto - ded;
            if (!isFinite(total) || isNaN(total)) total = 0;
            if (total < 0) total = 0; // no permitir negativos
            if (totalEl) totalEl.value = total.toFixed(2);
        };


        if (montoEl) {
            montoEl.removeEventListener && montoEl.removeEventListener('input', compute);
            montoEl.addEventListener('input', compute);
            montoEl.addEventListener('change', compute);
        }
        if (deducibleEl) {
            deducibleEl.removeEventListener && deducibleEl.removeEventListener('input', compute);
            deducibleEl.addEventListener('input', compute);
            deducibleEl.addEventListener('change', compute);
        }

        // Inicializar el calculo
        compute();
    } catch (e) {

        console.warn('attachAutoCalculoIndemnizacion error:', e);
    }
}

async function abrirModalNuevo() {
    document.getElementById('modalTitle').innerHTML = '<i class="bi bi-file-earmark-plus"></i> Añadir Siniestro';
    document.getElementById('formSiniestro').reset();
    document.getElementById('siniestroId').value = '';

    const poliza = document.getElementById('polizaCertif').textContent.trim();
    const contratante = document.getElementById('asegurado').textContent.trim();
    const cia = document.getElementById('compania').textContent.trim();
    // Tomar ramo desde el campo específico de la cabecera (ramoPoliza)
    const ramo = document.getElementById('ramoPoliza').textContent.trim();
    const materia = document.getElementById('materiaAsegurada') ? document.getElementById('materiaAsegurada').textContent.trim() : '';

    // Mostrar modal con loader
    modalSiniestro.show();

    // Detectar el grupo del ramo de la póliza
    try {
        const response = await fetch(`/api/siniestros/grupo-ramo?poliza=${encodeURIComponent(poliza)}`);
        if (response.ok) {
            const data = await response.json();
            // Datos del grupo recibidos

            // Guardar el grupo en un campo oculto
            document.getElementById('grupoRamoActual').value = data.grupo;

            // Cargar el formulario correspondiente
            await cargarFormularioPorGrupo(data.grupo, poliza, contratante, cia, ramo, materia);

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

async function cargarFormularioPorGrupo(grupo, poliza, contratante, cia, ramoVal, materiaVal) {
    const contenedor = document.getElementById('formularioDinamico');

    try {
        let formUrl = '';

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

                formUrl = '/templates/view/siniestros/form_siniestro_otros.html';
                break;
        }

        // Cargando formulario desde URL calculada

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
                if (ramoInput) ramoInput.value = ramoVal;
                if (estadoInput) estadoInput.value = 'PENDIENTE';

                // Intentar setear 'materia asegurada' en los formularios (varias posibilidades de id)
                const materiaIds = ['materia', 'materiaAsegurada', 'materia_asegurada', 'asegurada_poliza', 'aseguradaPoliza', 'descripcion_materia'];
                let materiaSet = false;
                for (const id of materiaIds) {
                    const el = document.getElementById(id);
                    if (el) {
                        if ('value' in el) el.value = materiaVal || '';
                        else el.textContent = materiaVal || '';
                        materiaSet = true;
                        break;
                    }
                }
                if (!materiaSet) {
                    // Si no existía un campo para materia, crear un hidden para que el backend la reciba si es necesario
                    const hidden = document.createElement('input');
                    hidden.type = 'hidden';
                    hidden.id = 'materia_asegurada';
                    hidden.name = 'materia_asegurada';
                    hidden.value = materiaVal || '';
                    contenedor.appendChild(hidden);
                }

                // Ejecutar scripts embebidos en el formulario cargado
                const scripts = contenedor.querySelectorAll('script');
                scripts.forEach(script => {
                    const newScript = document.createElement('script');
                    newScript.textContent = script.textContent;
                    document.body.appendChild(newScript);
                    document.body.removeChild(newScript);
                });

                // Reintentar fijar materia asegurada varias veces (por si el formulario crea los campos dinámicamente)
                setMateriaValue(materiaVal).then(found => {
                    if (!found) {
                        console.warn('materia asegurada: no se encontró campo, se creó hidden');
                    }
                });

                // Adjuntar cálculo automático de indemnización
                attachAutoCalculoIndemnizacion();

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
                    <input type="hidden" id="materia_asegurada" name="materia_asegurada" value="${materiaVal || ''}">
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
            document.getElementById('ramo').value = ramoVal;
            // materia ya incluida como hidden (id='materia_asegurada')
            document.getElementById('estado').value = 'PENDIENTE';

            // Adjuntar cálculo automático en el fallback
            attachAutoCalculoIndemnizacion();
        }, 100);
    }
}

function setMateriaValue(materiaVal, maxRetries = 6, interval = 150) {
    const materiaIds = ['materia', 'materiaAsegurada', 'materia_asegurada', 'asegurada_poliza', 'aseguradaPoliza', 'descripcion_materia', 'materia_asegurada'];

    return new Promise((resolve) => {
        let attempts = 0;
        const trySet = () => {
            attempts++;
            for (const id of materiaIds) {
                const el = document.getElementById(id);
                if (el) {
                    try {
                        if ('value' in el) el.value = materiaVal || '';
                        else el.textContent = materiaVal || '';
                    } catch (e) {
                        // ignore
                    }
                    return resolve(true);
                }
            }
            // If not found and reached max retries, create hidden once
            if (attempts >= maxRetries) {
                // ensure we don't duplicate hidden
                if (!document.getElementById('materia_asegurada')) {
                    const hidden = document.createElement('input');
                    hidden.type = 'hidden';
                    hidden.id = 'materia_asegurada';
                    hidden.name = 'materia_asegurada';
                    hidden.value = materiaVal || '';
                    const cont = document.getElementById('formularioDinamico') || document.body;
                    cont.appendChild(hidden);
                }
                return resolve(false);
            }
            setTimeout(trySet, interval);
        };
        trySet();
    });
}

async function editarSiniestro(id) {
    try {
        // Cargar datos del siniestro
        const response = await fetch(`/api/siniestros/${id}`);
        const siniestro = await response.json();


        // Actualizar título del modal
        document.getElementById('modalTitle').innerHTML = '<i class="bi bi-pencil-square"></i> Editar Siniestro';
        document.getElementById('siniestroId').value = siniestro.id;

        // Guardar el grupo del ramo
        const grupoRamo = siniestro.grupo_ramo || 'OTROS';
        document.getElementById('grupoRamoActual').value = grupoRamo;

        // Mostrar modal con loader
        modalSiniestro.show();

        // Cargar el formulario correspondiente al grupo
        await cargarFormularioPorGrupo(
            grupoRamo,
            siniestro.poliza,
            siniestro.contratante,
            siniestro.cia,
            siniestro.ramo,
            siniestro.asegurada || ''
        );

        // Esperar explícitamente a que el formulario esté montado
        await waitForElement('poliza', 3000);
        // Esperar un poco adicional para que scripts embebidos terminen de ejecutarse
        await sleep(350);

        // Llenar los campos (primera pasada)
        preLlenarFormularioEdicion(siniestro);
        // Reintento breve para sobreescribir valores si otros scripts modifiquen el DOM
        setTimeout(() => preLlenarFormularioEdicion(siniestro), 300);

    } catch (error) {
        console.error('Error al cargar siniestro:', error);
        mostrarError('Error al cargar el siniestro');
    }
}

function preLlenarFormularioEdicion(siniestro) {
    // Pre-llenando formulario con siniestro

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

    // Asegurar que 'materia asegurada' se establece en edición también
    try {
        const materiaVal = siniestro.asegurada || siniestro.materia_asegurada || '';
        if (materiaVal) {
            setMateriaValue(materiaVal);
        }
    } catch (e) {
        // no bloquear si falla
    }

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
        if (vehiculo) {
            // Si no hubo placa raíz, tomarla del objeto vehiculo
            if (!siniestro.placa && vehiculo.placa) {
                setVal('vehiculoPlaca', vehiculo.placa);
            }
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
        // Usar formatDateForInput para asegurar formato YYYY-MM-DD en inputs type=date
        setVal('fecAtencionMedica', formatDateForInput(siniestro.fec_atencion_medica));
        setVal('tipoPersona', siniestro.tipo_persona);
        setVal('titular', siniestro.titular);
        setVal('paciente', siniestro.paciente);
        setVal('diagnostico', siniestro.diagnostico);
        setVal('coaseguro', siniestro.coaseguro);
        setVal('noCubierto', siniestro.no_cubierto);
        // Estas dos fechas eran las que no se estaban mostrando correctamente: normalizar formato
        setVal('fecCiaConsentido', formatDateForInput(siniestro.fec_cia_consentido));
        setVal('fecPresentacionCia', formatDateForInput(siniestro.fec_presentacion_cia));

        // Cargar gastos presentados si vienen en el objeto del siniestro
        const gastos = siniestro.gastos || siniestro.gastos_presentados || [];
        try {
            // Garantizar que window.gastosArray exista (incluso si está vacío)
            try { window.gastosArray = Array.isArray(gastos) ? gastos.slice() : []; } catch (e) { window.gastosArray = gastos || []; }

            // Actualizar el campo oculto para que el payload lo contenga si el usuario guarda sin cambios
            const gastosField = document.getElementById('gastosData');
            if (gastosField) gastosField.value = JSON.stringify(window.gastosArray || []);

            // Fallback render directo de la tabla en caso `actualizarTablaGastos` no exista
            const renderGastosTableFallback = (arr) => {
                try {
                    const tbody = document.getElementById('gastosTableBody');
                    if (!tbody) return;
                    if (!arr || arr.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No hay gastos registrados</td></tr>';
                        return;
                    }
                    tbody.innerHTML = arr.map((gasto, index) => `
                        <tr>
                            <td>${gasto.tipo}</td>
                            <td>${gasto.descripcion}</td>
                            <td class="text-end">${(parseFloat(gasto.monto) || 0).toFixed(2)}</td>
                            <td>${gasto.fecha}</td>
                            <td class="text-center">
                                <button type="button" class="btn btn-sm btn-danger" onclick="eliminarGasto(${index})">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                } catch (e) {
                    // No mostrar debug en producción
                }
            };

            // Intentar ejecutar actualizarTablaGastos con varios reintentos
            const tryActualizarGastos = () => {
                const exists = typeof actualizarTablaGastos === 'function';
                if (exists) {
                    try {
                        actualizarTablaGastos();
                        return true;
                    } catch (e) {
                        return false;
                    }
                }
                return false;
            };

            // Reintentos escalonados y fallback
            if (!tryActualizarGastos()) {
                setTimeout(() => { if (!tryActualizarGastos()) { renderGastosTableFallback(window.gastosArray || []); } }, 200);
                setTimeout(() => { if (!tryActualizarGastos()) { renderGastosTableFallback(window.gastosArray || []); } }, 500);
                setTimeout(() => { if (!tryActualizarGastos()) { renderGastosTableFallback(window.gastosArray || []); } }, 1000);
            }

        } catch (e) {
            // No mostrar debug en producción
        }
    }

    // Formulario pre-llenado correctamente
    // Asegurar que la calculadora automática esté activa tras pre-llenar
    attachAutoCalculoIndemnizacion();
}

async function guardarSiniestro(event) {
    event.preventDefault();

    // Quitar required de campos ocultos antes de construir/validar el payload
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
        // Error silencioso al limpiar atributos required antes de enviar
    }

    const id = document.getElementById('siniestroId').value;
    const grupoRamo = document.getElementById('grupoRamoActual').value;

    // Función auxiliar para obtener valor de campo si existe
    const getVal = (id) => {
        const elem = document.getElementById(id);
        if (!elem) return null;
        // Obtener el valor y normalizar
        let val = elem.value;
        if (typeof val === 'string') {
            val = val.trim();
            if (val === '') return null; // Convertir cadenas vacías a null (evita enviar "" para fechas)
        }
        return val;
    };


    const data = {
        grupo_ramo: grupoRamo,
        poliza: getVal('poliza'),
        cia: getVal('cia'),
        ramo: getVal('ramo'),
        contratante: getVal('contratante'),
        asegurado: getVal('asegurado'),
        materia_asegurada: getVal('materia_asegurada') || getVal('materiaAsegurada') || getVal('asegurada'),
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

    // Preparando datos a enviar

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
            // Manejo robusto de errores: puede venir JSON o texto (HTML)
            const contentType = response.headers.get('content-type') || '';
            let errorMsg = `Error ${response.status} ${response.statusText}`;
            try {
                if (contentType.includes('application/json')) {
                    const errJson = await response.json();
                    errorMsg = errJson.error || errJson.message || JSON.stringify(errJson) || errorMsg;
                } else {
                    const text = await response.text();
                    // Si la respuesta parece HTML, intentar extraer contenido útil
                    if (text && text.trim().startsWith('<')) {
                        // Buscar bloque <pre> (Traceback de Flask en debug)
                        const preMatch = text.match(/<pre[^>]*>([\s\S]*?)<\/pre>/i);
                        if (preMatch && preMatch[1]) {
                            errorMsg = preMatch[1].trim();
                        } else {
                            // Buscar <title>
                            const titleMatch = text.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
                            if (titleMatch && titleMatch[1]) {
                                errorMsg = titleMatch[1].trim();
                            } else {
                                // Fallback: eliminar etiquetas HTML y truncar
                                const stripped = text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
                                errorMsg = stripped.length > 1000 ? stripped.slice(0, 1000) + '... (truncated)' : stripped;
                            }
                        }
                    } else {
                        // Si no es HTML, usar texto directo
                        errorMsg = text ? (text.length > 1000 ? text.slice(0, 1000) + '... (truncated)' : text) : errorMsg;
                    }
                }
            } catch (parseErr) {
                // fallback: intentar leer texto
                try {
                    const fallbackText = await response.text();
                    if (fallbackText) {
                        const stripped = fallbackText.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
                        errorMsg = stripped.length > 1000 ? stripped.slice(0, 1000) + '... (truncated)' : stripped;
                    }
                } catch (e) {
                    // nada más que hacer
                }
            }

            console.error('Error al guardar siniestro. Status:', response.status, response.statusText, 'Body:', errorMsg);
            mostrarError(errorMsg);
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarError('Error al guardar el siniestro: ' + (error.message || error));
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

async function descargarPDF(id) {
    try {
        const url = `/api/siniestros/${id}/pdf?inline=1`;
        window.open(url, '_blank');
    } catch (error) {
        console.error('Error al abrir PDF:', error);
        mostrarError('Error al abrir el PDF');
    }
}
