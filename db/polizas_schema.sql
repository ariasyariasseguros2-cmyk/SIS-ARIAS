USE ariasyariaspe_bd_sisnet;

-- Tabla de usuarios (sin cambios del ejemplo del usuario)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NULL,
    estado TINYINT(1) DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DELIMITER $$
CREATE PROCEDURE sp_login_usuario(IN p_username VARCHAR(50))
BEGIN
    SELECT id, username, password
    FROM usuarios
    WHERE username = p_username
    LIMIT 1;
END$$
DELIMITER ;

-- Table Ramos
CREATE TABLE ramos (
    idRamo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    abreviacion VARCHAR(50),
    codigo VARCHAR(50),
    grupo VARCHAR(100),
    estado ENUM('Activo','Inactivo') DEFAULT 'Activo'
);

-- SP listar ramos -> nombre; abreviacion
DELIMITER $$

CREATE PROCEDURE sp_listar_ramos()
BEGIN
    SELECT
        nombre,
        abreviacion
    FROM ramos
    ORDER BY nombre ASC;
END $$

DELIMITER ;

-- Table asegudoras = proveedor 
CREATE TABLE aseguradoras (
    idAseguradora INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    nombre_corto VARCHAR(50),
    ruc VARCHAR(15),
    tel1 VARCHAR(20),
    central_emergencia VARCHAR(20),
    logo VARCHAR(255)  -- ruta o nombre del archivo del logo
);

-- SP Listado de asegudora 
DELIMITER $$

CREATE PROCEDURE sp_listar_aseguradoras()
BEGIN
    SELECT
        nombre_corto
    FROM aseguradoras
    ORDER BY nombre_corto ASC;
END $$

DELIMITER ;

-- Table de SUB AGENTE 
CREATE TABLE SubAgente (
    idProductor INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    abreviacion VARCHAR(100),
    email VARCHAR(120),
    telefono VARCHAR(20),
    celular VARCHAR(20)
);

-- SP lista SUB AGENTE
DELIMITER $$

CREATE PROCEDURE sp_listar_SubAgente_abreviacion()
BEGIN
    SELECT abreviacion
    FROM SubAgente
    ORDER BY abreviacion ASC;
END $$

DELIMITER ;

-- Table de ejecutivos
CREATE TABLE ejecutivos (
    idEjecutivo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    abreviacion VARCHAR(100),
    grupo VARCHAR(100)
);

-- SP Listado de ejecutivos por nombre

DELIMITER $$

CREATE PROCEDURE sp_listar_ejecutivos()
BEGIN
    SELECT 
        nombre,
        abreviacion,
        grupo
    FROM ejecutivos
    ORDER BY nombre ASC;
END $$

DELIMITER ;

-- Tabla clientes (ajustada del ejemplo del usuario)
CREATE TABLE IF NOT EXISTS clientes (
    idCliente INT AUTO_INCREMENT PRIMARY KEY,
    razon_social VARCHAR(150) NOT NULL,
    tipo_documento ENUM('DNI', 'RUC', 'CE', 'PAS', 'CEX', 'DNI/CEDULA') NOT NULL,
    numero_documento VARCHAR(20) NOT NULL UNIQUE,

    -- Contacto y ubicación
    telefono VARCHAR(20),
    celular VARCHAR(20),
    telefono_sec VARCHAR(20),
    email VARCHAR(150),
    direccion VARCHAR(200),
    departamento VARCHAR(100),
    provincia VARCHAR(100),
    distrito VARCHAR(100),

    -- Relación con subagente
    subagente VARCHAR(100),
    idProductor INT NULL,

    -- Estado y tipo
    estado VARCHAR(20) DEFAULT 'Vigente',
    tipo_persona TINYINT NULL,

    -- Fechas de sistema
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,

    -- Perfil y clasificación
    profesion VARCHAR(150) NULL,
    fecha_ingreso DATE NULL,
    fecha_nacimiento DATE NULL,
    licencia_num VARCHAR(50) NULL,
    licencia_venc DATE NULL,
    grupo_economico VARCHAR(100) NULL,
    giro_negocio VARCHAR(100) NULL,
    referencia VARCHAR(200) NULL,
    recomendado_por VARCHAR(150) NULL,

    -- Contacto de emergencia
    recibir_notificaciones TINYINT(1) DEFAULT 0,
    contacto_nombre VARCHAR(150) NULL,
    contacto_email VARCHAR(150) NULL,
    contacto_telefono VARCHAR(20) NULL,

    -- Información adicional
    referencias_interes TEXT NULL,
    notas TEXT NULL,

    -- Siniestralidad
    siniestros_reportados INT NULL,
    ultimo_siniestro DATE NULL,
    detalle_siniestros TEXT NULL,
    preferencias TEXT NULL,

    -- Foreign Key a tabla subagente
    CONSTRAINT fk_clientes_subagente FOREIGN KEY (idProductor)
        REFERENCES SubAgente(idProductor) ON DELETE SET NULL
        

);

DELIMITER $$
CREATE PROCEDURE sp_insert_cliente (
    IN p_razon_social VARCHAR(150),
    IN p_tipo_documento VARCHAR(20),
    IN p_numero_documento VARCHAR(20),
    IN p_telefono VARCHAR(20),
    IN p_celular VARCHAR(20),
    IN p_telefono_sec VARCHAR(20),
    IN p_subagente VARCHAR(100),
    IN p_idProductor INT,
    IN p_email VARCHAR(150),
    IN p_direccion VARCHAR(200),
    IN p_departamento VARCHAR(100),
    IN p_provincia VARCHAR(100),
    IN p_distrito VARCHAR(100),
    IN p_estado VARCHAR(20),
    IN p_tipo_persona TINYINT,
    IN p_profesion VARCHAR(150),
    IN p_fecha_ingreso DATE,
    IN p_fecha_nacimiento DATE,
    IN p_licencia_num VARCHAR(50),
    IN p_licencia_venc DATE,
    IN p_grupo_economico VARCHAR(100),
    IN p_giro_negocio VARCHAR(100),
    IN p_referencia VARCHAR(200),
    IN p_recomendado_por VARCHAR(150),
    IN p_recibir_notificaciones TINYINT,
    IN p_contacto_nombre VARCHAR(150),
    IN p_contacto_email VARCHAR(150),
    IN p_contacto_telefono VARCHAR(20),
    IN p_referencias_interes TEXT,
    IN p_notas TEXT,
    IN p_siniestros_reportados INT,
    IN p_ultimo_siniestro DATE,
    IN p_detalle_siniestros TEXT,
    IN p_preferencias TEXT
)
BEGIN
    INSERT INTO clientes (
        razon_social, tipo_documento, numero_documento,
        telefono, celular, telefono_sec,
        subagente, idProductor,
        email, direccion, departamento, provincia, distrito,
        estado, tipo_persona,
        profesion, fecha_ingreso, fecha_nacimiento,
        licencia_num, licencia_venc,
        grupo_economico, giro_negocio, referencia, recomendado_por,
        recibir_notificaciones, contacto_nombre, contacto_email, contacto_telefono,
        referencias_interes, notas,
        siniestros_reportados, ultimo_siniestro, detalle_siniestros, preferencias
    ) VALUES (
        p_razon_social, p_tipo_documento, p_numero_documento,
        p_telefono, p_celular, p_telefono_sec,
        p_subagente, p_idProductor,
        p_email, p_direccion, p_departamento, p_provincia, p_distrito,
        p_estado, p_tipo_persona,
        p_profesion, p_fecha_ingreso, p_fecha_nacimiento,
        p_licencia_num, p_licencia_venc,
        p_grupo_economico, p_giro_negocio, p_referencia, p_recomendado_por,
        p_recibir_notificaciones, p_contacto_nombre, p_contacto_email, p_contacto_telefono,
        p_referencias_interes, p_notas,
        p_siniestros_reportados, p_ultimo_siniestro, p_detalle_siniestros, p_preferencias
    );
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_list_clientes ()
BEGIN
    SELECT
        idCliente,
        fecha_registro,
        razon_social,
        tipo_documento,
        numero_documento,
        telefono,
        subagente,
        email,
        direccion,
        estado,
        tipo_persona
    FROM clientes
    WHERE estado = 'Vigente'
    ORDER BY fecha_registro DESC;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_buscar_cliente (IN p_texto VARCHAR(150))
BEGIN
    SELECT *
    FROM clientes
    WHERE estado = 'Vigente'
      AND (
            razon_social LIKE CONCAT('%', p_texto, '%')
         OR numero_documento LIKE CONCAT('%', p_texto, '%')
         OR email LIKE CONCAT('%', p_texto, '%')
         OR telefono LIKE CONCAT('%', p_texto, '%')
      )
    ORDER BY fecha_registro DESC;
END$$
DELIMITER ;

-- Tabla polizas: quitar 'producto' y 'motivo', mantener 'cia' y 'ramos_producto'
CREATE TABLE IF NOT EXISTS polizas (
    idPoliza INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,

    asegurado VARCHAR(150) NULL,
    cia VARCHAR(100) NULL,
    ramo VARCHAR(120) NULL,
    -- producto VARCHAR(120) NULL,        -- ELIMINADO
    poliza VARCHAR(50) NULL,
    recibo VARCHAR(50) NULL,
    contrato_nro VARCHAR(50) NULL,
    nro VARCHAR(50) NULL,

    moneda VARCHAR(20) NULL,
    fecha_emision DATE NULL,
    vig_desde DATE NULL,
    vig_hasta DATE NULL,
    ultimo_dia_pago DATE NULL,
    fecha_vencimiento DATE NULL,      -- NUEVO
    forma_pago VARCHAR(30) NULL,

    sub_agente VARCHAR(100) NULL,
    ejecutivo VARCHAR(100) NULL,
    tipo_doc VARCHAR(10) NULL,
    asegurada VARCHAR(150) NULL,
    motivo VARCHAR(200) NULL,
    prima_comercial DECIMAL(15,2) NULL,
    prima_neta DECIMAL(15,2) NULL,
    prima_comercial_igv DECIMAL(15,2) NULL,
    prima_total DECIMAL(15,2) NULL,

    porc_compania DECIMAL(5,2) NULL,
    imp_compania DECIMAL(15,2) NULL,
    porc_subagente DECIMAL(5,2) NULL,
    imp_subagente DECIMAL(15,2) NULL,

    -- motivo VARCHAR(200) NULL,          -- ELIMINADO
    ramos_producto VARCHAR(120) NULL,

    estado VARCHAR(20) DEFAULT 'PENDIENTE',
    usuario_registro VARCHAR(50) NULL,
    usuario_edicion VARCHAR(50) NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (cliente_id) REFERENCES clientes(idCliente)
);

-- Tabla para archivos de pólizas (separada)
CREATE TABLE IF NOT EXISTS poliza_archivos (
    idArchivo INT AUTO_INCREMENT PRIMARY KEY,
    poliza_id INT NOT NULL,
    numero_poliza VARCHAR(50),
    ruta_archivo VARCHAR(255) NOT NULL,
    nombre_original VARCHAR(255),
    origen VARCHAR(50) DEFAULT 'CARGA_MASIVA',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (poliza_id) REFERENCES polizas(idPoliza) ON DELETE CASCADE
);

DELIMITER $$
CREATE PROCEDURE sp_get_cliente_por_numero(IN p_numero_documento VARCHAR(20))
BEGIN
    SELECT
        razon_social,
        tipo_documento,
        numero_documento,
        telefono
    FROM clientes
    WHERE numero_documento = p_numero_documento
    LIMIT 1;
END$$
DELIMITER ;

-- Insertar póliza enlazando por numero_documento del cliente (actualizado con todos los campos)
DELIMITER $$
CREATE PROCEDURE sp_insert_poliza_por_numero (
    IN p_numero_documento VARCHAR(20),
    IN p_tipo_doc VARCHAR(10),
    IN p_asegurado VARCHAR(150),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    -- IN p_producto VARCHAR(120),        -- ELIMINADO

    IN p_poliza VARCHAR(50),
    IN p_recibo VARCHAR(50),
    IN p_contrato_nro VARCHAR(50),
    IN p_nro VARCHAR(50),

    IN p_moneda VARCHAR(20),
    IN p_fecha_emision DATE,
    IN p_vig_desde DATE,
    IN p_vig_hasta DATE,
    IN p_ultimo_dia_pago DATE,
    IN p_fecha_vencimiento DATE,  -- NUEVO
    IN p_forma_pago VARCHAR(30),

    IN p_sub_agente VARCHAR(100),
    IN p_ejecutivo VARCHAR(100),

    IN p_asegurada VARCHAR(150),
    IN p_motivo VARCHAR(200),
    IN p_prima_comercial DECIMAL(15,2),
    IN p_prima_neta DECIMAL(15,2),
    IN p_prima_comercial_igv DECIMAL(15,2),
    IN p_prima_total DECIMAL(15,2),

    IN p_porc_compania DECIMAL(5,2),
    IN p_imp_compania DECIMAL(15,2),
    IN p_porc_subagente DECIMAL(5,2),
    IN p_imp_subagente DECIMAL(15,2),

    -- IN p_motivo VARCHAR(200),          -- ELIMINADO
    IN p_ramos_producto VARCHAR(120),
    IN p_estado VARCHAR(20),
    IN p_pdf_path VARCHAR(255),
    IN p_usuario_registro VARCHAR(50)
)
BEGIN
    DECLARE v_cliente_id INT;
    DECLARE v_exists INT DEFAULT 0;
    DECLARE v_msg VARCHAR(255);
    DECLARE v_key VARCHAR(50); -- clave para duplicados: contrato_nro o recibo
    DECLARE v_poliza_id INT;

    SELECT idCliente INTO v_cliente_id
    FROM clientes
    WHERE numero_documento = p_numero_documento
    LIMIT 1;

    IF v_cliente_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cliente no existe';
    END IF;

    -- Normalizar clave de duplicado: primero contrato_nro, si no, recibo
    SET v_key = NULLIF(TRIM(IFNULL(p_contrato_nro, '')), '');
    IF v_key IS NULL THEN
        SET v_key = NULLIF(TRIM(IFNULL(p_recibo, '')), '');
    END IF;

    -- Validación de duplicados: poliza + (contrato_nro|recibo), acotado por cliente
    IF COALESCE(p_poliza, '') <> '' AND COALESCE(v_key, '') <> '' THEN
        SELECT COUNT(*) INTO v_exists
        FROM polizas
        WHERE cliente_id = v_cliente_id
          AND poliza = p_poliza
          AND (
               contrato_nro = v_key
            OR recibo = v_key
          );

        IF v_exists > 0 THEN
            SET v_msg = CONCAT('Póliza ya existe con mismo número y contrato: ', p_poliza, ' / ', p_contrato_nro);
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    END IF;

    INSERT INTO polizas (
        cliente_id, asegurado, cia, ramo,
        poliza, recibo, contrato_nro, nro,
        moneda, fecha_emision, vig_desde, vig_hasta, ultimo_dia_pago, fecha_vencimiento, forma_pago,
        sub_agente, ejecutivo, tipo_doc,
        asegurada, motivo, prima_comercial, prima_neta, prima_comercial_igv, prima_total,
        porc_compania, imp_compania, porc_subagente, imp_subagente,
        ramos_producto, estado, usuario_registro
    ) VALUES (
        v_cliente_id, p_asegurado, p_cia, p_ramo,
        p_poliza, p_recibo, p_contrato_nro, p_nro,
        p_moneda, p_fecha_emision, p_vig_desde, p_vig_hasta, p_ultimo_dia_pago, p_fecha_vencimiento, p_forma_pago,
        p_sub_agente, p_ejecutivo, p_tipo_doc,
        p_asegurada, p_motivo, p_prima_comercial, p_prima_neta, p_prima_comercial_igv, p_prima_total,
        p_porc_compania, p_imp_compania, p_porc_subagente, p_imp_subagente,
        p_ramos_producto, p_estado, p_usuario_registro
    );

    SET v_poliza_id = LAST_INSERT_ID();

    IF p_pdf_path IS NOT NULL AND p_pdf_path <> '' THEN
        INSERT INTO poliza_archivos (poliza_id, numero_poliza, ruta_archivo, nombre_original)
        VALUES (v_poliza_id, p_poliza, p_pdf_path, SUBSTRING_INDEX(p_pdf_path, '/', -1));
    END IF;

    -- Insertar cuota inicial automática
    INSERT INTO cuotas (
        poliza, cupon, fecha_vencimiento, moneda, importe, 
        fecha_pago, factura, observacion
    ) VALUES (
        p_poliza, 
        p_recibo, 
        p_fecha_vencimiento, 
        p_moneda, 
        p_prima_comercial_igv, 
        NULL, 
        NULL, 
        NULL
    );
END$$
DELIMITER ;
-- NUEVO: listado global de pólizas (opcional, si prefieres usar SP)
DELIMITER $$
CREATE PROCEDURE sp_list_polizas_all()
BEGIN
    SELECT 
        p.idPoliza,
        c.razon_social AS contratante,
        p.asegurado,
        p.cia,
        p.ramo,
        p.ramos_producto AS producto,
        p.poliza,
        p.nro,
        p.moneda,
        DATE_FORMAT(p.fecha_emision, '%d/%m/%Y') AS fecha_emision,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
        p.sub_agente,
        p.asegurada,
        p.usuario_registro,
        p.usuario_edicion,
    (SELECT ruta_archivo FROM poliza_archivos WHERE poliza_id = p.idPoliza ORDER BY idArchivo DESC LIMIT 1) AS pdf_path
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    ORDER BY p.creado_en DESC;
END$$
DELIMITER ;

-- Listado de pólizas por cliente (mantiene columnas usadas en la vista)
DELIMITER $$
CREATE PROCEDURE sp_list_polizas_por_numero(IN p_numero_documento VARCHAR(20))
BEGIN
    SELECT 
        p.idPoliza,
        c.razon_social AS contratante,
        p.asegurado,
        p.cia,
        p.ramo,
        p.ramos_producto AS producto,
        p.poliza,
        p.nro,
        p.moneda,
        DATE_FORMAT(p.fecha_emision, '%d/%m/%Y') AS fecha_emision,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
        p.sub_agente,
        p.asegurada,
        p.usuario_registro,
        p.usuario_edicion,
    (SELECT ruta_archivo FROM poliza_archivos WHERE poliza_id = p.idPoliza ORDER BY idArchivo DESC LIMIT 1) AS pdf_path
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE c.numero_documento = p_numero_documento
    ORDER BY p.creado_en DESC;
END$$
DELIMITER ;

-- Nuevo: obtener cliente por ID
DELIMITER $$
CREATE PROCEDURE sp_get_cliente_por_id(IN p_id INT)
BEGIN
    SELECT
        razon_social,
        tipo_documento,
        numero_documento,
        telefono
    FROM clientes
    WHERE idCliente = p_id
    LIMIT 1;
END$$
DELIMITER ;

-- Nuevo: listar pólizas por cliente_id
DELIMITER $$
CREATE PROCEDURE sp_list_polizas_por_cliente_id(IN p_cliente_id INT)
BEGIN
    SELECT 
        p.idPoliza,
        c.razon_social AS contratante,
        p.asegurado,
        p.cia,
        p.ramo,
        p.ramos_producto AS producto,
        p.poliza,
        p.nro,
        p.moneda,
        DATE_FORMAT(p.fecha_emision, '%d/%m/%Y') AS fecha_emision,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
        p.sub_agente,
        p.asegurada,
        p.usuario_registro,
        p.usuario_edicion,
    (SELECT ruta_archivo FROM poliza_archivos WHERE poliza_id = p.idPoliza ORDER BY idArchivo DESC LIMIT 1) AS pdf_path
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE p.cliente_id = p_cliente_id
    ORDER BY p.creado_en DESC;
END$$
DELIMITER ;

DELIMITER $$
-- sp_list_primas_por_poliza
CREATE PROCEDURE sp_list_primas_por_poliza(IN p_poliza VARCHAR(50))
BEGIN
    SELECT
        p.idPoliza,  -- Added ID
        p.recibo,
        p.poliza,
        c.razon_social AS contratante,
        p.cia AS compania,
        p.ramo,
        -- aquí antes estaba: 'Emision' AS tipo,
        p.tipo_doc AS tipo,
        p.prima_comercial,
        p.prima_neta,
        p.prima_comercial_igv,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
        p.nro AS nro_operacion,
        p.motivo AS motivo
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE p.poliza = p_poliza
    ORDER BY p.creado_en DESC;
END$$
DELIMITER ;

DELIMITER $$
-- sp_list_primas_por_cliente_id
CREATE PROCEDURE sp_list_primas_por_cliente_id(IN p_cliente_id INT)
BEGIN
    SELECT
        p.idPoliza,  -- Added ID
        p.recibo,
        p.ejecutivo AS Ejecutivo,          -- corregido: antes p.ejecutivos
        p.poliza,
        c.razon_social AS contratante,
        p.asegurado AS Asegurado,
        p.cia AS compania,
        p.ramo,
        p.tipo_doc AS tipo,
        p.prima_comercial,
        p.prima_neta,
        p.prima_comercial_igv,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
        p.nro AS nro_operacion,
        p.motivo AS motivo
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE p.cliente_id = p_cliente_id
    ORDER BY p.creado_en DESC;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_get_poliza_detalle_por_numero(IN p_poliza VARCHAR(50))
BEGIN
    SELECT
        p.asegurado AS asegurado,          
        p.ejecutivo AS Ejecutivo,         
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE p.poliza = p_poliza
    LIMIT 1;
END$$
DELIMITER ;

-- Tabla cuotas (mínima)
CREATE TABLE IF NOT EXISTS cuotas (
    idCuota INT AUTO_INCREMENT PRIMARY KEY,
    poliza VARCHAR(50) NOT NULL,
    cupon VARCHAR(50) NULL,
    fecha_vencimiento DATE NULL,
    moneda VARCHAR(10) NULL,
    importe DECIMAL(15,2) NULL,
    fecha_pago DATE NULL,
    factura VARCHAR(50) NULL,
    observacion VARCHAR(255) NULL,
    usuario_registro VARCHAR(50) NULL,
    usuario_edicion VARCHAR(50) NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DELIMITER $$
CREATE PROCEDURE sp_list_cuotas_por_poliza(IN p_poliza VARCHAR(50))
BEGIN
    SELECT
        idCuota,
        cupon,
        DATE_FORMAT(fecha_vencimiento, '%d-%m-%Y') AS fecha_vencimiento,
        moneda,
        FORMAT(importe, 2) AS importe,
        DATE_FORMAT(fecha_pago, '%d-%m-%Y') AS fecha_pago,
        factura,
        observacion
    FROM cuotas
    WHERE poliza = p_poliza
    ORDER BY fecha_vencimiento ASC, idCuota ASC;
END$$
DELIMITER ;

-- NEW PROCEDURES FOR EDITING

DELIMITER $$
CREATE PROCEDURE sp_get_poliza_by_id(IN p_id INT)
BEGIN
    SELECT 
        p.*,
        c.razon_social AS cliente_razon_social,
        c.tipo_documento AS cliente_tipo_documento,
        c.numero_documento AS cliente_numero_documento,
        c.telefono AS cliente_telefono
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE p.idPoliza = p_id;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_update_poliza(
    IN p_idPoliza INT,
    IN p_asegurado VARCHAR(150),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_poliza VARCHAR(50),
    IN p_moneda VARCHAR(20),
    IN p_fecha_emision DATE,
    IN p_vig_desde DATE,
    IN p_vig_hasta DATE,
    IN p_sub_agente VARCHAR(100),
    IN p_ejecutivo VARCHAR(100),
    IN p_asegurada VARCHAR(150),
    IN p_motivo VARCHAR(200),
    IN p_prima_comercial DECIMAL(15,2),
    IN p_prima_neta DECIMAL(15,2),
    IN p_prima_comercial_igv DECIMAL(15,2),
    IN p_prima_total DECIMAL(15,2),
    IN p_porc_compania DECIMAL(5,2),
    IN p_imp_compania DECIMAL(15,2),
    IN p_porc_subagente DECIMAL(5,2),
    IN p_imp_subagente DECIMAL(15,2),
    IN p_ramos_producto VARCHAR(120),
    IN p_tipo_doc VARCHAR(10),
    IN p_estado VARCHAR(20),
    IN p_nro VARCHAR(50), -- Nuevo
    IN p_forma_pago VARCHAR(30), -- Nuevo
    IN p_recibo VARCHAR(50), -- Nuevo
    IN p_pdf_path VARCHAR(255), -- Nuevo
    IN p_usuario_edicion VARCHAR(50)
)
BEGIN
    UPDATE polizas SET
        usuario_edicion = p_usuario_edicion,
        asegurado = p_asegurado,
        cia = p_cia,
        ramo = p_ramo,
        poliza = p_poliza,
        moneda = p_moneda,
        fecha_emision = p_fecha_emision,
        vig_desde = p_vig_desde,
        vig_hasta = p_vig_hasta,
        sub_agente = p_sub_agente,
        ejecutivo = p_ejecutivo,
        asegurada = p_asegurada,
        motivo = p_motivo,
        prima_comercial = p_prima_comercial,
        prima_neta = p_prima_neta,
        prima_comercial_igv = p_prima_comercial_igv,
        prima_total = p_prima_total,
        porc_compania = p_porc_compania,
        imp_compania = p_imp_compania,
        porc_subagente = p_porc_subagente,
        imp_subagente = p_imp_subagente,
        ramos_producto = p_ramos_producto,
        tipo_doc = p_tipo_doc,
        estado = p_estado,
        nro = p_nro,
        forma_pago = p_forma_pago,
        recibo = p_recibo
    WHERE idPoliza = p_idPoliza;

    IF p_pdf_path IS NOT NULL AND p_pdf_path <> '' THEN
        INSERT INTO poliza_archivos (poliza_id, numero_poliza, ruta_archivo, nombre_original, origen)
        VALUES (p_idPoliza, p_poliza, p_pdf_path, SUBSTRING_INDEX(p_pdf_path, '/', -1), 'EDICION');
    END IF;
END$$
DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_reporte_archivos_poliza(IN p_busqueda VARCHAR(100))
BEGIN
    SELECT 
        pa.idArchivo,
        pa.ruta_archivo,
        pa.nombre_original,
        p.idPoliza,
        p.poliza,
        COALESCE(NULLIF(p.contrato_nro, ''), p.recibo) AS aviso_cob,
        DATE_FORMAT(p.vig_desde, '%Y-%m-%d') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%Y-%m-%d') AS vig_hasta,
        p.tipo_doc,
        c.razon_social AS contratante,
        DATE_FORMAT(pa.creado_en, '%Y-%m-%d %H:%i') AS fecha_subida
    FROM poliza_archivos pa
    INNER JOIN polizas p ON pa.poliza_id = p.idPoliza
    INNER JOIN clientes c ON p.cliente_id = c.idCliente
    WHERE p_busqueda IS NULL OR p_busqueda = '' 
       OR p.poliza LIKE CONCAT('%', p_busqueda, '%')
       OR c.razon_social LIKE CONCAT('%', p_busqueda, '%')
       OR pa.nombre_original LIKE CONCAT('%', p_busqueda, '%')
       OR p.contrato_nro LIKE CONCAT('%', p_busqueda, '%')
       OR p.recibo LIKE CONCAT('%', p_busqueda, '%')
    ORDER BY pa.creado_en DESC
    LIMIT 100;
END$$
DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_reporte_vencimientos(
    IN p_fecha_inicio DATE,
    IN p_fecha_fin DATE
)
BEGIN
    SELECT 
        p.cia AS compania,
        p.ramo,
        p.ramos_producto AS producto,
        c.tipo_documento,
        c.numero_documento,
        p.poliza,
        p.recibo AS aviso_cobranza,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
        (SELECT DATE_FORMAT(MAX(q.fecha_pago), '%d/%m/%Y') FROM cuotas q WHERE q.poliza = p.poliza) AS fecha_pago,
        p.moneda,
        p.prima_comercial_igv AS prima_neta,
        p.prima_comercial_igv AS prima_total,
        p.estado
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE p.vig_hasta BETWEEN p_fecha_inicio AND p_fecha_fin
    ORDER BY p.vig_hasta ASC;
END$$
DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_get_idProductor_por_abreviacion(IN p_abreviacion VARCHAR(100))
BEGIN
SELECT idProductor
FROM SubAgente
WHERE abreviacion = p_abreviacion
    LIMIT 1;
END$$
DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_update_cliente (
    IN p_idCliente INT,
    IN p_razon_social VARCHAR(150),
    IN p_tipo_documento VARCHAR(20),
    IN p_numero_documento VARCHAR(20),
    IN p_telefono VARCHAR(20),
    IN p_celular VARCHAR(20),
    IN p_telefono_sec VARCHAR(20),
    IN p_subagente VARCHAR(100),
    IN p_idProductor INT,
    IN p_email VARCHAR(150),
    IN p_direccion VARCHAR(200),
    IN p_departamento VARCHAR(100),
    IN p_provincia VARCHAR(100),
    IN p_distrito VARCHAR(100),
    IN p_estado VARCHAR(20),
    IN p_tipo_persona TINYINT,
    IN p_profesion VARCHAR(150),
    IN p_fecha_ingreso DATE,
    IN p_fecha_nacimiento DATE,
    IN p_licencia_num VARCHAR(50),
    IN p_licencia_venc DATE,
    IN p_grupo_economico VARCHAR(100),
    IN p_giro_negocio VARCHAR(100),
    IN p_referencia VARCHAR(200),
    IN p_recomendado_por VARCHAR(150),
    IN p_recibir_notificaciones TINYINT,
    IN p_contacto_nombre VARCHAR(150),
    IN p_contacto_email VARCHAR(150),
    IN p_contacto_telefono VARCHAR(20),
    IN p_referencias_interes TEXT,
    IN p_notas TEXT,
    IN p_siniestros_reportados INT,
    IN p_ultimo_siniestro DATE,
    IN p_detalle_siniestros TEXT,
    IN p_preferencias TEXT
)
BEGIN
UPDATE clientes
SET razon_social = p_razon_social,
    tipo_documento = p_tipo_documento,
    numero_documento = p_numero_documento,
    telefono = p_telefono,
    celular = p_celular,
    telefono_sec = p_telefono_sec,
    subagente = p_subagente,
    idProductor = p_idProductor,
    email = p_email,
    direccion = p_direccion,
    departamento = p_departamento,
    provincia = p_provincia,
    distrito = p_distrito,
    estado = p_estado,
    tipo_persona = p_tipo_persona,
    profesion = p_profesion,
    fecha_ingreso = p_fecha_ingreso,
    fecha_nacimiento = p_fecha_nacimiento,
    licencia_num = p_licencia_num,
    licencia_venc = p_licencia_venc,
    grupo_economico = p_grupo_economico,
    giro_negocio = p_giro_negocio,
    referencia = p_referencia,
    recomendado_por = p_recomendado_por,
    recibir_notificaciones = p_recibir_notificaciones,
    contacto_nombre = p_contacto_nombre,
    contacto_email = p_contacto_email,
    contacto_telefono = p_contacto_telefono,
    referencias_interes = p_referencias_interes,
    notas = p_notas,
    siniestros_reportados = p_siniestros_reportados,
    ultimo_siniestro = p_ultimo_siniestro,
    detalle_siniestros = p_detalle_siniestros,
    preferencias = p_preferencias
WHERE idCliente = p_idCliente;
END$$

DELIMITER ;