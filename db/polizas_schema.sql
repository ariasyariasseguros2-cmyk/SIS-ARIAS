CREATE DATABASE IF NOT EXISTS ariasyariaspe_bd_sisnet CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ariasyariaspe_bd_sisnet;

-- Tabla de usuarios (sin cambios del ejemplo del usuario)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    id_rol INT NULL,
    nombre VARCHAR(100) NULL,
    estado TINYINT(1) DEFAULT 1,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DELIMITER $$
DROP PROCEDURE IF EXISTS sp_login_usuario $$
CREATE PROCEDURE sp_login_usuario(IN p_username VARCHAR(50))
BEGIN
    SELECT 
        u.id,
        u.username,
        u.password,
        u.id_rol,
        r.nombre AS rol_nombre
    FROM usuarios u
    LEFT JOIN roles r ON r.idRol = u.id_rol
    WHERE u.username = p_username
    LIMIT 1;
END $$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_listar_usuarios()
BEGIN
    SELECT username
    FROM usuarios
    WHERE estado = 1
    ORDER BY username ASC;
END$$
DELIMITER ;

-- Tabla de Ajustadores
CREATE TABLE IF NOT EXISTS ajustadores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    abreviacion VARCHAR(150),
    codigo VARCHAR(20) NOT NULL UNIQUE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DELIMITER $$

CREATE PROCEDURE sp_listar_ajustadores()
BEGIN
    SELECT
        nombre,
        abreviacion,
        codigo
    FROM ajustadores
    ORDER BY nombre ASC;
END $$
DELIMITER ;



DROP PROCEDURE IF EXISTS sp_insertar_ajustador;
DELIMITER $$
CREATE PROCEDURE sp_insertar_ajustador(
    IN p_nombre VARCHAR(255),
    IN p_abreviacion VARCHAR(150),
    IN p_codigo VARCHAR(20),
    OUT p_new_id INT
)
BEGIN
    INSERT INTO ajustadores (nombre, abreviacion, codigo)
    VALUES (p_nombre, p_abreviacion, p_codigo)
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

    SET p_new_id = LAST_INSERT_ID();
END $$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_eliminar_ajustador(
    IN p_id INT
)
BEGIN
DELETE FROM ajustadores
WHERE id = p_id;
END $$

DELIMITER ;

-- Table Ramos
CREATE TABLE ramos (
    idRamo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    abreviacion VARCHAR(50),
    codigo VARCHAR(50),
    grupo VARCHAR(100),
    estado ENUM('Activo','Inactivo') DEFAULT 'Activo',
    UNIQUE KEY uq_ramos_nombre (nombre)
);

-- SP listar ramos -> nombre; abreviacion
DELIMITER $$

CREATE PROCEDURE sp_listar_ramos()
BEGIN
    SELECT
        nombre,
        abreviacion
    FROM ramos
    ORDER BY idRamo ASC;
END $$

DELIMITER ;

-- PROCEDIMIENTOS: RAMOS (insertar / eliminar)
DROP PROCEDURE IF EXISTS sp_insertar_ramo;
DELIMITER $$
CREATE PROCEDURE sp_insertar_ramo(
    IN p_nombre VARCHAR(150),
    IN p_abreviacion VARCHAR(50),
    IN p_codigo VARCHAR(50),
    IN p_grupo VARCHAR(100),
    OUT p_new_id INT
)
BEGIN
    IF TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre del ramo no puede estar vacío';
    END IF;

    INSERT INTO ramos (nombre, abreviacion, codigo, grupo)
    VALUES (TRIM(p_nombre), NULLIF(TRIM(p_abreviacion), ''), NULLIF(TRIM(p_codigo), ''), NULLIF(TRIM(p_grupo), ''))
    ON DUPLICATE KEY UPDATE idRamo = LAST_INSERT_ID(idRamo);

    SET p_new_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_eliminar_ramo;
DELIMITER $$
CREATE PROCEDURE sp_eliminar_ramo(
    IN p_id INT
)
BEGIN
    DELETE FROM ramos WHERE idRamo = p_id;
END$$
DELIMITER ;

CREATE TABLE IF NOT EXISTS productos (
    id_producto BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    idRamo      INT NOT NULL,
    nombre      VARCHAR(150) NOT NULL,
    CONSTRAINT fk_productos_ramos
    FOREIGN KEY (idRamo) REFERENCES ramos(idRamo)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
);

CREATE INDEX idx_productos_idRamo ON productos(idRamo);
CREATE UNIQUE INDEX uk_productos_ramo_nombre ON productos(idRamo, nombre);

-- PROCEDIMIENTOS: PRODUCTOS
DROP PROCEDURE IF EXISTS sp_listar_productos;
DELIMITER $$
CREATE PROCEDURE sp_listar_productos()
BEGIN
    SELECT id_producto AS id, idRamo AS ramo_id, nombre
    FROM productos
    ORDER BY nombre ASC;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_insertar_producto;
DELIMITER $$
CREATE PROCEDURE sp_insertar_producto(
    IN p_idRamo INT,
    IN p_nombre VARCHAR(150),
    OUT p_new_id BIGINT UNSIGNED
)
BEGIN
    IF p_idRamo IS NULL OR p_idRamo = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El idRamo es requerido';
    END IF;
    IF TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre del producto no puede estar vacío';
    END IF;

    INSERT INTO productos (idRamo, nombre)
    VALUES (p_idRamo, TRIM(p_nombre))
    ON DUPLICATE KEY UPDATE id_producto = LAST_INSERT_ID(id_producto);

    SET p_new_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_eliminar_producto;
DELIMITER $$
CREATE PROCEDURE sp_eliminar_producto(
    IN p_id BIGINT UNSIGNED
)
BEGIN
    DELETE FROM productos WHERE id_producto = p_id;
END$$
DELIMITER ;


-- Table asegudoras = proveedor
CREATE TABLE companias (
    id_compania INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    nombre_corto VARCHAR(50),
    ruc VARCHAR(15),
    tel1 VARCHAR(20),
    central_emergencia VARCHAR(20),
    logo VARCHAR(255)
);


-- SP Listado de asegudora
DELIMITER $$

CREATE PROCEDURE sp_listar_companias()
BEGIN
    SELECT
        nombre_corto
    FROM companias
    ORDER BY nombre_corto ASC;
END $$

DELIMITER ;

CREATE TABLE comisiones_temp (
    id INT AUTO_INCREMENT PRIMARY KEY,

    ramo_nombre        VARCHAR(100),
    ramo_abreviacion   VARCHAR(50),
    ramo_codigo        VARCHAR(50),
    ramo_grupo         VARCHAR(100),
    ramo_estado        VARCHAR(20),

    producto           VARCHAR(150),
    producto_abrev     VARCHAR(50),
    producto_codigo    VARCHAR(50),

    pos_eps       DECIMAL(5,2),
    pos_vsr       DECIMAL(5,2),
    pos_sr        DECIMAL(5,2),
    pacifico      DECIMAL(5,2),
    sanitas       DECIMAL(5,2),
    protecta      DECIMAL(5,2),
    mapfre        DECIMAL(5,2),
    crecer        DECIMAL(5,2),
    ohio_natural  DECIMAL(5,2),

    factor        DECIMAL(10,4)
);

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

-- Tabla Endosatarios
CREATE TABLE IF NOT EXISTS endosatarios (
    idEndosatario INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    estado ENUM('Activo','Inactivo') DEFAULT 'Activo'
);

-- SP listar endosatarios
DELIMITER $$
CREATE PROCEDURE sp_listar_endosatarios()
BEGIN
    SELECT nombre
    FROM endosatarios
    WHERE estado = 'Activo'
    ORDER BY nombre ASC;
END$$
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

    -- Auditoría: registro de usuarios
    usuario_creacion VARCHAR(50) NULL COMMENT 'Usuario que registró el cliente',
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Fecha de creación del registro',
    usuario_modificacion VARCHAR(50) NULL COMMENT 'Último usuario que modificó el cliente',
    fecha_modificacion DATETIME NULL ON UPDATE CURRENT_TIMESTAMP COMMENT 'Última fecha de modificación',

    -- Borrado lógico
    activo BOOLEAN NOT NULL DEFAULT TRUE COMMENT '1=activo, 0=eliminado lógicamente',

    --
    -- Foreign Key a tabla subagente
    CONSTRAINT fk_clientes_subagente FOREIGN KEY (idProductor)
        REFERENCES SubAgente(idProductor) ON DELETE SET NULL


);

    -- ACTUALIZA EL ROW ACTIVE A 1 PARA REGISTROS EXISTENTES (NO FUNCIONAL TEMPORALMENTE)
    UPDATE clientes SET activo = 1 WHERE activo IS NULL AND idCliente IS NOT NULL;

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
    IN p_usuario_creacion VARCHAR(50)
)
BEGIN
    DECLARE v_cliente_id INT;

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
        usuario_creacion
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
        p_usuario_creacion
    );

    SET v_cliente_id = LAST_INSERT_ID();
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
    WHERE activo = 1
    ORDER BY fecha_registro DESC;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_buscar_cliente (IN p_texto VARCHAR(150))
BEGIN
    SELECT *
    FROM clientes
    WHERE activo = 1
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
    tipo_vigencia VARCHAR(50) NULL,   -- NUEVO
    endosatario VARCHAR(150) NULL,    -- NUEVO
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

    datos_vehiculo JSON NULL,         -- NUEVO: Para almacenar datos del vehículo en SOAT
    codigo_agente VARCHAR(50) NULL,   -- NUEVO: Código de agente/vendedor

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
    ramo VARCHAR(120),
    producto VARCHAR(120),
    usuario VARCHAR(50),
    compania VARCHAR(100),
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (poliza_id) REFERENCES polizas(idPoliza) ON DELETE CASCADE
);



DELIMITER $$
CREATE PROCEDURE sp_reporte_archivos_detalle(
    IN p_busqueda VARCHAR(100),
    IN p_identificador VARCHAR(50),
    IN p_tipo_origen VARCHAR(20)
)
BEGIN
    -- Archivos de Pólizas
    SELECT
        pa.idArchivo,
        pa.ruta_archivo,
        pa.nombre_original,
        p.poliza AS identificador,
        'POLIZA' AS tipo_origen
    FROM poliza_archivos pa
    INNER JOIN polizas p ON pa.poliza_id = p.idPoliza
    INNER JOIN clientes c ON p.cliente_id = c.idCliente
    WHERE (p_busqueda IS NULL OR p_busqueda = ''
           OR p.poliza LIKE CONCAT('%', p_busqueda, '%')
           OR c.razon_social LIKE CONCAT('%', p_busqueda, '%')
           OR pa.nombre_original LIKE CONCAT('%', p_busqueda, '%')
           OR p.contrato_nro LIKE CONCAT('%', p_busqueda, '%')
           OR p.recibo LIKE CONCAT('%', p_busqueda, '%'))
      AND (p_identificador IS NULL OR p_identificador = '' OR p.poliza = p_identificador)
      AND (p_tipo_origen IS NULL OR p_tipo_origen = '' OR 'POLIZA' = p_tipo_origen);
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_reporte_archivos_resumen(IN p_busqueda VARCHAR(100))
BEGIN
    SELECT
        identificador,
        tipo_origen,
        contratante,
        COUNT(*) AS cantidad_archivos,
        MAX(fecha_subida) AS ultima_fecha,
        ramo,
        producto,
        usuario,
        compania
    FROM (
        -- Archivos de Pólizas
        SELECT
            p.poliza AS identificador,
            'POLIZA' AS tipo_origen,
            c.razon_social AS contratante,
            pa.creado_en AS fecha_subida,
            p.ramo,
            p.ramos_producto AS producto,
            p.usuario_registro AS usuario,
            p.cia AS compania
        FROM poliza_archivos pa
        INNER JOIN polizas p ON pa.poliza_id = p.idPoliza
        INNER JOIN clientes c ON p.cliente_id = c.idCliente
        WHERE p_busqueda IS NULL OR p_busqueda = ''
           OR p.poliza LIKE CONCAT('%', p_busqueda, '%')
           OR c.razon_social LIKE CONCAT('%', p_busqueda, '%')
           OR pa.nombre_original LIKE CONCAT('%', p_busqueda, '%')
           OR p.contrato_nro LIKE CONCAT('%', p_busqueda, '%')
           OR p.recibo LIKE CONCAT('%', p_busqueda, '%')
    ) AS combined
    GROUP BY identificador, tipo_origen, contratante, ramo, producto, usuario, compania
    ORDER BY ultima_fecha DESC
    LIMIT 100;
END$$
DELIMITER ;




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
      AND activo = 1
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
    IN p_tipo_vigencia VARCHAR(50),   -- NUEVO
    IN p_endosatario VARCHAR(150),    -- NUEVO
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
        moneda, fecha_emision, vig_desde, vig_hasta, ultimo_dia_pago, fecha_vencimiento, tipo_vigencia, endosatario, forma_pago,
        sub_agente, ejecutivo, tipo_doc,
        asegurada, motivo, prima_comercial, prima_neta, prima_comercial_igv, prima_total,
        porc_compania, imp_compania, porc_subagente, imp_subagente,
        ramos_producto, estado, usuario_registro
    ) VALUES (
        v_cliente_id, p_asegurado, p_cia, p_ramo,
        p_poliza, p_recibo, p_contrato_nro, p_nro,
        p_moneda, p_fecha_emision, p_vig_desde, p_vig_hasta, p_ultimo_dia_pago, p_fecha_vencimiento, p_tipo_vigencia, p_endosatario, p_forma_pago,
        p_sub_agente, p_ejecutivo, p_tipo_doc,
        p_asegurada, p_motivo, p_prima_comercial, p_prima_neta, p_prima_comercial_igv, p_prima_total,
        p_porc_compania, p_imp_compania, p_porc_subagente, p_imp_subagente,
        p_ramos_producto, p_estado, p_usuario_registro
    );

    SET v_poliza_id = LAST_INSERT_ID();

    IF p_pdf_path IS NOT NULL AND p_pdf_path <> '' THEN
        INSERT INTO poliza_archivos (poliza_id, numero_poliza, ruta_archivo, nombre_original, ramo, producto, usuario, compania)
        VALUES (v_poliza_id, p_poliza, p_pdf_path, SUBSTRING_INDEX(p_pdf_path, '/', -1), p_ramo, p_ramos_producto, p_usuario_registro, p_cia);
    END IF;


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
    idCliente,
    razon_social,
    tipo_documento,
    numero_documento,
    telefono,
    celular,
    telefono_sec,
    email,
    direccion,
    departamento,
    provincia,
    distrito,
    subagente,
    idProductor,
    estado,
    tipo_persona,
    fecha_registro,
    fecha_actualizacion,
    profesion,
    fecha_ingreso,
    fecha_nacimiento,
    licencia_num,
    licencia_venc,
    grupo_economico,
    giro_negocio,
    referencia,
    recomendado_por,
    recibir_notificaciones,
    contacto_nombre,
    contacto_email,
    contacto_telefono,
    usuario_creacion,
    fecha_creacion,
    usuario_modificacion,
    fecha_modificacion,
    activo
FROM clientes
WHERE idCliente = p_id
  AND activo = 1
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
CREATE PROCEDURE sp_list_primas_por_poliza(IN p_poliza VARCHAR(50))
BEGIN
    SELECT
        p.idPoliza,  -- Added ID
        p.recibo,
        p.recibo AS cupon, -- Alias for consistency
        p.poliza,
        c.razon_social AS contratante,
        p.cia AS compania,
        p.ramo,
        -- aquí antes estaba: 'Emision' AS tipo,
        p.tipo_doc AS tipo,
        p.prima_comercial,
        p.prima_neta,
        p.prima_comercial_igv,
        p.prima_comercial_igv AS importe, -- Alias for consistency
        p.moneda,
        DATE_FORMAT(p.fecha_vencimiento, '%d/%m/%Y') AS fecha_vencimiento,
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
    fecha_vencimiento DATE NOT NULL,
    moneda VARCHAR(10) DEFAULT 'SOLES',
    importe DECIMAL(15,2) NOT NULL,
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

DELIMITER $$
CREATE PROCEDURE sp_insert_cuota(
    IN p_poliza VARCHAR(50),
    IN p_cupon VARCHAR(50),
    IN p_fecha_vencimiento DATE,
    IN p_moneda VARCHAR(10),
    IN p_importe DECIMAL(15,2),
    IN p_fecha_pago DATE,
    IN p_factura VARCHAR(50),
    IN p_observacion VARCHAR(255),
    IN p_usuario VARCHAR(50)
)
BEGIN
    INSERT INTO cuotas (
        poliza, cupon, fecha_vencimiento, moneda, importe,
        fecha_pago, factura, observacion, usuario_registro
    ) VALUES (
        p_poliza, p_cupon, p_fecha_vencimiento, p_moneda, p_importe,
        p_fecha_pago, p_factura, p_observacion, p_usuario
    );

    -- Update poliza status to CANCELADO if payment date is present
    IF p_fecha_pago IS NOT NULL THEN
        UPDATE polizas
        SET estado = 'CANCELADO'
        WHERE TRIM(poliza) = TRIM(p_poliza);
    END IF;
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
    IN p_tipo_vigencia VARCHAR(50), -- Nuevo
    IN p_endosatario VARCHAR(150), -- Nuevo
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
        recibo = p_recibo,
        tipo_vigencia = p_tipo_vigencia,
        endosatario = p_endosatario
    WHERE idPoliza = p_idPoliza;

    IF p_pdf_path IS NOT NULL AND p_pdf_path <> '' THEN
        INSERT INTO poliza_archivos (poliza_id, numero_poliza, ruta_archivo, nombre_original, origen, ramo, producto, usuario, compania)
        VALUES (p_idPoliza, p_poliza, p_pdf_path, SUBSTRING_INDEX(p_pdf_path, '/', -1), 'EDICION', p_ramo, p_ramos_producto, p_usuario_edicion, p_cia);
    END IF;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_reporte_vencimientos(
    IN p_usuarios VARCHAR(255),
    IN p_estado VARCHAR(50),
    IN p_fecha_desde DATE,
    IN p_fecha_hasta DATE,
    IN p_ramo TEXT
)
BEGIN
    SELECT
        p.cia AS compania,
        p.ramo,
        p.ramos_producto AS producto,
        c.tipo_documento,
        c.numero_documento,
        c.razon_social AS contratante,
        p.poliza,
        p.recibo AS aviso_cobranza,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
        (SELECT DATE_FORMAT(MAX(q.fecha_pago), '%d/%m/%Y') FROM cuotas q WHERE TRIM(q.poliza) = TRIM(p.poliza)) AS fecha_pago,
        p.moneda,
        p.prima_neta AS prima_neta,
        p.prima_comercial_igv AS prima_total,
        p.estado
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE (p_usuarios IS NULL OR p_usuarios = '' OR FIND_IN_SET(p.usuario_registro, p_usuarios))
    AND (p_estado IS NULL OR p_estado = '' OR p.estado = p_estado)
    AND (p_fecha_desde IS NULL OR p.vig_hasta >= p_fecha_desde)
    AND (p_fecha_hasta IS NULL OR p.vig_hasta <= p_fecha_hasta)
    AND (p_ramo IS NULL OR p_ramo = '' OR FIND_IN_SET(p.ramo, p_ramo))
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
    IN p_usuario_modificacion VARCHAR(50)
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
    usuario_modificacion = p_usuario_modificacion,
    fecha_modificacion = NOW()
WHERE idCliente = p_idCliente;
END$$

DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_delete_cliente(
    IN p_idCliente INT,
    IN p_usuario_modificacion VARCHAR(50)
)
BEGIN
    UPDATE clientes
    SET
        activo = 0,
        usuario_modificacion = p_usuario_modificacion,
        fecha_modificacion = NOW()
    WHERE idCliente = p_idCliente
      AND activo = 1;

    SELECT ROW_COUNT() AS affected_rows;
END$$
DELIMITER ;
DELIMITER $$
CREATE PROCEDURE sp_restore_cliente(
    IN p_idCliente INT,
    IN p_usuario_modificacion VARCHAR(50)
)
BEGIN
    UPDATE clientes
    SET
        activo = 1,
        usuario_modificacion = p_usuario_modificacion,
        fecha_modificacion = NOW()
    WHERE idCliente = p_idCliente
      AND activo = 0;

    SELECT ROW_COUNT() AS affected_rows;
END$$
DELIMITER ;

-- Índices de auditoría para consultas de auditoría
ALTER TABLE clientes
  ADD INDEX idx_usuario_creacion (usuario_creacion),
  ADD INDEX idx_usuario_modificacion (usuario_modificacion);

-- =====================================================
-- MÓDULO DE SINIESTROS
-- Tablas y procedimientos para gestión de siniestros
-- =====================================================


CREATE TABLE siniestros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    grupo_ramo VARCHAR(50) NOT NULL COMMENT 'RRGG, VEHICULOS, RRHH, OTROS',

    -- Relación robusta
    poliza_id INT NOT NULL,
    poliza VARCHAR(50) NOT NULL, -- opcional, solo para consulta rápida/visual

    cia VARCHAR(100) NOT NULL COMMENT 'Compañía aseguradora',
    ramo VARCHAR(120) NOT NULL,
    contratante VARCHAR(150) NOT NULL,
    asegurado VARCHAR(150) NOT NULL,

    fec_presentacion_broker DATE COMMENT 'Fecha presentación al Broker',
    fec_aviso_cia DATE COMMENT 'Fecha aviso a compañía',
    fec_presentacion_cia DATE COMMENT 'Fecha presentación a compañía',
    fec_stro DATE COMMENT 'Fecha del siniestro',
    fec_atencion_medica DATE COMMENT 'Fecha atención médica (RRHH)',
    fec_notificacion_broker DATE COMMENT 'Fecha notificación broker (VEHICULOS)',

    hora_siniestro VARCHAR(20),
    quien_reporta VARCHAR(150),
    email TEXT,
    telefonos VARCHAR(100),

    lugar_siniestro TEXT,
    causa TEXT,
    descripcion_hechos TEXT,
    siniestro_no VARCHAR(50) COMMENT 'Número de siniestro de la CIA',
    ejecutivo_cia VARCHAR(100),
    estado VARCHAR(50) DEFAULT 'PENDIENTE' COMMENT 'PENDIENTE, EN_PROCESO, CERRADO, RECHAZADO',

    liquidador_ajustador VARCHAR(150),
    conductor VARCHAR(150),
    tercero VARCHAR(150),
    comisaria VARCHAR(150),
    numero_denuncia VARCHAR(50),
    fec_denuncia_policial DATE,
    fec_entrega_doc_ajustador DATE,
    fec_entrega_doc_cia DATE,
    fec_cia_consentido DATE,
    numero_ajuste VARCHAR(50),

    hora_contacto VARCHAR(20),
    hora_culminacion VARCHAR(20),
    tipo_atencion VARCHAR(50),
    situacion VARCHAR(50),
    placa VARCHAR(20),

    tipo_persona VARCHAR(20),
    titular VARCHAR(150),
    paciente VARCHAR(150),
    diagnostico TEXT,
    coaseguro DECIMAL(15,2) DEFAULT 0.00,
    no_cubierto DECIMAL(15,2) DEFAULT 0.00,

    moneda VARCHAR(10) DEFAULT 'US$',
    monto_siniestro DECIMAL(15,2) DEFAULT 0.00,
    deducible DECIMAL(15,2) DEFAULT 0.00,
    descripcion_deducible TEXT,
    total_indemnizar DECIMAL(15,2) DEFAULT 0.00,
    fec_pago DATE,
    forma_pago VARCHAR(50),
    numero_cheque VARCHAR(50),
    banco VARCHAR(100),

    numero_factura VARCHAR(50),
    monto_pagar_factura DECIMAL(15,2) DEFAULT 0.00,
    fec_vencimiento_factura DATE,
    fec_pago_factura DATE,

    datos_vehiculo JSON,
    datos_denuncia JSON,
    datos_conductor JSON,
    datos_copiloto JSON,
    datos_tercero JSON,
    gastos_presentados JSON,

    usuario_registro VARCHAR(50),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    usuario_modificacion VARCHAR(50),
    fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    eliminado TINYINT(1) DEFAULT 0,

    INDEX idx_poliza_id (poliza_id),
    INDEX idx_poliza (poliza),
    INDEX idx_grupo_ramo (grupo_ramo),
    INDEX idx_contratante (contratante),
    INDEX idx_estado (estado),
    INDEX idx_fecha_siniestro (fec_stro),
    INDEX idx_cia (cia),
    INDEX idx_eliminado (eliminado),

    CONSTRAINT fk_siniestro_poliza_id
        FOREIGN KEY (poliza_id)
        REFERENCES polizas(idPoliza)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



-- =====================================================
-- TABLAS RELACIONADAS PARA DOCUMENTOS Y BITÁCORA
-- =====================================================


CREATE TABLE siniestro_documentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    siniestro_id INT NOT NULL,
    tipo_documento VARCHAR(100) NOT NULL COMMENT 'INFORME MEDICO, RECETA, PROFORMA, etc.',
    nombre_documento VARCHAR(255),
    numero_documento VARCHAR(50),
    fecha_documento DATE,
    monto DECIMAL(15,2) DEFAULT 0.00,
    archivo_path VARCHAR(500) COMMENT 'Ruta del archivo si está digitalizado',
    observaciones TEXT,
    usuario_registro VARCHAR(50),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    eliminado TINYINT(1) DEFAULT 0,

    INDEX idx_siniestro (siniestro_id),
    INDEX idx_tipo (tipo_documento),

    CONSTRAINT fk_documento_siniestro FOREIGN KEY (siniestro_id)
        REFERENCES siniestros(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Documentos relacionados a siniestros (principalmente para RRHH)';



CREATE TABLE siniestro_bitacora (
    id INT AUTO_INCREMENT PRIMARY KEY,
    siniestro_id INT NOT NULL,
    fecha DATE NOT NULL,
    hora VARCHAR(20),
    descripcion TEXT NOT NULL,
    responsable VARCHAR(100),
    tipo_actividad VARCHAR(50) COMMENT 'LLAMADA, EMAIL, REUNION, VISITA, etc.',
    usuario_registro VARCHAR(50),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    eliminado TINYINT(1) DEFAULT 0,

    INDEX idx_siniestro (siniestro_id),
    INDEX idx_fecha (fecha),
    INDEX idx_tipo (tipo_actividad),

    CONSTRAINT fk_bitacora_siniestro FOREIGN KEY (siniestro_id)
        REFERENCES siniestros(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Bitácora de seguimiento de siniestros';



CREATE TABLE siniestro_archivos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    siniestro_id INT NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    tipo_archivo VARCHAR(100) COMMENT 'PDF, IMAGEN, EXCEL, WORD, etc.',
    descripcion TEXT,
    ruta_archivo VARCHAR(500) NOT NULL,
    tamano_bytes BIGINT,
    usuario_subida VARCHAR(50),
    fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP,
    eliminado TINYINT(1) DEFAULT 0,

    INDEX idx_siniestro (siniestro_id),
    INDEX idx_tipo (tipo_archivo),

    CONSTRAINT fk_archivo_siniestro FOREIGN KEY (siniestro_id)
        REFERENCES siniestros(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Archivos adjuntos relacionados a siniestros';

-- =====================================================
-- PROCEDIMIENTOS PARA INSERTAR DATOS RELACIONADOS
-- =====================================================

-- Stored procedures para grupo OTROS: insertar y actualizar
DROP PROCEDURE IF EXISTS sp_insert_siniestro_otros;
DELIMITER $$
CREATE PROCEDURE sp_insert_siniestro_otros(
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_descripcion_hechos TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_descripcion_deducible TEXT,
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_gastos_presentados TEXT,
    IN p_usuario VARCHAR(50)
)
BEGIN
    INSERT INTO siniestros (
        grupo_ramo, poliza, cia, ramo, contratante, asegurado,
        fec_stro, hora_siniestro, quien_reporta, email, telefonos,
        lugar_siniestro, causa, descripcion_hechos, siniestro_no, ejecutivo_cia, estado,
        moneda, monto_siniestro, deducible, descripcion_deducible, total_indemnizar,
        fec_pago, forma_pago, numero_cheque, banco,
        numero_factura, monto_pagar_factura, fec_vencimiento_factura, fec_pago_factura,
        gastos_presentados, usuario_registro
    ) VALUES (
        'OTROS', p_poliza, p_cia, p_ramo, p_contratante, p_asegurado,
        p_fec_stro, p_hora_siniestro, p_quien_reporta, p_email, p_telefonos,
        p_lugar_siniestro, p_causa, p_descripcion_hechos, p_siniestro_no, p_ejecutivo_cia, p_estado,
        p_moneda, p_monto_siniestro, p_deducible, p_descripcion_deducible, p_total_indemnizar,
        p_fec_pago, p_forma_pago, p_numero_cheque, p_banco,
        p_numero_factura, p_monto_pagar_factura, p_fec_vencimiento_factura, p_fec_pago_factura,
        p_gastos_presentados, p_usuario
    );
    SELECT LAST_INSERT_ID() AS id;
END $$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_update_siniestro_otros;
DELIMITER $$
CREATE PROCEDURE sp_update_siniestro_otros(
    IN p_id INT,
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_descripcion_hechos TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_descripcion_deducible TEXT,
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_gastos_presentados TEXT,
    IN p_usuario_edicion VARCHAR(50)
)
BEGIN
    UPDATE siniestros SET
        grupo_ramo = 'OTROS',
        poliza = p_poliza,
        cia = p_cia,
        ramo = p_ramo,
        contratante = p_contratante,
        asegurado = p_asegurado,
        fec_stro = p_fec_stro,
        hora_siniestro = p_hora_siniestro,
        quien_reporta = p_quien_reporta,
        email = p_email,
        telefonos = p_telefonos,
        lugar_siniestro = p_lugar_siniestro,
        causa = p_causa,
        descripcion_hechos = p_descripcion_hechos,
        siniestro_no = p_siniestro_no,
        ejecutivo_cia = p_ejecutivo_cia,
        estado = p_estado,
        moneda = p_moneda,
        monto_siniestro = p_monto_siniestro,
        deducible = p_deducible,
        descripcion_deducible = p_descripcion_deducible,
        total_indemnizar = p_total_indemnizar,
        fec_pago = p_fec_pago,
        forma_pago = p_forma_pago,
        numero_cheque = p_numero_cheque,
        banco = p_banco,
        numero_factura = p_numero_factura,
        monto_pagar_factura = p_monto_pagar_factura,
        fec_vencimiento_factura = p_fec_vencimiento_factura,
        fec_pago_factura = p_fec_pago_factura,
        usuario_edicion = p_usuario_edicion
    WHERE id = p_id;

    SELECT ROW_COUNT() AS affected_rows;
END $$
DELIMITER ;

-- Procedimiento para insertar documento
DROP PROCEDURE IF EXISTS sp_insert_siniestro_documento;

DELIMITER $$
CREATE PROCEDURE sp_insert_siniestro_documento(
    IN p_siniestro_id INT,
    IN p_tipo_documento VARCHAR(100),
    IN p_nombre_documento VARCHAR(255),
    IN p_numero_documento VARCHAR(50),
    IN p_fecha_documento DATE,
    IN p_monto DECIMAL(15,2),
    IN p_archivo_path VARCHAR(500),
    IN p_observaciones TEXT,
    IN p_usuario VARCHAR(50)
)
BEGIN
    INSERT INTO siniestro_documentos (
        siniestro_id, tipo_documento, nombre_documento, numero_documento,
        fecha_documento, monto, archivo_path, observaciones, usuario_registro
    ) VALUES (
        p_siniestro_id, p_tipo_documento, p_nombre_documento, p_numero_documento,
        p_fecha_documento, p_monto, p_archivo_path, p_observaciones, p_usuario
    );

    SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- Procedimiento para insertar bitácora
DROP PROCEDURE IF EXISTS sp_insert_siniestro_bitacora;

DELIMITER $$
CREATE PROCEDURE sp_insert_siniestro_bitacora(
    IN p_siniestro_id INT,
    IN p_fecha DATE,
    IN p_hora VARCHAR(20),
    IN p_descripcion TEXT,
    IN p_responsable VARCHAR(100),
    IN p_tipo_actividad VARCHAR(50),
    IN p_usuario VARCHAR(50)
)
BEGIN
    INSERT INTO siniestro_bitacora (
        siniestro_id, fecha, hora, descripcion, responsable, tipo_actividad, usuario_registro
    ) VALUES (
        p_siniestro_id, p_fecha, p_hora, p_descripcion, p_responsable, p_tipo_actividad, p_usuario
    );

    SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- Procedimiento para insertar archivo
DROP PROCEDURE IF EXISTS sp_insert_siniestro_archivo;

DELIMITER $$
CREATE PROCEDURE sp_insert_siniestro_archivo(
    IN p_siniestro_id INT,
    IN p_nombre_archivo VARCHAR(255),
    IN p_tipo_archivo VARCHAR(100),
    IN p_descripcion TEXT,
    IN p_ruta_archivo VARCHAR(500),
    IN p_tamano_bytes BIGINT,
    IN p_usuario VARCHAR(50)
)
BEGIN
    INSERT INTO siniestro_archivos (
        siniestro_id, nombre_archivo, tipo_archivo, descripcion,
        ruta_archivo, tamano_bytes, usuario_subida
    ) VALUES (
        p_siniestro_id, p_nombre_archivo, p_tipo_archivo, p_descripcion,
        p_ruta_archivo, p_tamano_bytes, p_usuario
    );

    SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- =====================================================
-- VISTAS ÚTILES
-- =====================================================

-- Se mantienen los DROP VIEW para no causar errores si existen vistas previas,
-- las definiciones de las vistas han sido eliminadas a petición del usuario.

DROP VIEW IF EXISTS v_siniestros_resumen;
-- Vista consolidada de siniestros eliminada del script.

DROP VIEW IF EXISTS v_siniestros_rrgg;
-- Vista para siniestros RRGG eliminada del script.

DROP VIEW IF EXISTS v_siniestros_vehiculos;
-- Vista para siniestros VEHICULOS eliminada del script.

DROP VIEW IF EXISTS v_siniestros_rrhh;
-- Vista para siniestros RRHH eliminada del script.

-- =====================================================
-- PROCEDIMIENTOS DE ACTUALIZACIÓN DE SINIESTROS (RRGG / RRHH / VEHICULOS)
-- Estos procedimientos se nombran como sp_update_siniestro_* para coincidir con los controladores.
-- =====================================================

DROP PROCEDURE IF EXISTS sp_update_siniestro_rrgg;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_update_siniestro_rrgg(
    IN p_id INT,
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_presentacion_broker DATE,
    IN p_fec_aviso_cia DATE,
    IN p_fec_presentacion_cia DATE,
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_descripcion_hechos TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_liquidador_ajustador VARCHAR(150),
    IN p_conductor VARCHAR(150),
    IN p_tercero VARCHAR(150),
    IN p_comisaria VARCHAR(150),
    IN p_numero_denuncia VARCHAR(50),
    IN p_fec_denuncia_policial DATE,
    IN p_fec_entrega_doc_ajustador DATE,
    IN p_fec_entrega_doc_cia DATE,
    IN p_fec_cia_consentido DATE,
    IN p_numero_ajuste VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_usuario_modificacion VARCHAR(50)
)
BEGIN
    UPDATE siniestros SET
        poliza = p_poliza,
        cia = p_cia,
        ramo = p_ramo,
        contratante = p_contratante,
        asegurado = p_asegurado,
        fec_presentacion_broker = p_fec_presentacion_broker,
        fec_aviso_cia = p_fec_aviso_cia,
        fec_presentacion_cia = p_fec_presentacion_cia,
        fec_stro = p_fec_stro,
        hora_siniestro = p_hora_siniestro,
        quien_reporta = p_quien_reporta,
        email = p_email,
        telefonos = p_telefonos,
        lugar_siniestro = p_lugar_siniestro,
        causa = p_causa,
        descripcion_hechos = p_descripcion_hechos,
        siniestro_no = p_siniestro_no,
        ejecutivo_cia = p_ejecutivo_cia,
        estado = p_estado,
        liquidador_ajustador = p_liquidador_ajustador,
        conductor = p_conductor,
        tercero = p_tercero,
        comisaria = p_comisaria,
        numero_denuncia = p_numero_denuncia,
        fec_denuncia_policial = p_fec_denuncia_policial,
        fec_entrega_doc_ajustador = p_fec_entrega_doc_ajustador,
        fec_entrega_doc_cia = p_fec_entrega_doc_cia,
        fec_cia_consentido = p_fec_cia_consentido,
        numero_ajuste = p_numero_ajuste,
        moneda = p_moneda,
        monto_siniestro = p_monto_siniestro,
        deducible = p_deducible,
        total_indemnizar = p_total_indemnizar,
        fec_pago = p_fec_pago,
        forma_pago = p_forma_pago,
        numero_cheque = p_numero_cheque,
        banco = p_banco,
        numero_factura = p_numero_factura,
        monto_pagar_factura = p_monto_pagar_factura,
        fec_vencimiento_factura = p_fec_vencimiento_factura,
        fec_pago_factura = p_fec_pago_factura,
        usuario_modificacion = p_usuario_modificacion,
        fecha_modificacion = NOW()
    WHERE id = p_id;

    SELECT ROW_COUNT() AS affected_rows;
END$$
DELIMITER ;
DROP PROCEDURE IF EXISTS sp_update_siniestro_vehiculos;
DELIMITER $$

CREATE DEFINER=`root`@`localhost` PROCEDURE sp_update_siniestro_vehiculos(
    IN p_id INT,
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_presentacion_broker DATE,
    IN p_fec_aviso_cia DATE,
    IN p_fec_presentacion_cia DATE,
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_tipo_atencion VARCHAR(50),
    IN p_situacion VARCHAR(50),
    IN p_placa VARCHAR(20),
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_usuario_modificacion VARCHAR(50)
)
BEGIN
    UPDATE siniestros SET
        poliza = p_poliza,
        cia = p_cia,
        ramo = p_ramo,
        contratante = p_contratante,
        asegurado = p_asegurado,
        fec_presentacion_broker = p_fec_presentacion_broker,
        fec_aviso_cia = p_fec_aviso_cia,
        fec_presentacion_cia = p_fec_presentacion_cia,
        fec_stro = p_fec_stro,
        hora_siniestro = p_hora_siniestro,
        quien_reporta = p_quien_reporta,
        email = p_email,
        telefonos = p_telefonos,
        lugar_siniestro = p_lugar_siniestro,
        causa = p_causa,
        tipo_atencion = p_tipo_atencion,
        situacion = p_situacion,
        placa = p_placa,
        siniestro_no = p_siniestro_no,
        ejecutivo_cia = p_ejecutivo_cia,
        estado = p_estado,
        moneda = p_moneda,
        monto_siniestro = p_monto_siniestro,
        deducible = p_deducible,
        total_indemnizar = p_total_indemnizar,
        fec_pago = p_fec_pago,
        forma_pago = p_forma_pago,
        numero_cheque = p_numero_cheque,
        banco = p_banco,
        numero_factura = p_numero_factura,
        monto_pagar_factura = p_monto_pagar_factura,
        fec_vencimiento_factura = p_fec_vencimiento_factura,
        fec_pago_factura = p_fec_pago_factura,
        usuario_modificacion = p_usuario_modificacion,
        fecha_modificacion = NOW()
    WHERE id = p_id;

    SELECT ROW_COUNT() AS affected_rows;
END$$

DELIMITER ;

DROP PROCEDURE IF EXISTS sp_update_siniestro_rrhh;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_update_siniestro_rrhh(
    IN p_id INT,
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_presentacion_broker DATE,
    IN p_fec_aviso_cia DATE,
    IN p_fec_presentacion_cia DATE,
    IN p_fec_stro DATE,
    IN p_fec_atencion_medica DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_descripcion_hechos TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_usuario_modificacion VARCHAR(50)
)
BEGIN
    UPDATE siniestros SET
        poliza = p_poliza,
        cia = p_cia,
        ramo = p_ramo,
        contratante = p_contratante,
        asegurado = p_asegurado,
        fec_presentacion_broker = p_fec_presentacion_broker,
        fec_aviso_cia = p_fec_aviso_cia,
        fec_presentacion_cia = p_fec_presentacion_cia,
        fec_stro = p_fec_stro,
        fec_atencion_medica = p_fec_atencion_medica,
        hora_siniestro = p_hora_siniestro,
        quien_reporta = p_quien_reporta,
        email = p_email,
        telefonos = p_telefonos,
        lugar_siniestro = p_lugar_siniestro,
        causa = p_causa,
        descripcion_hechos = p_descripcion_hechos,
        siniestro_no = p_siniestro_no,
        ejecutivo_cia = p_ejecutivo_cia,
        estado = p_estado,
        moneda = p_moneda,
        monto_siniestro = p_monto_siniestro,
        deducible = p_deducible,
        total_indemnizar = p_total_indemnizar,
        fec_pago = p_fec_pago,
        forma_pago = p_forma_pago,
        numero_cheque = p_numero_cheque,
        banco = p_banco,
        numero_factura = p_numero_factura,
        monto_pagar_factura = p_monto_pagar_factura,
        fec_vencimiento_factura = p_fec_vencimiento_factura,
        fec_pago_factura = p_fec_pago_factura,
        usuario_modificacion = p_usuario_modificacion,
        fecha_modificacion = NOW()
    WHERE id = p_id;

    SELECT ROW_COUNT() AS affected_rows;
END$$
DELIMITER ;



CREATE TABLE IF NOT EXISTS usos (
    id INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(120) NOT NULL,
    estado ENUM('Activado','Inactivo') NOT NULL DEFAULT 'Activado',
    PRIMARY KEY (id),
    UNIQUE KEY uq_usos_nombre (nombre),
    KEY idx_usos_estado (estado),
    KEY idx_usos_nombre (nombre)
) ENGINE=InnoDB   DEFAULT CHARSET=utf8mb4   COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS clases (
    id INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(150) NOT NULL,
    costo_soat DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    estado ENUM('Activado','Inactivo') NOT NULL DEFAULT 'Activado',
    PRIMARY KEY (id),
    UNIQUE KEY uq_clases_nombre (nombre),
    KEY idx_clases_estado (estado),
    KEY idx_clases_nombre (nombre)
) ENGINE=InnoDB   DEFAULT CHARSET=utf8mb4   COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS marcas (
    id INT NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(120) NOT NULL,
    estado ENUM('Activado','Inactivo') NOT NULL DEFAULT 'Activado',
    PRIMARY KEY (id),
    UNIQUE KEY uq_marcas_nombre (nombre),
    KEY idx_marcas_estado (estado),
    KEY idx_marcas_nombre (nombre)
) ENGINE=InnoDB   DEFAULT CHARSET=utf8mb4   COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS modelos (
    id INT NOT NULL AUTO_INCREMENT,
    marca_id INT NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    estado ENUM('Activado','Inactivo') NOT NULL DEFAULT 'Activado',
    PRIMARY KEY (id),
    KEY idx_modelos_marca_id (marca_id),
    KEY idx_modelos_estado (estado),
    KEY idx_modelos_nombre (nombre),
    KEY idx_modelos_marca_estado (marca_id, estado),
    UNIQUE KEY uq_modelo_por_marca (marca_id, nombre),
    CONSTRAINT fk_modelos_marcas
        FOREIGN KEY (marca_id) REFERENCES marcas(id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB   DEFAULT CHARSET=utf8mb4   COLLATE=utf8mb4_unicode_ci;


CREATE OR REPLACE VIEW vw_modelos_marcas AS SELECT
    mo.id AS modelo_id,
    mo.nombre AS modelo_nombre,
    mo.estado AS modelo_estado,
    ma.id AS marca_id,
    ma.nombre AS marca_nombre,
    ma.estado AS marca_estado
FROM modelos mo
JOIN marcas ma ON ma.id = mo.marca_id;



DROP PROCEDURE IF EXISTS sp_listar_usos;
DELIMITER $$
CREATE PROCEDURE sp_listar_usos()
BEGIN
    SELECT id, nombre, estado
    FROM usos
    ORDER BY nombre ASC;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_insertar_uso;
DELIMITER $$
CREATE PROCEDURE sp_insertar_uso(
    IN p_nombre VARCHAR(120),
    OUT p_new_id INT )
BEGIN
    IF TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre de uso no puede estar vacío';
    END IF;

    INSERT INTO usos (nombre)
    VALUES (TRIM(p_nombre))
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

    SET p_new_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_delete_uso;
DELIMITER $$
CREATE PROCEDURE sp_delete_uso(
    IN p_id INT,
    OUT p_deleted INT )
BEGIN
    DELETE FROM usos WHERE id = p_id;
    SET p_deleted = ROW_COUNT();
END$$
DELIMITER ;

-- =========================================================
-- PROCEDIMIENTOS: CLASES
-- =========================================================

DROP PROCEDURE IF EXISTS sp_listar_clases;
DELIMITER $$
CREATE PROCEDURE sp_listar_clases()
BEGIN
    SELECT id, nombre, costo_soat, estado
    FROM clases
    ORDER BY nombre ASC;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_insertar_clase;
DELIMITER $$
CREATE PROCEDURE sp_insertar_clase(
    IN p_nombre VARCHAR(150),
    IN p_costo_soat DECIMAL(10,2),
    OUT p_new_id INT )
BEGIN
    IF TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre de clase no puede estar vacío';
    END IF;

    INSERT INTO clases (nombre, costo_soat)
    VALUES (TRIM(p_nombre), IFNULL(p_costo_soat, 0.00))
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

    SET p_new_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_delete_clase;
DELIMITER $$
CREATE PROCEDURE sp_delete_clase(
    IN p_id INT,
    OUT p_deleted INT )
BEGIN
    DELETE FROM clases WHERE id = p_id;
    SET p_deleted = ROW_COUNT();
END$$
DELIMITER ;

-- =========================================================
-- PROCEDIMIENTOS: MARCAS
-- =========================================================

DROP PROCEDURE IF EXISTS sp_listar_marcas;
DELIMITER $$
CREATE PROCEDURE sp_listar_marcas()
BEGIN
    SELECT id, nombre, estado
    FROM marcas
    ORDER BY nombre ASC;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_insertar_marca;
DELIMITER $$
CREATE PROCEDURE sp_insertar_marca(
    IN p_nombre VARCHAR(120),
    OUT p_new_id INT )
BEGIN
    IF TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre de marca no puede estar vacío';
    END IF;

    INSERT INTO marcas (nombre)
    VALUES (TRIM(p_nombre))
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

    SET p_new_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_delete_marca;
DELIMITER $$
CREATE PROCEDURE sp_delete_marca(
    IN p_id INT,
    OUT p_deleted INT )
BEGIN
    IF EXISTS (SELECT 1 FROM modelos WHERE marca_id = p_id) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'No se puede eliminar la marca: existen modelos asociados';
    END IF;

    DELETE FROM marcas WHERE id = p_id;
    SET p_deleted = ROW_COUNT();
END$$
DELIMITER ;

-- =========================================================
-- PROCEDIMIENTOS: MODELOS
-- =========================================================

DROP PROCEDURE IF EXISTS sp_listar_modelos;
DELIMITER $$
CREATE PROCEDURE sp_listar_modelos()
BEGIN
    SELECT
        mo.id AS modelo_id,
        ma.id AS marca_id,
        ma.nombre AS marca,
        mo.nombre AS modelo,
        mo.estado
    FROM modelos mo
    JOIN marcas ma ON ma.id = mo.marca_id
    ORDER BY ma.nombre, mo.nombre;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_insertar_modelo;
DELIMITER $$
CREATE PROCEDURE sp_insertar_modelo(
    IN p_marca_id INT,
    IN p_nombre VARCHAR(150),
    OUT p_new_id INT )
BEGIN
    IF TRIM(p_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre de modelo no puede estar vacío';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM marcas WHERE id = p_marca_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La marca indicada no existe';
    END IF;

    INSERT INTO modelos (marca_id, nombre)
    VALUES (p_marca_id, TRIM(p_nombre))
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

    SET p_new_id = LAST_INSERT_ID();
END$$
DELIMITER ;

-- Inserta modelo resolviendo marca por nombre (sin tabla temporal)
DROP PROCEDURE IF EXISTS sp_insertar_modelo_por_nombres;
DELIMITER $$
CREATE PROCEDURE sp_insertar_modelo_por_nombres(
    IN  p_marca_nombre  VARCHAR(120),
    IN  p_modelo_nombre VARCHAR(150),
    OUT p_marca_id      INT,
    OUT p_modelo_id     INT )
BEGIN
    IF TRIM(p_marca_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre de marca no puede estar vacío';
    END IF;

    IF TRIM(p_modelo_nombre) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre de modelo no puede estar vacío';
    END IF;

    INSERT INTO marcas (nombre)
    VALUES (TRIM(p_marca_nombre))
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

    SET p_marca_id = LAST_INSERT_ID();

    INSERT INTO modelos (marca_id, nombre)
    VALUES (p_marca_id, TRIM(p_modelo_nombre))
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

    SET p_modelo_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_delete_modelo;
DELIMITER $$
CREATE PROCEDURE sp_delete_modelo(
    IN p_id INT,
    OUT p_deleted INT )
BEGIN
    DELETE FROM modelos WHERE id = p_id;
    SET p_deleted = ROW_COUNT();
END$$
DELIMITER ;

-- =====================================================
-- SP ADICIONALES MÓDULO SINIESTROS (compatibilidad)
-- Pegar debajo del final de tu script actual
-- =====================================================

-- 1) Obtener siniestro por ID
DROP PROCEDURE IF EXISTS sp_get_siniestro_by_id;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_get_siniestro_by_id(IN p_id INT)
BEGIN
    SELECT *
    FROM siniestros
    WHERE id = p_id
    LIMIT 1;
END$$
DELIMITER ;

-- 2) Eliminar siniestro (físico)
DROP PROCEDURE IF EXISTS sp_delete_siniestro;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_delete_siniestro(IN p_id INT)
BEGIN
    DELETE FROM siniestros
    WHERE id = p_id;

    SELECT ROW_COUNT() AS affected_rows;
END$$
DELIMITER ;

-- 3) Insert genérico siniestro
DROP PROCEDURE IF EXISTS sp_insert_siniestro;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_insert_siniestro(
    IN p_grupo_ramo VARCHAR(20),
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_presentacion_broker DATE,
    IN p_fec_aviso_cia DATE,
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_descripcion_hechos TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_liquidador_ajustador VARCHAR(150),
    IN p_conductor VARCHAR(150),
    IN p_tercero VARCHAR(150),
    IN p_comisaria VARCHAR(150),
    IN p_numero_denuncia VARCHAR(50),
    IN p_fec_denuncia_policial DATE,
    IN p_fec_entrega_doc_ajustador DATE,
    IN p_fec_entrega_doc_cia DATE,
    IN p_fec_cia_consentido DATE,
    IN p_numero_ajuste VARCHAR(50),
    IN p_fec_notificacion_broker DATE,
    IN p_hora_contacto VARCHAR(20),
    IN p_hora_culminacion VARCHAR(20),
    IN p_tipo_atencion VARCHAR(50),
    IN p_fec_presentacion_cia DATE,
    IN p_situacion VARCHAR(50),
    IN p_placa VARCHAR(20),
    IN p_fec_atencion_medica DATE,
    IN p_tipo_persona VARCHAR(20),
    IN p_titular VARCHAR(150),
    IN p_paciente VARCHAR(150),
    IN p_diagnostico TEXT,
    IN p_coaseguro DECIMAL(15,2),
    IN p_no_cubierto DECIMAL(15,2),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_descripcion_deducible TEXT,
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_datos_vehiculo JSON,
    IN p_datos_denuncia JSON,
    IN p_datos_conductor JSON,
    IN p_datos_copiloto JSON,
    IN p_datos_tercero JSON,
    IN p_gastos_presentados JSON,
    IN p_usuario_registro VARCHAR(50)
)
BEGIN
    INSERT INTO siniestros (
        grupo_ramo, poliza, cia, ramo, contratante, asegurado,
        fec_presentacion_broker, fec_aviso_cia, fec_stro, hora_siniestro,
        quien_reporta, email, telefonos, lugar_siniestro, causa, descripcion_hechos,
        siniestro_no, ejecutivo_cia, estado,
        liquidador_ajustador, conductor, tercero, comisaria, numero_denuncia,
        fec_denuncia_policial, fec_entrega_doc_ajustador, fec_entrega_doc_cia,
        fec_cia_consentido, numero_ajuste,
        fec_notificacion_broker, hora_contacto, hora_culminacion, tipo_atencion,
        fec_presentacion_cia, situacion, placa,
        fec_atencion_medica, tipo_persona, titular, paciente, diagnostico,
        coaseguro, no_cubierto,
        moneda, monto_siniestro, deducible, descripcion_deducible, total_indemnizar,
        fec_pago, forma_pago, numero_cheque, banco,
        numero_factura, monto_pagar_factura, fec_vencimiento_factura, fec_pago_factura,
        datos_vehiculo, datos_denuncia, datos_conductor, datos_copiloto, datos_tercero,
        gastos_presentados,
        usuario_registro
    ) VALUES (
        p_grupo_ramo, p_poliza, p_cia, p_ramo, p_contratante, p_asegurado,
        p_fec_presentacion_broker, p_fec_aviso_cia, p_fec_stro, p_hora_siniestro,
        p_quien_reporta, p_email, p_telefonos, p_lugar_siniestro, p_causa, p_descripcion_hechos,
        p_siniestro_no, p_ejecutivo_cia, p_estado,
        p_liquidador_ajustador, p_conductor, p_tercero, p_comisaria, p_numero_denuncia,
        p_fec_denuncia_policial, p_fec_entrega_doc_ajustador, p_fec_entrega_doc_cia,
        p_fec_cia_consentido, p_numero_ajuste,
        p_fec_notificacion_broker, p_hora_contacto, p_hora_culminacion, p_tipo_atencion,
        p_fec_presentacion_cia, p_situacion, p_placa,
        p_fec_atencion_medica, p_tipo_persona, p_titular, p_paciente, p_diagnostico,
        p_coaseguro, p_no_cubierto,
        p_moneda, p_monto_siniestro, p_deducible, p_descripcion_deducible, p_total_indemnizar,
        p_fec_pago, p_forma_pago, p_numero_cheque, p_banco,
        p_numero_factura, p_monto_pagar_factura, p_fec_vencimiento_factura, p_fec_pago_factura,
        p_datos_vehiculo, p_datos_denuncia, p_datos_conductor, p_datos_copiloto, p_datos_tercero,
        p_gastos_presentados,
        p_usuario_registro
    );

    SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- 4) Insertar siniestro OTROS
DROP PROCEDURE IF EXISTS sp_insert_siniestro_otros;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_insert_siniestro_otros(
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_descripcion_hechos TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_descripcion_deducible TEXT,
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_gastos_presentados TEXT,
    IN p_usuario VARCHAR(50)
)
BEGIN
    INSERT INTO siniestros (
        grupo_ramo, poliza, cia, ramo, contratante, asegurado,
        fec_stro, hora_siniestro, quien_reporta, email, telefonos,
        lugar_siniestro, causa, descripcion_hechos, siniestro_no, ejecutivo_cia, estado,
        moneda, monto_siniestro, deducible, descripcion_deducible, total_indemnizar,
        fec_pago, forma_pago, numero_cheque, banco,
        numero_factura, monto_pagar_factura, fec_vencimiento_factura, fec_pago_factura,
        gastos_presentados, usuario_registro
    ) VALUES (
        'OTROS', p_poliza, p_cia, p_ramo, p_contratante, p_asegurado,
        p_fec_stro, p_hora_siniestro, p_quien_reporta, p_email, p_telefonos,
        p_lugar_siniestro, p_causa, p_descripcion_hechos, p_siniestro_no, p_ejecutivo_cia, p_estado,
        p_moneda, p_monto_siniestro, p_deducible, p_descripcion_deducible, p_total_indemnizar,
        p_fec_pago, p_forma_pago, p_numero_cheque, p_banco,
        p_numero_factura, p_monto_pagar_factura, p_fec_vencimiento_factura, p_fec_pago_factura,
        CAST(p_gastos_presentados AS JSON), p_usuario
    );

    SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- 5) Insertar siniestro RRGG
DROP PROCEDURE IF EXISTS sp_insert_siniestro_rrgg;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_insert_siniestro_rrgg(
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_presentacion_broker DATE,
    IN p_fec_aviso_cia DATE,
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_descripcion_hechos TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_liquidador_ajustador VARCHAR(150),
    IN p_conductor VARCHAR(150),
    IN p_tercero VARCHAR(150),
    IN p_comisaria VARCHAR(150),
    IN p_numero_denuncia VARCHAR(50),
    IN p_fec_denuncia_policial DATE,
    IN p_fec_entrega_doc_ajustador DATE,
    IN p_fec_entrega_doc_cia DATE,
    IN p_fec_cia_consentido DATE,
    IN p_numero_ajuste VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_descripcion_deducible TEXT,
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_usuario_registro VARCHAR(50)
)
BEGIN
    INSERT INTO siniestros (
        grupo_ramo, poliza, cia, ramo, contratante, asegurado,
        fec_presentacion_broker, fec_aviso_cia, fec_stro, hora_siniestro,
        quien_reporta, email, telefonos, lugar_siniestro, causa, descripcion_hechos,
        siniestro_no, ejecutivo_cia, estado,
        liquidador_ajustador, conductor, tercero, comisaria, numero_denuncia,
        fec_denuncia_policial, fec_entrega_doc_ajustador, fec_entrega_doc_cia,
        fec_cia_consentido, numero_ajuste,
        moneda, monto_siniestro, deducible, descripcion_deducible, total_indemnizar,
        fec_pago, forma_pago, numero_cheque, banco,
        numero_factura, monto_pagar_factura, fec_vencimiento_factura, fec_pago_factura,
        usuario_registro
    ) VALUES (
        'RRGG', p_poliza, p_cia, p_ramo, p_contratante, p_asegurado,
        p_fec_presentacion_broker, p_fec_aviso_cia, p_fec_stro, p_hora_siniestro,
        p_quien_reporta, p_email, p_telefonos, p_lugar_siniestro, p_causa, p_descripcion_hechos,
        p_siniestro_no, p_ejecutivo_cia, p_estado,
        p_liquidador_ajustador, p_conductor, p_tercero, p_comisaria, p_numero_denuncia,
        p_fec_denuncia_policial, p_fec_entrega_doc_ajustador, p_fec_entrega_doc_cia,
        p_fec_cia_consentido, p_numero_ajuste,
        p_moneda, p_monto_siniestro, p_deducible, p_descripcion_deducible, p_total_indemnizar,
        p_fec_pago, p_forma_pago, p_numero_cheque, p_banco,
        p_numero_factura, p_monto_pagar_factura, p_fec_vencimiento_factura, p_fec_pago_factura,
        p_usuario_registro
    );

    SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- 6) Insertar siniestro RRHH
DROP PROCEDURE IF EXISTS sp_insert_siniestro_rrhh;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_insert_siniestro_rrhh(
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_presentacion_broker DATE,
    IN p_fec_atencion_medica DATE,
    IN p_fec_aviso_cia DATE,
    IN p_fec_presentacion_cia DATE,
    IN p_fec_cia_consentido DATE,
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_tipo_persona VARCHAR(20),
    IN p_titular VARCHAR(150),
    IN p_paciente VARCHAR(150),
    IN p_diagnostico TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_descripcion_deducible TEXT,
    IN p_coaseguro DECIMAL(15,2),
    IN p_no_cubierto DECIMAL(15,2),
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_gastos_presentados JSON,
    IN p_usuario_registro VARCHAR(50)
)
BEGIN
    INSERT INTO siniestros (
        grupo_ramo, poliza, cia, ramo, contratante, asegurado,
        fec_presentacion_broker, fec_atencion_medica, fec_aviso_cia, fec_presentacion_cia, fec_cia_consentido,
        quien_reporta, email, telefonos, tipo_persona, titular, paciente, diagnostico,
        siniestro_no, ejecutivo_cia, estado,
        moneda, monto_siniestro, deducible, descripcion_deducible, coaseguro, no_cubierto, total_indemnizar,
        fec_pago, forma_pago, numero_cheque, banco,
        numero_factura, monto_pagar_factura, fec_vencimiento_factura, fec_pago_factura,
        gastos_presentados, usuario_registro
    ) VALUES (
        'RRHH', p_poliza, p_cia, p_ramo, p_contratante, p_asegurado,
        p_fec_presentacion_broker, p_fec_atencion_medica, p_fec_aviso_cia, p_fec_presentacion_cia, p_fec_cia_consentido,
        p_quien_reporta, p_email, p_telefonos, p_tipo_persona, p_titular, p_paciente, p_diagnostico,
        p_siniestro_no, p_ejecutivo_cia, p_estado,
        p_moneda, p_monto_siniestro, p_deducible, p_descripcion_deducible, p_coaseguro, p_no_cubierto, p_total_indemnizar,
        p_fec_pago, p_forma_pago, p_numero_cheque, p_banco,
        p_numero_factura, p_monto_pagar_factura, p_fec_vencimiento_factura, p_fec_pago_factura,
        p_gastos_presentados, p_usuario_registro
    );

    SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- 7) Insertar siniestro VEHICULOS
DROP PROCEDURE IF EXISTS sp_insert_siniestro_vehiculos;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_insert_siniestro_vehiculos(
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_notificacion_broker DATE,
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email VARCHAR(100),
    IN p_telefonos VARCHAR(100),
    IN p_hora_contacto VARCHAR(20),
    IN p_hora_culminacion VARCHAR(20),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_tipo_atencion VARCHAR(50),
    IN p_fec_presentacion_cia DATE,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_situacion VARCHAR(50),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_descripcion_deducible TEXT,
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_datos_vehiculo JSON,
    IN p_datos_denuncia JSON,
    IN p_datos_conductor JSON,
    IN p_datos_copiloto JSON,
    IN p_datos_tercero JSON,
    IN p_usuario_registro VARCHAR(50)
)
BEGIN
    INSERT INTO siniestros (
        grupo_ramo, poliza, cia, ramo, contratante, asegurado,
        fec_notificacion_broker, fec_stro, hora_siniestro,
        quien_reporta, email, telefonos, hora_contacto, hora_culminacion,
        lugar_siniestro, causa, tipo_atencion, fec_presentacion_cia,
        siniestro_no, ejecutivo_cia, estado, situacion,
        moneda, monto_siniestro, deducible, descripcion_deducible, total_indemnizar,
        fec_pago, forma_pago, numero_cheque, banco,
        numero_factura, monto_pagar_factura, fec_vencimiento_factura, fec_pago_factura,
        datos_vehiculo, datos_denuncia, datos_conductor, datos_copiloto, datos_tercero,
        usuario_registro
    ) VALUES (
        'VEHICULOS', p_poliza, p_cia, p_ramo, p_contratante, p_asegurado,
        p_fec_notificacion_broker, p_fec_stro, p_hora_siniestro,
        p_quien_reporta, p_email, p_telefonos, p_hora_contacto, p_hora_culminacion,
        p_lugar_siniestro, p_causa, p_tipo_atencion, p_fec_presentacion_cia,
        p_siniestro_no, p_ejecutivo_cia, p_estado, p_situacion,
        p_moneda, p_monto_siniestro, p_deducible, p_descripcion_deducible, p_total_indemnizar,
        p_fec_pago, p_forma_pago, p_numero_cheque, p_banco,
        p_numero_factura, p_monto_pagar_factura, p_fec_vencimiento_factura, p_fec_pago_factura,
        p_datos_vehiculo, p_datos_denuncia, p_datos_conductor, p_datos_copiloto, p_datos_tercero,
        p_usuario_registro
    );

    SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- 8) Listar siniestros (como estaba originalmente)
DROP PROCEDURE IF EXISTS sp_list_siniestros;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_list_siniestros()
BEGIN
    SELECT
        id, grupo_ramo, contratante, poliza, cia, ramo, fec_stro,
        causa, siniestro_no, monto_siniestro, estado, ejecutivo_cia, placa, creado_en
    FROM siniestros
    ORDER BY creado_en DESC;
END$$
DELIMITER ;

-- 9) Listar siniestros por póliza (como estaba originalmente)
DROP PROCEDURE IF EXISTS sp_list_siniestros_por_poliza;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_list_siniestros_por_poliza(IN p_poliza VARCHAR(50))
BEGIN
    SELECT
        id, grupo_ramo, contratante, poliza, cia, ramo, fec_stro,
        causa, siniestro_no, monto_siniestro, estado, ejecutivo_cia, placa, creado_en
    FROM siniestros
    WHERE poliza = p_poliza
    ORDER BY fec_stro DESC;
END$$
DELIMITER ;

-- 10) Update genérico siniestro
DROP PROCEDURE IF EXISTS sp_update_siniestro;
DELIMITER $$
CREATE DEFINER=`root`@`localhost` PROCEDURE sp_update_siniestro(
    IN p_id INT,
    IN p_grupo_ramo VARCHAR(20),
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_contratante VARCHAR(150),
    IN p_asegurado VARCHAR(150),
    IN p_fec_presentacion_broker DATE,
    IN p_fec_aviso_cia DATE,
    IN p_fec_stro DATE,
    IN p_hora_siniestro VARCHAR(20),
    IN p_quien_reporta VARCHAR(150),
    IN p_email TEXT,
    IN p_telefonos VARCHAR(100),
    IN p_lugar_siniestro TEXT,
    IN p_causa TEXT,
    IN p_descripcion_hechos TEXT,
    IN p_siniestro_no VARCHAR(50),
    IN p_ejecutivo_cia VARCHAR(100),
    IN p_estado VARCHAR(50),
    IN p_liquidador_ajustador VARCHAR(150),
    IN p_conductor VARCHAR(150),
    IN p_tercero VARCHAR(150),
    IN p_comisaria VARCHAR(150),
    IN p_numero_denuncia VARCHAR(50),
    IN p_fec_denuncia_policial DATE,
    IN p_fec_entrega_doc_ajustador DATE,
    IN p_fec_entrega_doc_cia DATE,
    IN p_fec_cia_consentido DATE,
    IN p_numero_ajuste VARCHAR(50),
    IN p_fec_notificacion_broker DATE,
    IN p_hora_contacto VARCHAR(20),
    IN p_hora_culminacion VARCHAR(20),
    IN p_tipo_atencion VARCHAR(50),
    IN p_fec_presentacion_cia DATE,
    IN p_situacion VARCHAR(50),
    IN p_placa VARCHAR(20),
    IN p_fec_atencion_medica DATE,
    IN p_tipo_persona VARCHAR(20),
    IN p_titular VARCHAR(150),
    IN p_paciente VARCHAR(150),
    IN p_diagnostico TEXT,
    IN p_coaseguro DECIMAL(15,2),
    IN p_no_cubierto DECIMAL(15,2),
    IN p_moneda VARCHAR(10),
    IN p_monto_siniestro DECIMAL(15,2),
    IN p_deducible DECIMAL(15,2),
    IN p_descripcion_deducible TEXT,
    IN p_total_indemnizar DECIMAL(15,2),
    IN p_fec_pago DATE,
    IN p_forma_pago VARCHAR(50),
    IN p_numero_cheque VARCHAR(50),
    IN p_banco VARCHAR(100),
    IN p_numero_factura VARCHAR(50),
    IN p_monto_pagar_factura DECIMAL(15,2),
    IN p_fec_vencimiento_factura DATE,
    IN p_fec_pago_factura DATE,
    IN p_datos_vehiculo JSON,
    IN p_datos_denuncia JSON,
    IN p_datos_conductor JSON,
    IN p_datos_copiloto JSON,
    IN p_datos_tercero JSON,
    IN p_gastos_presentados JSON,
    IN p_usuario_edicion VARCHAR(50)
)
BEGIN
    UPDATE siniestros SET
        grupo_ramo = p_grupo_ramo,
        poliza = p_poliza,
        cia = p_cia,
        ramo = p_ramo,
        contratante = p_contratante,
        asegurado = p_asegurado,
        fec_presentacion_broker = p_fec_presentacion_broker,
        fec_aviso_cia = p_fec_aviso_cia,
        fec_stro = p_fec_stro,
        hora_siniestro = p_hora_siniestro,
        quien_reporta = p_quien_reporta,
        email = p_email,
        telefonos = p_telefonos,
        lugar_siniestro = p_lugar_siniestro,
        causa = p_causa,
        descripcion_hechos = p_descripcion_hechos,
        siniestro_no = p_siniestro_no,
        ejecutivo_cia = p_ejecutivo_cia,
        estado = p_estado,
        liquidador_ajustador = p_liquidador_ajustador,
        conductor = p_conductor,
        tercero = p_tercero,
        comisaria = p_comisaria,
        numero_denuncia = p_numero_denuncia,
        fec_denuncia_policial = p_fec_denuncia_policial,
        fec_entrega_doc_ajustador = p_fec_entrega_doc_ajustador,
        fec_entrega_doc_cia = p_fec_entrega_doc_cia,
        fec_cia_consentido = p_fec_cia_consentido,
        numero_ajuste = p_numero_ajuste,
        fec_notificacion_broker = p_fec_notificacion_broker,
        hora_contacto = p_hora_contacto,
        hora_culminacion = p_hora_culminacion,
        tipo_atencion = p_tipo_atencion,
        fec_presentacion_cia = p_fec_presentacion_cia,
        situacion = p_situacion,
        placa = p_placa,
        fec_atencion_medica = p_fec_atencion_medica,
        tipo_persona = p_tipo_persona,
        titular = p_titular,
        paciente = p_paciente,
        diagnostico = p_diagnostico,
        coaseguro = p_coaseguro,
        no_cubierto = p_no_cubierto,
        moneda = p_moneda,
        monto_siniestro = p_monto_siniestro,
        deducible = p_deducible,
        descripcion_deducible = p_descripcion_deducible,
        total_indemnizar = p_total_indemnizar,
        fec_pago = p_fec_pago,
        forma_pago = p_forma_pago,
        numero_cheque = p_numero_cheque,
        banco = p_banco,
        numero_factura = p_numero_factura,
        monto_pagar_factura = p_monto_pagar_factura,
        fec_vencimiento_factura = p_fec_vencimiento_factura,
        fec_pago_factura = p_fec_pago_factura,
        datos_vehiculo = p_datos_vehiculo,
        datos_denuncia = p_datos_denuncia,
        datos_conductor = p_datos_conductor,
        datos_copiloto = p_datos_copiloto,
        datos_tercero = p_datos_tercero,
        gastos_presentados = p_gastos_presentados,
        usuario_modificacion = p_usuario_edicion,
        fecha_modificacion = NOW()
    WHERE id = p_id;

    SELECT ROW_COUNT() AS affected_rows;
END$$
DELIMITER ;

-- rol 
-- 1. Create roles table
CREATE TABLE IF NOT EXISTS roles (
    idRol INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Insert default roles
INSERT INTO roles (nombre, descripcion) VALUES
('BROKER', 'Todo acceso'),
('EJECUTIVO DE CUENTAS', 'Acceso a todo, menos a maestros y solo mira y ELIMINA'),
('OPERADOR', 'Acceso a todo, menos a maestros, adiciona, actualiza, NO ELIMINA, Reportes sin comisiones'),
('SUB AGENTE', 'Acceso a solo sus cuentas, NO maestros, adiciona, NO ELIMINA, Reporte estado de cuenta y producción')
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

-- 3. Add id_rol to usuarios table if it doesn't exist
-- We use a stored procedure to check if column exists to avoid errors on re-run or just run ALTER and ignore error
SET @dbname = DATABASE();
SET @tablename = 'usuarios';
SET @columnname = 'id_rol';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  'ALTER TABLE usuarios ADD COLUMN id_rol INT NULL AFTER password;'
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add foreign key if not exists (similar logic or just try add)
-- For simplicity, we assume it might fail if exists, but in a script we'd check constraint_name.
-- Here we just run it, if it fails it fails (or we wrap in block).
-- Let's try to be safe.
SET @constraintname = 'fk_usuarios_roles';
SET @preparedStatementFK = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (constraint_name = @constraintname)
  ) > 0,
  'SELECT 1',
  'ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_roles FOREIGN KEY (id_rol) REFERENCES roles(idRol);'
));
PREPARE addFK FROM @preparedStatementFK;
EXECUTE addFK;
DEALLOCATE PREPARE addFK;


-- Add id_ejecutivo column to usuarios and FK to ejecutivos (if not exists)
SET @dbname = DATABASE();
SET @tablename = 'usuarios';
SET @columnname = 'id_ejecutivo';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  'ALTER TABLE usuarios ADD COLUMN id_ejecutivo INT NULL AFTER id_rol;'
));
PREPARE alterIfNotExists2 FROM @preparedStatement;
EXECUTE alterIfNotExists2;
DEALLOCATE PREPARE alterIfNotExists2;

-- Add FK constraint to ejecutivos.idEjecutivo if not exists
SET @constraintname2 = 'fk_usuarios_ejecutivos';
SET @preparedStatementFK2 = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (constraint_name = @constraintname2)
  ) > 0,
  'SELECT 1',
  'ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_ejecutivos FOREIGN KEY (id_ejecutivo) REFERENCES ejecutivos(idEjecutivo);'
));
PREPARE addFK2 FROM @preparedStatementFK2;
EXECUTE addFK2;
DEALLOCATE PREPARE addFK2;


-- 4. Update sp_login_usuario to return role info
DROP PROCEDURE IF EXISTS sp_login_usuario;
DELIMITER $$
CREATE PROCEDURE sp_login_usuario(IN p_username VARCHAR(50))
BEGIN
    SELECT u.id, u.username, u.password, u.id_rol, r.nombre as rol_nombre
    FROM usuarios u
    LEFT JOIN roles r ON u.id_rol = r.idRol
    WHERE u.username = p_username
    LIMIT 1;
END$$
DELIMITER ;

-- 5. Update sp_listar_usuarios to return role info
DROP PROCEDURE IF EXISTS sp_listar_usuarios;
DELIMITER $$
CREATE PROCEDURE sp_listar_usuarios()
BEGIN
    SELECT u.id, u.username, u.nombre, u.estado, u.id_rol, r.nombre as rol
    FROM usuarios u
    LEFT JOIN roles r ON u.id_rol = r.idRol
    ORDER BY u.username ASC;
END$$
DELIMITER ;

-- 6. Procedure to update user role
DROP PROCEDURE IF EXISTS sp_actualizar_usuario_rol;
DELIMITER $$
CREATE PROCEDURE sp_actualizar_usuario_rol(
    IN p_id INT,
    IN p_id_rol INT
)
BEGIN
    UPDATE usuarios SET id_rol = p_id_rol WHERE id = p_id;
END$$
DELIMITER ;

-- 7. Procedure to list roles
DROP PROCEDURE IF EXISTS sp_listar_roles;
DELIMITER $$
CREATE PROCEDURE sp_listar_roles()
BEGIN
    SELECT idRol, nombre, descripcion FROM roles ORDER BY idRol;
END$$
DELIMITER ;


-- =====================================================
-- STORED PROCEDURE PARA CARGA MASIVA DE SOAT
-- =====================================================
DROP PROCEDURE IF EXISTS sp_insert_poliza_soat_masivo;
DELIMITER $$
CREATE PROCEDURE sp_insert_poliza_soat_masivo (
    IN p_numero_documento VARCHAR(20),
    IN p_tipo_doc VARCHAR(10),
    IN p_asegurado VARCHAR(150),
    IN p_cia VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_poliza VARCHAR(50),
    IN p_recibo VARCHAR(50),
    IN p_contrato_nro VARCHAR(50),
    IN p_nro VARCHAR(50),
    IN p_moneda VARCHAR(20),
    IN p_fecha_emision DATE,
    IN p_vig_desde DATE,
    IN p_vig_hasta DATE,
    IN p_ultimo_dia_pago DATE,
    IN p_fecha_vencimiento DATE,
    IN p_tipo_vigencia VARCHAR(50),
    IN p_endosatario VARCHAR(150),
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
    IN p_ramos_producto VARCHAR(120),
    IN p_estado VARCHAR(20),
    IN p_pdf_path VARCHAR(255),
    IN p_usuario_registro VARCHAR(50),
    IN p_datos_vehiculo JSON,
    IN p_codigo_agente VARCHAR(50)
)
BEGIN
    DECLARE v_cliente_id INT;
    DECLARE v_exists INT DEFAULT 0;
    DECLARE v_msg VARCHAR(255);
    DECLARE v_key VARCHAR(50);
    DECLARE v_poliza_id INT;

    -- Validar que el cliente existe
    SELECT idCliente INTO v_cliente_id
    FROM clientes
    WHERE numero_documento = p_numero_documento
    LIMIT 1;

    IF v_cliente_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cliente no existe';
    END IF;

    -- Normalizar clave de duplicado
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
          AND (contrato_nro = v_key OR recibo = v_key);

        IF v_exists > 0 THEN
            SET v_msg = CONCAT('Póliza ya existe: ', p_poliza);
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    END IF;

    -- Insertar póliza
    INSERT INTO polizas (
        cliente_id, asegurado, cia, ramo,
        poliza, recibo, contrato_nro, nro,
        moneda, fecha_emision, vig_desde, vig_hasta, ultimo_dia_pago,
        fecha_vencimiento, tipo_vigencia, endosatario, forma_pago,
        sub_agente, ejecutivo, tipo_doc,
        asegurada, motivo, prima_comercial, prima_neta, prima_comercial_igv, prima_total,
        porc_compania, imp_compania, porc_subagente, imp_subagente,
        ramos_producto, estado, usuario_registro, datos_vehiculo, codigo_agente
    ) VALUES (
        v_cliente_id, p_asegurado, p_cia, p_ramo,
        p_poliza, p_recibo, p_contrato_nro, p_nro,
        p_moneda, p_fecha_emision, p_vig_desde, p_vig_hasta, p_ultimo_dia_pago,
        p_fecha_vencimiento, p_tipo_vigencia, p_endosatario, p_forma_pago,
        p_sub_agente, p_ejecutivo, p_tipo_doc,
        p_asegurada, p_motivo, p_prima_comercial, p_prima_neta, p_prima_comercial_igv, p_prima_total,
        p_porc_compania, p_imp_compania, p_porc_subagente, p_imp_subagente,
        p_ramos_producto, p_estado, p_usuario_registro, p_datos_vehiculo, p_codigo_agente
    );

    SET v_poliza_id = LAST_INSERT_ID();

    -- Insertar archivo si existe
    IF p_pdf_path IS NOT NULL AND p_pdf_path <> '' THEN
        INSERT INTO poliza_archivos (poliza_id, numero_poliza, ruta_archivo, nombre_original, ramo, producto, usuario, compania)
        VALUES (v_poliza_id, p_poliza, p_pdf_path, SUBSTRING_INDEX(p_pdf_path, '/', -1), p_ramo, p_ramos_producto, p_usuario_registro, p_cia);
    END IF;

END$$
DELIMITER ;


-- =========================================================
-- TABLA: AGENTES/VENDEDORES
-- =========================================================
CREATE TABLE IF NOT EXISTS agentes (
    id INT NOT NULL AUTO_INCREMENT,
    codigo_agente VARCHAR(50) NOT NULL,
    nombre_vendedor VARCHAR(255) NOT NULL,
    estado ENUM('ACTIVO','INACTIVO') NOT NULL DEFAULT 'ACTIVO',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_agentes_codigo (codigo_agente),
    KEY idx_agentes_estado (estado),
    KEY idx_agentes_nombre (nombre_vendedor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- =========================================================
-- PROCEDIMIENTOS: AGENTES/VENDEDORES
-- =========================================================

DROP PROCEDURE IF EXISTS sp_listar_agentes;
DELIMITER $$
CREATE PROCEDURE sp_listar_agentes()
BEGIN
    SELECT id, codigo_agente, nombre_vendedor, estado
    FROM agentes
    ORDER BY nombre_vendedor ASC;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_insertar_agente;
DELIMITER $$
CREATE PROCEDURE sp_insertar_agente(
    IN p_codigo_agente VARCHAR(50),
    IN p_nombre_vendedor VARCHAR(255),
    OUT p_new_id INT
)
BEGIN
    IF TRIM(p_codigo_agente) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El código de agente no puede estar vacío';
    END IF;

    IF TRIM(p_nombre_vendedor) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El nombre del vendedor no puede estar vacío';
    END IF;

    INSERT INTO agentes (codigo_agente, nombre_vendedor)
    VALUES (TRIM(p_codigo_agente), TRIM(p_nombre_vendedor))
    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id);

    SET p_new_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_delete_agente;
DELIMITER $$
CREATE PROCEDURE sp_delete_agente(
    IN p_id INT,
    OUT p_deleted INT
)
BEGIN
    DELETE FROM agentes WHERE id = p_id;
    SET p_deleted = ROW_COUNT();
END$$
DELIMITER ;


-- ========================================
-- MIGRACIONES Y ALTERACIONES DE TABLAS
-- ========================================

-- Agregar columna datos_vehiculo si no existe
SET @dbname = DATABASE();
SET @tablename = 'polizas';
SET @columnname = 'datos_vehiculo';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' JSON NULL COMMENT ''Datos del vehículo para pólizas SOAT'' AFTER ramos_producto;')
));
PREPARE alterStatement FROM @preparedStatement;
EXECUTE alterStatement;
DEALLOCATE PREPARE alterStatement;

-- Agregar columna codigo_agente si no existe
SET @dbname = DATABASE();
SET @tablename = 'polizas';
SET @columnname = 'codigo_agente';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (table_name = @tablename)
      AND (table_schema = @dbname)
      AND (column_name = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' VARCHAR(50) NULL COMMENT ''Código de agente/vendedor'' AFTER datos_vehiculo;')
));
PREPARE alterStatement FROM @preparedStatement;
EXECUTE alterStatement;
DEALLOCATE PREPARE alterStatement;


