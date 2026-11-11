
/* =========================================================
   SIS-ARIAS - GENERADOR DE TRAMAS
   ConsultaPE DNI / RUC
   ========================================================= */

(() => {
    'use strict';

    const MAX_REGISTROS_TRAMA = 10;

    const $ = id => document.getElementById(id);

    const btnConsultar = $('btnConsultar');
    const btnAgregar = $('btnAgregar');
    const btnExportar = $('btnExportarExcel');
    const formulario = $('tramaForm');
    const tabla = $('tablaTramas');

    if (!btnConsultar || !formulario || !tabla) {
        console.error('No se encontraron los elementos de Tramas.');
        return;
    }

    /* =====================================================
       MODALES Y MENSAJES
       ===================================================== */

    function mostrarModal(id) {
        const elemento = $(id);

        if (elemento && window.bootstrap) {
            bootstrap.Modal
                .getOrCreateInstance(elemento)
                .show();
            return true;
        }

        return false;
    }

    function mostrarDialogoTrama({
        titulo = 'Información',
        mensaje = '',
        confirmar = false,
        textoAceptar = 'Entendido',
        textoCancelar = 'Cancelar',
        destructivo = false,
        elementoEnfoque = null
    } = {}) {
        const modalEl = $('tramaDialogo');

        if (!modalEl || !window.bootstrap) {
            return Promise.resolve(
                confirmar
                    ? window.confirm(mensaje)
                    : (window.alert(mensaje), true)
            );
        }

        const tituloEl = $('tramaDialogoTitulo');
        const mensajeEl = $('tramaDialogoMensaje');
        const aceptarEl = $('tramaDialogoAceptar');
        const cancelarEl = $('tramaDialogoCancelar');

        tituloEl.textContent = titulo;
        mensajeEl.textContent = mensaje;
        aceptarEl.textContent = textoAceptar;
        cancelarEl.textContent = textoCancelar;

        aceptarEl.classList.toggle(
            'is-danger',
            destructivo
        );

        cancelarEl.classList.toggle(
            'd-none',
            !confirmar
        );

        return new Promise(resolve => {
            let aceptado = false;

            const manejarClick = event => {
                const boton = event.target.closest(
                    '[data-trama-dialog-result]'
                );

                if (boton) {
                    aceptado =
                        boton.dataset.tramaDialogResult ===
                        'accept';
                }
            };

            const finalizar = () => {
                modalEl.removeEventListener(
                    'click',
                    manejarClick
                );

                if (elementoEnfoque) {
                    elementoEnfoque.focus();
                }

                resolve(aceptado);
            };

            modalEl.addEventListener(
                'click',
                manejarClick
            );

            modalEl.addEventListener(
                'hidden.bs.modal',
                finalizar,
                { once: true }
            );

            bootstrap.Modal
                .getOrCreateInstance(modalEl)
                .show();
        });
    }

    function actualizarAyudaCampo(id, mensaje) {
        const elemento = $(id);

        if (elemento) {
            elemento.textContent = mensaje || '';
        }
    }

    let temporizadorAlerta = null;

    function ocultarAlertaRegistroAgregado() {
        $('alertRegistroAgregado')
            ?.classList.add('d-none');

        if (temporizadorAlerta) {
            clearTimeout(temporizadorAlerta);
            temporizadorAlerta = null;
        }
    }

    function mostrarAlertaRegistroAgregado() {
        const alerta = $('alertRegistroAgregado');

        if (!alerta) return;

        alerta.classList.remove('d-none');

        clearTimeout(temporizadorAlerta);

        temporizadorAlerta = setTimeout(
            ocultarAlertaRegistroAgregado,
            3000
        );
    }

    const cerrarAlerta = document.querySelector(
        '#alertRegistroAgregado .btn-close'
    );

    cerrarAlerta?.addEventListener(
        'click',
        ocultarAlertaRegistroAgregado
    );

    /* =====================================================
       FECHA DE NACIMIENTO
       ===================================================== */

    function normalizarFechaInput(valor) {
        if (valor === null || valor === undefined) {
            return '';
        }

        const texto = String(valor).trim();

        if (!texto) return '';

        let anio, mes, dia;

        // AAAA-MM-DD, incluso con hora ISO
        let coincidencia = texto.match(
            /^(\d{4})-(\d{1,2})-(\d{1,2})/
        );

        if (coincidencia) {
            anio = coincidencia[1];
            mes = coincidencia[2].padStart(2, '0');
            dia = coincidencia[3].padStart(2, '0');
        } else {
            // DD/MM/AAAA o DD-MM-AAAA
            coincidencia = texto.match(
                /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$/
            );

            if (!coincidencia) return '';

            dia = coincidencia[1].padStart(2, '0');
            mes = coincidencia[2].padStart(2, '0');
            anio = coincidencia[3];
        }

        const fecha = `${anio}-${mes}-${dia}`;

        const comprobacion = new Date(
            `${fecha}T12:00:00`
        );

        if (Number.isNaN(comprobacion.getTime())) {
            return '';
        }

        if (
            comprobacion.getFullYear() !== Number(anio) ||
            comprobacion.getMonth() + 1 !== Number(mes) ||
            comprobacion.getDate() !== Number(dia)
        ) {
            return '';
        }

        return fecha;
    }

    function fechaParaExcel(fecha) {
        const fechaNormalizada =
            normalizarFechaInput(fecha);

        if (!fechaNormalizada) return '';

        const [anio, mes, dia] =
            fechaNormalizada.split('-');

        return `${dia}/${mes}/${anio}`;
    }

    function obtenerAvisoFecha() {
        let aviso = $('FecNacimientoApiHint');

        if (!aviso) {
            const campo = $('FecNacimiento');

            if (!campo) return null;

            aviso = document.createElement('div');

            aviso.id = 'FecNacimientoApiHint';
            aviso.className = 'api-hint text-muted';

            campo.insertAdjacentElement(
                'afterend',
                aviso
            );
        }

        return aviso;
    }

    const mensajesFecha = {
        obtenida:
            'Fecha obtenida desde ConsultaPE',

        obtenida_consulta_dni:
            'Fecha obtenida desde ConsultaPE',

        no_disponible_en_fuente:
            'ConsultaPE no encontró la fecha para este DNI.',

        sin_campo_fecha:
            'ConsultaPE no devolvió una fecha reconocible.',

        error_http_401:
            'Token no autorizado para consultar la fecha.',

        error_http_403:
            'El módulo de fecha está bloqueado o sin permiso.',

        error_http_429:
            'Se alcanzó el límite de consultas.',

        error_conexion:
            'No se pudo conectar al módulo de fecha.',

        error_interno:
            'No se pudo procesar la fecha de nacimiento.',

        respuesta_invalida:
            'Respuesta de fecha inválida.'
    };

    /* =====================================================
       NORMALIZAR SEXO
       ===================================================== */

    function normalizarSexo(valor) {
        const texto = String(valor || '')
            .trim()
            .toUpperCase();

        if (
            texto === 'M' ||
            texto.startsWith('MASC')
        ) {
            return 'M';
        }

        if (
            texto === 'F' ||
            texto.startsWith('FEM')
        ) {
            return 'F';
        }

        return '';
    }

    /* =====================================================
       NORMALIZAR ESTADO CIVIL
       ===================================================== */

    function normalizarEstadoCivil(valor) {
        const texto = String(valor || '')
            .trim()
            .toLowerCase();

        if (!texto) return '';

        const opciones = Array.from(
            $('EstadoCivil')?.options || []
        );

        const opcion = opciones.find(item => {
            return (
                item.value.toLowerCase() === texto ||
                item.textContent
                    .trim()
                    .toLowerCase() === texto
            );
        });

        if (opcion) return opcion.value;

        const equivalencias = {
            s: 'Soltero',
            c: 'Casado',
            d: 'Divorciado',
            v: 'Viudo'
        };

        return equivalencias[texto] || '';
    }

    /* =====================================================
       CONSULTAR DNI Y RUC - CONSULTAPE
       ===================================================== */

    async function consultarDocumento() {
        const tipo = $('TipoIdent').value === '1'
            ? 'DNI'
            : 'RUC';

        const numero = $('NumIdent')
            .value
            .trim();

        const longitud = tipo === 'DNI' ? 8 : 11;

        const patron = new RegExp(
            `^\\d{${longitud}}$`
        );

        if (!patron.test(numero)) {
            await mostrarDialogoTrama({
                titulo: 'Documento incorrecto',
                mensaje:
                    `El ${tipo} debe contener exactamente ` +
                    `${longitud} dígitos.`,
                elementoEnfoque: $('NumIdent')
            });
            return;
        }

        const textoOriginal = btnConsultar.textContent;
        const avisoFecha = obtenerAvisoFecha();

        btnConsultar.disabled = true;
        btnConsultar.textContent = 'Buscando...';

        actualizarAyudaCampo(
            'SexoApiHint',
            ''
        );

        actualizarAyudaCampo(
            'EstadoCivilApiHint',
            ''
        );

        if (avisoFecha) {
            avisoFecha.textContent =
                tipo === 'DNI'
                    ? 'Consultando fecha de nacimiento...'
                    : '';
        }

        try {
            const parametros = new URLSearchParams({
                tipo_documento: tipo,
                numero_documento: numero,
                modo: 'basico'
            });

            const url =
                '/api/clientes/documento-lookup?' +
                parametros.toString();

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'same-origin',
                cache: 'no-store',
                headers: {
                    'Accept': 'application/json'
                }
            });

            const result = await response.json();

            if (
                !response.ok ||
                !result.ok ||
                !result.data
            ) {
                throw new Error(
                    result.error ||
                    'No se encontraron datos.'
                );
            }

            const data = result.data;

            /* ============================================
               1. NOMBRES
               ============================================ */

            $('Nombres').value =
                data.nombres || '';

            /* ============================================
               2. APELLIDO PATERNO
               ============================================ */

            $('ApPaterno').value =
                data.apellido_paterno || '';

            /* ============================================
               3. APELLIDO MATERNO
               ============================================ */

            $('ApMaterno').value =
                data.apellido_materno || '';

            /* ============================================
               4. FECHA DE NACIMIENTO
               ============================================ */

            const fechaRecibida =
                data.fecha_nacimiento ||
                data.fechaNacimiento ||
                data.fecha_nac ||
                '';

            const fechaNormalizada =
                normalizarFechaInput(
                    fechaRecibida
                );

            const campoFecha = $('FecNacimiento');

            campoFecha.value = fechaNormalizada;

            if (avisoFecha) {
                if (tipo === 'RUC') {
                    avisoFecha.textContent =
                        'No aplica para RUC';
                } else if (campoFecha.value) {
                    avisoFecha.textContent =
                        'Fecha obtenida desde ConsultaPE';
                } else {
                    avisoFecha.textContent =
                        mensajesFecha[result.estado_fecha] ||
                        'Fecha no disponible. Ingrésala manualmente.';
                }
            }

            /* ============================================
               SEXO (SI LA API LO PROPORCIONA)
               ============================================ */

            const sexo = normalizarSexo(
                data.sexo
            );

            $('Sexo').value = sexo;

            actualizarAyudaCampo(
                'SexoApiHint',
                sexo
                    ? 'Dato obtenido'
                    : 'Dato no disponible'
            );

            /* ============================================
               ESTADO CIVIL
               ============================================ */

            const estadoCivil =
                normalizarEstadoCivil(
                    data.estado_civil
                );

            $('EstadoCivil').value =
                estadoCivil;

            actualizarAyudaCampo(
                'EstadoCivilApiHint',
                estadoCivil
                    ? 'Dato obtenido'
                    : 'Dato no disponible'
            );

            /* ============================================
               DIAGNÓSTICO
               ============================================ */

            console.info(
                '[ConsultaPE] Consulta correcta:',
                tipo
            );

            console.info(
                '[ConsultaPE] Estado de fecha:',
                result.estado_fecha
            );

            console.info(
                '[ConsultaPE] Fecha presente:',
                Boolean(fechaRecibida)
            );

            console.info(
                '[ConsultaPE] Fecha válida:',
                Boolean(campoFecha.value)
            );

        } catch (error) {
            console.error(
                '[ConsultaPE] Error:',
                error
            );

            if (avisoFecha) {
                avisoFecha.textContent = '';
            }

            await mostrarDialogoTrama({
                titulo: 'No se pudo realizar la consulta',
                mensaje:
                    error.message ||
                    'Comprueba la conexión e inténtalo nuevamente.'
            });

        } finally {
            btnConsultar.disabled = false;
            btnConsultar.textContent = textoOriginal;
        }
    }

    btnConsultar.addEventListener(
        'click',
        consultarDocumento
    );

    /* =====================================================
       TABLA DE REGISTROS
       ===================================================== */

    const CAMPOS_TRAMA = [
        'Nombres',
        'ApPaterno',
        'ApMaterno',
        'TipoTrabajador',
        'PaisNacimiento',
        'TipoIdent',
        'NumIdent',
        'Sexo',
        'FecNacimiento',
        'Moneda',
        'Remuneracion',
        'EstadoCivil',
        'Sede'
    ];

    function obtenerFilas() {
        return Array.from(
            tabla.querySelectorAll('tbody tr')
        );
    }

    function actualizarNumeracion() {
        obtenerFilas().forEach((fila, indice) => {
            if (fila.cells[0]) {
                fila.cells[0].textContent =
                    indice + 1;

                fila.cells[0].classList.add(
                    'numero-registro'
                );
            }
        });
    }

    function actualizarContador() {
        const cantidad = obtenerFilas().length;

        const contador = $('contadorRegistros');

        if (!contador) return;

        contador.textContent =
            cantidad === 1
                ? '1 registro'
                : `${cantidad} registros`;

        contador.classList.toggle(
            'limite',
            cantidad >= MAX_REGISTROS_TRAMA
        );
    }

    /* =====================================================
       OBTENER DATOS DEL FORMULARIO
       ===================================================== */

    function obtenerRegistroActualFormulario() {
        const nombres = $('Nombres').value.trim();
        const paterno = $('ApPaterno').value.trim();
        const materno = $('ApMaterno').value.trim();

        if (!nombres && !paterno && !materno) {
            return null;
        }

        const registro = {};

        CAMPOS_TRAMA.forEach(id => {
            const elemento = $(id);

            registro[id] = elemento
                ? String(elemento.value || '').trim()
                : '';
        });

        registro.FecNacimiento = fechaParaExcel(
            $('FecNacimiento').value
        );

        return registro;
    }

    function obtenerRegistrosTrama() {
        return obtenerFilas().map(fila => {
            const registro = {};

            CAMPOS_TRAMA.forEach((campo, indice) => {
                registro[campo] = (
                    fila.cells[indice + 1]
                        ?.textContent || ''
                ).trim();
            });

            return registro;
        });
    }

    /* =====================================================
       VALIDACIONES DEL FORMULARIO
       ===================================================== */

    async function validarRegistro() {
        const tipo = $('TipoIdent').value.trim();
        const numero = $('NumIdent').value.trim();

        if (!numero) {
            if (!mostrarModal('tramaDocumentoRequerido')) {
                await mostrarDialogoTrama({
                    titulo: 'Documento requerido',
                    mensaje:
                        'Ingrese el número de DNI o RUC.',
                    elementoEnfoque: $('NumIdent')
                });
            }
            return false;
        }

        if (
            tipo === '1' &&
            !/^\d{8}$/.test(numero)
        ) {
            await mostrarDialogoTrama({
                titulo: 'DNI no válido',
                mensaje:
                    'El DNI debe tener exactamente 8 dígitos.',
                elementoEnfoque: $('NumIdent')
            });
            return false;
        }

        if (
            tipo === '6' &&
            !/^\d{11}$/.test(numero)
        ) {
            await mostrarDialogoTrama({
                titulo: 'RUC no válido',
                mensaje:
                    'El RUC debe tener exactamente 11 dígitos.',
                elementoEnfoque: $('NumIdent')
            });
            return false;
        }

        const duplicado = obtenerFilas().some(fila => {
            return (
                fila.cells[6]?.textContent.trim() === tipo &&
                fila.cells[7]?.textContent.trim() === numero
            );
        });

        if (duplicado) {
            const tipoTexto = tipo === '1'
                ? 'DNI'
                : 'RUC';

            const mensaje =
                `El ${tipoTexto} N.º ${numero} ya ` +
                'se encuentra registrado en esta trama.';

            if ($('tramaDocumentoDuplicadoMensaje')) {
                $('tramaDocumentoDuplicadoMensaje')
                    .textContent = mensaje;
            }

            if (!mostrarModal('tramaDocumentoDuplicado')) {
                await mostrarDialogoTrama({
                    titulo: 'Documento duplicado',
                    mensaje
                });
            }

            return false;
        }

        if (
            !$('Nombres').value.trim() ||
            !$('ApPaterno').value.trim() ||
            !$('ApMaterno').value.trim()
        ) {
            await mostrarDialogoTrama({
                titulo: 'Datos incompletos',
                mensaje:
                    'Complete nombres, apellido paterno ' +
                    'y apellido materno.'
            });
            return false;
        }

        if (!$('Sexo').value.trim()) {
            await mostrarDialogoTrama({
                titulo: 'Sexo requerido',
                mensaje: 'Seleccione el sexo del cliente.',
                elementoEnfoque: $('Sexo')
            });
            return false;
        }

        if (!$('FecNacimiento').value.trim()) {
            await mostrarDialogoTrama({
                titulo: 'Fecha de nacimiento requerida',
                mensaje:
                    'Ingrese la fecha de nacimiento.',
                elementoEnfoque: $('FecNacimiento')
            });
            return false;
        }

        if (!$('EstadoCivil').value.trim()) {
            await mostrarDialogoTrama({
                titulo: 'Estado civil requerido',
                mensaje:
                    'Seleccione el estado civil del cliente.',
                elementoEnfoque: $('EstadoCivil')
            });
            return false;
        }

        const remuneracion =
            $('Remuneracion').value.trim();

        if (
            remuneracion === '' ||
            !Number.isFinite(Number(remuneracion)) ||
            Number(remuneracion) < 0
        ) {
            await mostrarDialogoTrama({
                titulo: 'Remuneración no válida',
                mensaje:
                    'Ingrese una remuneración válida.',
                elementoEnfoque: $('Remuneracion')
            });
            return false;
        }

        return true;
    }

    /* =====================================================
       AGREGAR REGISTRO
       ===================================================== */

    async function agregarRegistro() {
        const filas = obtenerFilas();

        if (filas.length >= MAX_REGISTROS_TRAMA) {
            const continuar = await mostrarDialogoTrama({
                titulo: 'Máximo recomendado alcanzado',
                mensaje:
                    `La trama tiene ${filas.length} registros.\n\n` +
                    'El máximo recomendado es 10. ' +
                    '¿Desea continuar?',
                confirmar: true,
                textoAceptar: 'Registrar'
            });

            if (!continuar) return;
        }

        const valido = await validarRegistro();

        if (!valido) return;

        const tbody = tabla.querySelector('tbody');

        const fila = tbody.insertRow();

        const celdaNumero = fila.insertCell();

        celdaNumero.className = 'numero-registro';

        CAMPOS_TRAMA.forEach(campo => {
            const celda = fila.insertCell();

            let valor = $(campo).value;

            if (campo === 'FecNacimiento') {
                valor = fechaParaExcel(valor);
            }

            celda.textContent = valor;
        });

        /* BOTÓN ELIMINAR */

        const celdaAcciones = fila.insertCell();

        celdaAcciones.className = 'text-center';

        const botonEliminar =
            document.createElement('button');

        botonEliminar.type = 'button';

        botonEliminar.className =
            'btn btn-outline-danger btn-sm btn-eliminar';

        botonEliminar.textContent = 'Eliminar';

        botonEliminar.addEventListener(
            'click',
            async () => {
                const nombre =
                    fila.cells[1]?.textContent || '';

                const tipo =
                    fila.cells[6]?.textContent === '1'
                        ? 'DNI'
                        : 'RUC';

                const numero =
                    fila.cells[7]?.textContent || '';

                const confirmar =
                    await mostrarDialogoTrama({
                        titulo: 'Confirmar eliminación',
                        mensaje:
                            '¿Está seguro de eliminar este registro?\n\n' +
                            `Nombre: ${nombre}\n` +
                            `${tipo}: ${numero}\n\n` +
                            'Esta acción no se puede deshacer.',
                        confirmar: true,
                        textoAceptar: 'Eliminar',
                        destructivo: true
                    });

                if (!confirmar) return;

                fila.remove();

                actualizarNumeracion();
                actualizarContador();
            }
        );

        celdaAcciones.appendChild(botonEliminar);

        actualizarNumeracion();
        actualizarContador();

        mostrarAlertaRegistroAgregado();

        /* LIMPIAR FORMULARIO */

        formulario.reset();

        $('PaisNacimiento').value = 'Perú';
        $('Moneda').value = 'S/.';
        $('Remuneracion').value = '0';
        $('Sede').value = 'Principal';

        actualizarAyudaCampo(
            'SexoApiHint',
            ''
        );

        actualizarAyudaCampo(
            'EstadoCivilApiHint',
            ''
        );

        const avisoFecha = obtenerAvisoFecha();

        if (avisoFecha) {
            avisoFecha.textContent = '';
        }
    }

    btnAgregar?.addEventListener(
        'click',
        agregarRegistro
    );

    /* =====================================================
       EXPORTAR EXCEL
       ===================================================== */

    async function exportarExcel() {
        const registros = obtenerRegistrosTrama();

        const registroActual =
            obtenerRegistroActualFormulario();

        if (registroActual) {
            registros.push(registroActual);
        }

        if (registros.length === 0) {
            await mostrarDialogoTrama({
                titulo: 'Sin registros',
                mensaje:
                    'No hay registros para exportar.'
            });
            return;
        }

        if (registros.length > MAX_REGISTROS_TRAMA) {
            const continuar = await mostrarDialogoTrama({
                titulo: 'Más de 10 registros',
                mensaje:
                    `La trama contiene ${registros.length} registros.\n\n` +
                    '¿Desea continuar con la exportación?',
                confirmar: true,
                textoAceptar: 'Exportar'
            });

            if (!continuar) return;
        }

        const textoOriginal = btnExportar.textContent;

        btnExportar.disabled = true;
        btnExportar.textContent =
            'Generando Excel...';

        try {
            const respuesta = await fetch(
                '/clientes/trama/export',
                {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type':
                            'application/json'
                    },
                    body: JSON.stringify({
                        rows: registros
                    })
                }
            );

            if (!respuesta.ok) {
                const error = await respuesta
                    .json()
                    .catch(() => ({}));

                throw new Error(
                    error.error ||
                    'No se pudo generar el Excel.'
                );
            }

            const blob = await respuesta.blob();

            const disposition =
                respuesta.headers.get(
                    'Content-Disposition'
                ) || '';

            let nombreArchivo =
                'Trama_Clientes.xlsx';

            const coincidencia = disposition.match(
                /filename\*?=["']?(?:UTF-8'')?([^;"']+)/i
            );

            if (coincidencia?.[1]) {
                try {
                    nombreArchivo = decodeURIComponent(
                        coincidencia[1].trim()
                    );
                } catch {
                    nombreArchivo =
                        coincidencia[1].trim();
                }
            }

            /* GUARDAR ARCHIVO */

            if ('showSaveFilePicker' in window) {
                const archivo = await window
                    .showSaveFilePicker({
                        suggestedName: nombreArchivo,
                        types: [{
                            description: 'Archivo Excel',
                            accept: {
                                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                                    ['.xlsx']
                            }
                        }]
                    });

                const writable =
                    await archivo.createWritable();

                await writable.write(blob);
                await writable.close();

                await mostrarDialogoTrama({
                    titulo: 'Exportación completada',
                    mensaje:
                        'Excel guardado correctamente.'
                });

            } else {
                const urlArchivo =
                    URL.createObjectURL(blob);

                const enlace =
                    document.createElement('a');

                enlace.href = urlArchivo;
                enlace.download = nombreArchivo;

                document.body.appendChild(enlace);
                enlace.click();
                enlace.remove();

                setTimeout(
                    () => URL.revokeObjectURL(urlArchivo),
                    1000
                );
            }

        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }

            console.error(
                'Error exportando Excel:',
                error
            );

            await mostrarDialogoTrama({
                titulo: 'No se pudo exportar',
                mensaje:
                    error.message ||
                    'No se pudo exportar la trama.'
            });

        } finally {
            btnExportar.disabled = false;
            btnExportar.textContent = textoOriginal;
        }
    }

    btnExportar?.addEventListener(
        'click',
        exportarExcel
    );

    /* =====================================================
       INICIALIZACIÓN
       ===================================================== */

    actualizarNumeracion();
    actualizarContador();
    obtenerAvisoFecha();

    console.info(
        '[SIS-ARIAS] Generador de Tramas inicializado.'
    );

})();
