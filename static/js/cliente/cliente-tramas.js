/* =========================================================
       CONFIGURACIÓN
    ========================================================== */

    const MAX_REGISTROS_TRAMA = 10;

    const alertRegistroAgregado =
        document.getElementById('alertRegistroAgregado');
    const documentoRequeridoModalEl =
        document.getElementById('tramaDocumentoRequerido');
    const documentoRequeridoModal =
        documentoRequeridoModalEl && window.bootstrap
            ? window.bootstrap.Modal.getOrCreateInstance(documentoRequeridoModalEl)
            : null;

    let temporizadorAlertaRegistro = null;

    function ocultarAlertaRegistroAgregado() {
        if (!alertRegistroAgregado) {
            return;
        }

        alertRegistroAgregado.classList.add('d-none');
        temporizadorAlertaRegistro = null;
    }

    function mostrarAlertaRegistroAgregado() {
        if (!alertRegistroAgregado) {
            return;
        }

        window.clearTimeout(temporizadorAlertaRegistro);
        alertRegistroAgregado.classList.remove('d-none');
        temporizadorAlertaRegistro = window.setTimeout(
            ocultarAlertaRegistroAgregado,
            3000
        );
    }

    if (alertRegistroAgregado) {
        const btnCerrarAlerta =
            alertRegistroAgregado.querySelector('.btn-close');

        if (btnCerrarAlerta) {
            btnCerrarAlerta.addEventListener(
                'click',
                () => {
                    window.clearTimeout(temporizadorAlertaRegistro);
                    ocultarAlertaRegistroAgregado();
                }
            );
        }
    }

    if (documentoRequeridoModalEl) {
        documentoRequeridoModalEl.addEventListener('hidden.bs.modal', () => {
            document.getElementById('NumIdent')?.focus();
        });
    }


    /* =========================================================
       ACTUALIZAR NUMERACIÓN N°
       
       Esta función vuelve a numerar todas las filas:
       1
       2
       3
       4
       ...
       
       Si se elimina la fila 2:
       1
       2
       3
       
       Así nunca quedan saltos.
    ========================================================== */

    function actualizarNumeracion() {

        const filas = Array.from(
            document.querySelectorAll(
                '#tablaTramas tbody tr'
            )
        );

        filas.forEach((row, index) => {

            if (row.cells[0]) {

                row.cells[0].textContent =
                    index + 1;

                row.cells[0].classList.add(
                    'numero-registro'
                );

            }

        });

    }


    /* =========================================================
       ACTUALIZAR CONTADOR
    ========================================================== */

    function actualizarContador() {

        const cantidad =
            document.querySelectorAll(
                '#tablaTramas tbody tr'
            ).length;

        const contador =
            document.getElementById(
                'contadorRegistros'
            );

        if (!contador) {
            return;
        }

        contador.textContent =
            cantidad === 1
                ? '1 registro'
                : `${cantidad} registros`;

        if (cantidad >= MAX_REGISTROS_TRAMA) {

            contador.classList.add(
                'limite'
            );

        } else {

            contador.classList.remove(
                'limite'
            );

        }

    }


    /* =========================================================
       NORMALIZAR FECHA
    ========================================================== */

    function normalizarFechaInput(valor) {

        const texto =
            (valor || '').trim();

        if (!texto) {
            return '';
        }

        if (
            /^\d{4}-\d{2}-\d{2}$/.test(texto)
        ) {

            return texto;

        }

        const match =
            texto.match(
                /^(\d{2})[\/-](\d{2})[\/-](\d{4})$/
            );

        if (match) {

            const [
                ,
                dd,
                mm,
                yyyy
            ] = match;

            return `${yyyy}-${mm}-${dd}`;

        }

        return '';

    }


    /* =========================================================
       NORMALIZAR ESTADO CIVIL
    ========================================================== */

    function normalizarEstadoCivil(valor) {

        const texto =
            (valor || '')
                .trim()
                .toUpperCase();

        if (!texto) {
            return '';
        }

        if (texto.startsWith('S')) {
            return 'S';
        }

        if (texto.startsWith('C')) {
            return 'C';
        }

        return '';

    }


    /* =========================================================
       NORMALIZAR SEXO
    ========================================================== */

    function normalizarSexo(valor) {

        const texto =
            (valor || '')
                .trim()
                .toUpperCase();

        if (!texto) {
            return '';
        }

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


    /* =========================================================
       AYUDA CAMPOS
    ========================================================== */

    function actualizarAyudaCampo(
        id,
        mensaje
    ) {

        const el =
            document.getElementById(id);

        if (!el) {
            return;
        }

        el.textContent =
            mensaje || '';

    }


    /* =========================================================
       OBTENER REGISTROS DE TABLA

       IMPORTANTE:
       La columna N° NO se envía al Excel.

       Por eso los índices se manejan desde la
       posición 1 de la tabla.
    ========================================================== */

    function obtenerRegistrosTrama() {

        const headers = [

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

        const rows =
            Array.from(
                document.querySelectorAll(
                    '#tablaTramas tbody tr'
                )
            );

        return rows.map(row => {

            const cells =
                Array.from(row.cells);

            const item = {};

            headers.forEach(
                (header, index) => {

                    item[header] =
                        (
                            cells[index + 1]
                                ?.textContent || ''
                        ).trim();

                }
            );

            return item;

        });

    }


    /* =========================================================
       OBTENER REGISTRO ACTUAL DEL FORMULARIO
    ========================================================== */

    function obtenerRegistroActualFormulario() {

        const nombres =
            (
                document.getElementById(
                    'Nombres'
                ).value || ''
            ).trim();

        const apPaterno =
            (
                document.getElementById(
                    'ApPaterno'
                ).value || ''
            ).trim();

        const apMaterno =
            (
                document.getElementById(
                    'ApMaterno'
                ).value || ''
            ).trim();


        /*
         * Si NO hay ningún dato del formulario,
         * no agregamos un registro al exportar.
         */

        if (
            !nombres &&
            !apPaterno &&
            !apMaterno
        ) {

            return null;

        }


        const fechaInput =
            (
                document.getElementById(
                    'FecNacimiento'
                ).value || ''
            ).trim();

        let fecha = fechaInput;

        if (fechaInput) {

            const partes =
                fechaInput.split('-');

            if (partes.length === 3) {

                const [
                    yyyy,
                    mm,
                    dd
                ] = partes;

                fecha =
                    `${dd}/${mm}/${yyyy}`;

            }

        }


        return {

            Nombres:
                nombres,

            ApPaterno:
                apPaterno,

            ApMaterno:
                apMaterno,

            TipoTrabajador:
                document.getElementById(
                    'TipoTrabajador'
                ).value.trim(),

            PaisNacimiento:
                document.getElementById(
                    'PaisNacimiento'
                ).value.trim(),

            TipoIdent:
                document.getElementById(
                    'TipoIdent'
                ).value.trim(),

            NumIdent:
                document.getElementById(
                    'NumIdent'
                ).value.trim(),

            Sexo:
                document.getElementById(
                    'Sexo'
                ).value.trim(),

            FecNacimiento:
                fecha,

            Moneda:
                document.getElementById(
                    'Moneda'
                ).value.trim(),

            Remuneracion:
                document.getElementById(
                    'Remuneracion'
                ).value.trim(),

            EstadoCivil:
                document.getElementById(
                    'EstadoCivil'
                ).value.trim(),

            Sede:
                document.getElementById(
                    'Sede'
                ).value.trim()

        };

    }


    /* =========================================================
       CONSULTAR DNI / RUC
    ========================================================== */

    document
        .getElementById('btnConsultar')
        .addEventListener(
            'click',
            async () => {

                const tipo =
                    document.getElementById(
                        'TipoIdent'
                    ).value === '1'
                        ? 'DNI'
                        : 'RUC';

                const numero =
                    document.getElementById(
                        'NumIdent'
                    ).value.trim();


                if (!numero) {

                    alert(
                        'Número de documento requerido.\n\n' +
                        'Ingrese el DNI o RUC para realizar la consulta.'
                    );

                    document.getElementById(
                        'NumIdent'
                    ).focus();

                    return;

                }


                try {

                    actualizarAyudaCampo(
                        'SexoApiHint',
                        ''
                    );

                    actualizarAyudaCampo(
                        'EstadoCivilApiHint',
                        ''
                    );


                    const btn =
                        document.getElementById(
                            'btnConsultar'
                        );

                    const textoOriginal =
                        btn.textContent;


                    btn.disabled = true;

                    btn.textContent =
                        'Buscando...';


                    const qs =
                        new URLSearchParams({

                            tipo_documento:
                                tipo,

                            numero_documento:
                                numero,

                            modo:
                                'basico'

                        });


                    const response =
                        await fetch(
                            `/api/clientes/documento-lookup?${qs.toString()}`
                        );


                    const result =
                        await response.json();


                    if (
                        response.ok &&
                        result.ok &&
                        result.data
                    ) {

                        const data =
                            result.data || {};


                        document.getElementById(
                            'ApPaterno'
                        ).value =
                            data.apellido_paterno || '';


                        document.getElementById(
                            'ApMaterno'
                        ).value =
                            data.apellido_materno || '';


                        document.getElementById(
                            'Nombres'
                        ).value =
                            data.nombres || '';


                        const fecha =
                            normalizarFechaInput(
                                data.fecha_nacimiento
                            );


                        document.getElementById(
                            'FecNacimiento'
                        ).value =
                            fecha;


                        const sexo =
                            normalizarSexo(
                                data.sexo
                            );


                        document.getElementById(
                            'Sexo'
                        ).value =
                            sexo;


                        const estadoCivil =
                            normalizarEstadoCivil(
                                data.estado_civil
                            );


                        document.getElementById(
                            'EstadoCivil'
                        ).value =
                            estadoCivil;


                        actualizarAyudaCampo(
                            'SexoApiHint',
                            sexo
                                ? 'Dato obtenido'
                                : 'Dato no disponible'
                        );


                        actualizarAyudaCampo(
                            'EstadoCivilApiHint',
                            estadoCivil
                                ? 'Dato obtenido'
                                : 'Dato no disponible'
                        );


                    } else {

                        alert(
                            result.error ||
                            'No se encontraron datos para el documento.'
                        );

                    }


                    btn.disabled = false;

                    btn.textContent =
                        textoOriginal;


                } catch (error) {

                    console.error(
                        'Error al consultar:',
                        error
                    );


                    const btn =
                        document.getElementById(
                            'btnConsultar'
                        );


                    btn.disabled = false;

                    btn.textContent =
                        'Buscar';


                    alert(
                        'No se pudo realizar la consulta.\n\n' +
                        'Verifique su conexión e inténtelo nuevamente.'
                    );

                }

            }
        );


    /* =========================================================
       AGREGAR REGISTRO
    ========================================================== */

    document
        .getElementById('btnAgregar')
        .addEventListener(
            'click',
            () => {

                const tbody =
                    document.querySelector(
                        '#tablaTramas tbody'
                    );


                const cantidadRegistros =
                    tbody.querySelectorAll(
                        'tr'
                    ).length;


                /* =================================================
                   DESDE EL REGISTRO 11 PREGUNTAR
                ================================================== */

                if (
                    cantidadRegistros >=
                    MAX_REGISTROS_TRAMA
                ) {

                    const continuar =
                        window.confirm(

                            'MÁXIMO RECOMENDADO ALCANZADO\n\n' +

                            `La trama tiene actualmente ${cantidadRegistros} registros.\n\n` +

                            'El máximo recomendado es de 10 registros.\n\n' +

                            '¿Está seguro de que desea registrar una persona adicional?\n\n' +

                            'Aceptar = Registrar\n' +

                            'Cancelar = No registrar'

                        );


                    if (!continuar) {
                        return;
                    }

                }


                /* =================================================
                   DOCUMENTO
                ================================================== */

                const tipoIdent =
                    document.getElementById(
                        'TipoIdent'
                    ).value.trim();


                const numIdent =
                    document.getElementById(
                        'NumIdent'
                    ).value.trim();


                if (!numIdent) {
                    if (documentoRequeridoModal) {
                        documentoRequeridoModal.show();
                    } else {
                        console.error('No se pudo abrir el aviso de documento requerido.');
                    }

                    return;

                }


                /* =================================================
                   VALIDAR DNI
                ================================================== */

                if (
                    tipoIdent === '1' &&
                    !/^\d{8}$/.test(
                        numIdent.replace(/\s+/g, '')
                    )
                ) {

                    alert(
                        'DNI NO VÁLIDO\n\n' +
                        'El DNI debe contener exactamente 8 dígitos.'
                    );

                    document.getElementById(
                        'NumIdent'
                    ).focus();

                    return;

                }


                /* =================================================
                   VALIDAR RUC
                ================================================== */

                if (
                    tipoIdent === '6' &&
                    !/^\d{11}$/.test(
                        numIdent.replace(/\s+/g, '')
                    )
                ) {

                    alert(
                        'RUC NO VÁLIDO\n\n' +
                        'El RUC debe contener exactamente 11 dígitos.'
                    );

                    document.getElementById(
                        'NumIdent'
                    ).focus();

                    return;

                }


                /* =================================================
                   NORMALIZAR DOCUMENTO
                ================================================== */

                const documentoNuevo =
                    numIdent
                        .replace(/\s+/g, '')
                        .toUpperCase();


                /* =================================================
                   VALIDAR DOCUMENTO DUPLICADO
                ================================================== */

                const filas =
                    Array.from(
                        tbody.querySelectorAll(
                            'tr'
                        )
                    );


                const documentoDuplicado =
                    filas.some(row => {

                        /*
                         * Ahora la columna N° ocupa
                         * la posición 0.
                         *
                         * TipoIdent = posición 6
                         * NumIdent  = posición 7
                         */

                        const tipo =
                            (
                                row.cells[6]
                                    ?.textContent || ''
                            ).trim();


                        const numero =
                            (
                                row.cells[7]
                                    ?.textContent || ''
                            )
                                .trim()
                                .replace(
                                    /\s+/g,
                                    ''
                                )
                                .toUpperCase();


                        return (
                            tipo === tipoIdent &&
                            numero === documentoNuevo
                        );

                    });


                if (documentoDuplicado) {

                    const tipoTexto =
                        tipoIdent === '1'
                            ? 'DNI'
                            : 'RUC';

                    const modalElement =
                        document.getElementById(
                            'tramaDocumentoDuplicado'
                        );

                    const modalMessage =
                        document.getElementById(
                            'tramaDocumentoDuplicadoMensaje'
                        );

                    modalMessage.textContent =
                        `El ${tipoTexto} N.º ${numIdent} ya se encuentra registrado en esta trama.`;

                    modalElement.addEventListener(
                        'hidden.bs.modal',
                        () => {
                            document.getElementById(
                                'NumIdent'
                            ).focus();
                        },
                        { once: true }
                    );

                    window.bootstrap.Modal
                        .getOrCreateInstance(modalElement)
                        .show();

                    return;

                }


                /* =================================================
                   VALIDAR NOMBRES Y APELLIDOS
                ================================================== */

                const nombres =
                    document.getElementById(
                        'Nombres'
                    ).value.trim();


                const apPaterno =
                    document.getElementById(
                        'ApPaterno'
                    ).value.trim();


                const apMaterno =
                    document.getElementById(
                        'ApMaterno'
                    ).value.trim();


                /*
                 * IMPORTANTE:
                 * Debe ser || y no &&.
                 */

                if (
                    !nombres ||
                    !apPaterno ||
                    !apMaterno
                ) {

                    alert(

                        'DATOS INCOMPLETOS\n\n' +

                        'Complete los nombres, apellido paterno y apellido materno antes de agregar el registro.'

                    );

                    return;

                }


                /* =================================================
                   VALIDAR TIPO DE TRABAJADOR
                ================================================== */

                const tipoTrabajador =
                    document.getElementById(
                        'TipoTrabajador'
                    ).value.trim();


                /* =================================================
                   VALIDAR SEXO
                ================================================== */

                const sexo =
                    document.getElementById(
                        'Sexo'
                    ).value.trim();


                if (!sexo) {

                    alert(

                        'SEXO REQUERIDO\n\n' +

                        'Seleccione el sexo del cliente.'

                    );

                    document.getElementById(
                        'Sexo'
                    ).focus();

                    return;

                }


                /* =================================================
                   VALIDAR FECHA
                ================================================== */

                const fechaNacimiento =
                    document.getElementById(
                        'FecNacimiento'
                    ).value.trim();


                if (!fechaNacimiento) {

                    alert(

                        'FECHA DE NACIMIENTO REQUERIDA\n\n' +

                        'Ingrese la fecha de nacimiento.'

                    );

                    document.getElementById(
                        'FecNacimiento'
                    ).focus();

                    return;

                }


                /* =================================================
                   VALIDAR ESTADO CIVIL
                ================================================== */

                const estadoCivil =
                    document.getElementById(
                        'EstadoCivil'
                    ).value.trim();


                if (!estadoCivil) {

                    alert(

                        'ESTADO CIVIL REQUERIDO\n\n' +

                        'Seleccione el estado civil.'

                    );

                    document.getElementById(
                        'EstadoCivil'
                    ).focus();

                    return;

                }


                /* =================================================
                   VALIDAR REMUNERACIÓN
                ================================================== */

                const remuneracion =
                    document.getElementById(
                        'Remuneracion'
                    ).value.trim();


                if (
                    remuneracion === '' ||
                    Number(remuneracion) < 0
                ) {

                    alert(

                        'REMUNERACIÓN NO VÁLIDA\n\n' +

                        'Ingrese una remuneración válida.'

                    );

                    document.getElementById(
                        'Remuneracion'
                    ).focus();

                    return;

                }


                /* =================================================
                   CREAR FILA
                ================================================== */

                const row =
                    tbody.insertRow();


                /*
                 * PRIMERA CELDA:
                 * N°
                 */

                const numeroCell =
                    row.insertCell();

                numeroCell.className =
                    'numero-registro';


                /* =================================================
                   CAMPOS
                ================================================== */

                const campos = [

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


                campos.forEach(id => {

                    const cell =
                        row.insertCell();


                    let valor =
                        document.getElementById(
                            id
                        ).value;


                    /* =================================================
                       FECHA DD/MM/YYYY
                    ================================================== */

                    if (
                        id === 'FecNacimiento' &&
                        valor
                    ) {

                        const partes =
                            valor.split('-');


                        if (
                            partes.length === 3
                        ) {

                            const [
                                yyyy,
                                mm,
                                dd
                            ] = partes;


                            valor =
                                `${dd}/${mm}/${yyyy}`;

                        }

                    }


                    cell.textContent =
                        valor;

                });


                /* =================================================
                   ACCIONES
                ================================================== */

                const acciones =
                    row.insertCell();


                acciones.className =
                    'text-center';


                const btnEliminar =
                    document.createElement(
                        'button'
                    );


                btnEliminar.type =
                    'button';


                btnEliminar.className =
                    'btn btn-outline-danger btn-sm btn-eliminar';


                btnEliminar.innerHTML =
                    'Eliminar';


                btnEliminar.addEventListener(
                    'click',
                    () => {

                        /*
                         * N° está en 0
                         * Nombres está en 1
                         * TipoIdent está en 6
                         * NumIdent está en 7
                         */

                        const nombre =
                            row.cells[1]
                                ?.textContent || '';


                        const tipoDocumento =
                            row.cells[6]
                                ?.textContent === '1'
                                ? 'DNI'
                                : 'RUC';


                        const numeroDocumento =
                            row.cells[7]
                                ?.textContent || '';


                        const confirmar =
                            window.confirm(

                                'CONFIRMAR ELIMINACIÓN\n\n' +

                                '¿Está seguro de eliminar este registro?\n\n' +

                                `Nombre: ${nombre}\n` +

                                `${tipoDocumento}: ${numeroDocumento}\n\n` +

                                'Esta acción no se puede deshacer.'

                            );


                        if (confirmar) {

                            row.remove();

                            /*
                             * Reordenar N°
                             */

                            actualizarNumeracion();

                            actualizarContador();

                        }

                    }
                );


                acciones.appendChild(
                    btnEliminar
                );

                mostrarAlertaRegistroAgregado();


                /* =================================================
                   ACTUALIZAR N°
                   
                   Ejemplo:
                   Registro agregado -> 1
                   Registro agregado -> 2
                   Registro agregado -> 3
                ================================================== */

                actualizarNumeracion();


                /* =================================================
                   LIMPIAR FORMULARIO
                ================================================== */

                document
                    .getElementById(
                        'tramaForm'
                    )
                    .reset();


                document.getElementById(
                    'PaisNacimiento'
                ).value =
                    'Perú';


                document.getElementById(
                    'Moneda'
                ).value =
                    'S/.';


                document.getElementById(
                    'Remuneracion'
                ).value =
                    '0';


                document.getElementById(
                    'Sede'
                ).value =
                    'Principal';


                actualizarAyudaCampo(
                    'SexoApiHint',
                    ''
                );


                actualizarAyudaCampo(
                    'EstadoCivilApiHint',
                    ''
                );


                actualizarContador();

            }
        );


    /* =========================================================
       EXPORTAR EXCEL
    ========================================================== */

    document
        .getElementById('btnExportarExcel')
        .addEventListener(
            'click',
            async () => {

                const rows =
                    obtenerRegistrosTrama();


                const currentRow =
                    obtenerRegistroActualFormulario();


                if (currentRow) {

                    rows.push(
                        currentRow
                    );

                }


                if (!rows.length) {

                    alert(
                        'No hay registros para exportar.'
                    );

                    return;

                }


                /* =================================================
                   CONFIRMAR EXPORTACIÓN SI SUPERA 10
                ================================================== */

                if (
                    rows.length >
                    MAX_REGISTROS_TRAMA
                ) {

                    const continuar =
                        window.confirm(

                            'TRAMA CON MÁS DE 10 REGISTROS\n\n' +

                            `La trama contiene ${rows.length} registros.\n\n` +

                            'El máximo recomendado es de 10 registros.\n\n' +

                            '¿Está seguro de que desea continuar con la exportación?\n\n' +

                            'Aceptar = Exportar\n' +

                            'Cancelar = No exportar'

                        );


                    if (!continuar) {
                        return;
                    }

                }


                /* =================================================
                   GENERAR EXCEL
                ================================================== */

                try {

                    const btn =
                        document.getElementById(
                            'btnExportarExcel'
                        );


                    btn.disabled = true;

                    btn.textContent =
                        'Generando Excel...';


                    const response =
                        await fetch(

                            '/clientes/trama/export',

                            {

                                method:
                                    'POST',

                                headers: {

                                    'Content-Type':
                                        'application/json'

                                },

                                body:
                                    JSON.stringify({

                                        rows:
                                            rows

                                    })

                            }

                        );


                    if (!response.ok) {

                        const result =
                            await response
                                .json()
                                .catch(
                                    () => ({})
                                );


                        throw new Error(

                            result.error ||
                            'No se pudo generar el Excel.'

                        );

                    }


                    const blob =
                        await response.blob();


                    const disposition =
                        response.headers.get(
                            'Content-Disposition'
                        ) || '';


                    let filename =
                        'Trama_Clientes.xlsx';


                    const match =
                        disposition.match(
                            /filename\*?=["']?(?:UTF-8'')?([^;"']+)["']?/i
                        );


                    if (
                        match &&
                        match[1]
                    ) {

                        filename =
                            decodeURIComponent(
                                match[1]
                            ).trim();

                    }


                    /* =================================================
                       GUARDAR ARCHIVO
                    ================================================== */

                    if (
                        'showSaveFilePicker'
                        in window
                    ) {

                        const fileHandle =
                            await window
                                .showSaveFilePicker(

                                    {

                                        suggestedName:
                                            filename,

                                        types: [

                                            {

                                                description:
                                                    'Archivo Excel',

                                                accept: {

                                                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                                                        ['.xlsx']

                                                }

                                            }

                                        ]

                                    }

                                );


                        const writable =
                            await fileHandle
                                .createWritable();


                        await writable.write(
                            blob
                        );


                        await writable.close();


                        alert(
                            'Excel guardado correctamente.'
                        );


                    } else {

                        const url =
                            window.URL
                                .createObjectURL(
                                    blob
                                );


                        const link =
                            document.createElement(
                                'a'
                            );


                        link.href =
                            url;


                        link.download =
                            filename;


                        document.body.appendChild(
                            link
                        );


                        link.click();


                        link.remove();


                        window.URL
                            .revokeObjectURL(
                                url
                            );

                    }


                    btn.disabled =
                        false;


                    btn.textContent =
                        'Exportar a Excel';


                } catch (error) {

                    /* =================================================
                       CANCELAR SELECTOR
                    ================================================== */

                    if (
                        error.name ===
                        'AbortError'
                    ) {

                        const btn =
                            document.getElementById(
                                'btnExportarExcel'
                            );


                        btn.disabled =
                            false;


                        btn.textContent =
                            'Exportar a Excel';


                        return;

                    }


                    console.error(
                        'Error exportando:',
                        error
                    );


                    alert(
                        error.message ||
                        'No se pudo exportar la trama.'
                    );


                    const btn =
                        document.getElementById(
                            'btnExportarExcel'
                        );


                    btn.disabled =
                        false;


                    btn.textContent =
                        'Exportar a Excel';

                }

            }
        );


    /* =========================================================
       INICIALIZAR
    ========================================================== */

    actualizarNumeracion();

    actualizarContador();
