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

-- Tabla clientes (ajustada del ejemplo del usuario)
CREATE TABLE IF NOT EXISTS clientes (
    idCliente INT AUTO_INCREMENT PRIMARY KEY,
    razon_social VARCHAR(150) NOT NULL,
    tipo_documento ENUM('DNI', 'RUC', 'CE', 'PAS') NOT NULL,
    numero_documento VARCHAR(20) NOT NULL UNIQUE,
    telefono VARCHAR(20),
    subagente VARCHAR(100),
    email VARCHAR(150),
    direccion VARCHAR(200),
    estado VARCHAR(20) DEFAULT 'Vigente',
    tipo_persona TINYINT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP
);

DELIMITER $$
CREATE PROCEDURE sp_insert_cliente (
    IN p_razon_social VARCHAR(150),
    IN p_tipo_documento VARCHAR(10),
    IN p_numero_documento VARCHAR(20),
    IN p_telefono VARCHAR(20),
    IN p_subagente VARCHAR(100),
    IN p_email VARCHAR(150),
    IN p_direccion VARCHAR(200),
    IN p_estado VARCHAR(20),
    IN p_tipo_persona TINYINT
)
BEGIN
    INSERT INTO clientes (
        razon_social, tipo_documento, numero_documento,
        telefono, subagente, email, direccion,
        estado, tipo_persona
    ) VALUES (
        p_razon_social, p_tipo_documento, p_numero_documento,
        p_telefono, p_subagente, p_email, p_direccion,
        p_estado, p_tipo_persona
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

    porc_compania DECIMAL(7,4) NULL,
    imp_compania DECIMAL(15,2) NULL,
    porc_subagente DECIMAL(7,4) NULL,
    imp_subagente DECIMAL(15,2) NULL,

    -- motivo VARCHAR(200) NULL,          -- ELIMINADO
    ramos_producto VARCHAR(120) NULL,

    estado VARCHAR(20) DEFAULT 'PENDIENTE',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (cliente_id) REFERENCES clientes(idCliente)
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
    IN p_forma_pago VARCHAR(30),

    IN p_sub_agente VARCHAR(100),
    IN p_ejecutivo VARCHAR(100),

    IN p_asegurada VARCHAR(150),
    IN p_motivo VARCHAR(200),
    IN p_prima_comercial DECIMAL(15,2),
    IN p_prima_neta DECIMAL(15,2),
    IN p_prima_comercial_igv DECIMAL(15,2),
    IN p_prima_total DECIMAL(15,2),

    IN p_porc_compania DECIMAL(7,4),
    IN p_imp_compania DECIMAL(15,2),
    IN p_porc_subagente DECIMAL(7,4),
    IN p_imp_subagente DECIMAL(15,2),

    -- IN p_motivo VARCHAR(200),          -- ELIMINADO
    IN p_ramos_producto VARCHAR(120),
    IN p_estado VARCHAR(20)
)
BEGIN
    DECLARE v_cliente_id INT;

    SELECT idCliente INTO v_cliente_id
    FROM clientes
    WHERE numero_documento = p_numero_documento
    LIMIT 1;

    IF v_cliente_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cliente no existe';
    END IF;

    INSERT INTO polizas (
        cliente_id, asegurado, cia, ramo,
        poliza, recibo, contrato_nro, nro,
        moneda, fecha_emision, vig_desde, vig_hasta, ultimo_dia_pago, forma_pago,
        sub_agente, ejecutivo, tipo_doc,
        asegurada, motivo, prima_comercial, prima_neta, prima_comercial_igv, prima_total,
        porc_compania, imp_compania, porc_subagente, imp_subagente,
        ramos_producto, estado
    ) VALUES (
        v_cliente_id, p_asegurado, p_cia, p_ramo,
        p_poliza, p_recibo, p_contrato_nro, p_nro,
        p_moneda, p_fecha_emision, p_vig_desde, p_vig_hasta, p_ultimo_dia_pago, p_forma_pago,
        p_sub_agente, p_ejecutivo, p_tipo_doc,
        p_asegurada, p_motivo, p_prima_comercial, p_prima_neta, p_prima_comercial_igv, p_prima_total,
        p_porc_compania, p_imp_compania, p_porc_subagente, p_imp_subagente,
        p_ramos_producto, p_estado
    );
END$$
DELIMITER ;

-- Listado de pólizas por cliente (mantiene columnas usadas en la vista)
DELIMITER $$
CREATE PROCEDURE sp_list_polizas_por_numero(IN p_numero_documento VARCHAR(20))
BEGIN
    SELECT 
        c.razon_social AS contratante,
        p.asegurado,
        p.cia,
        p.ramo,
        p.ramos_producto AS producto,
        p.poliza,
        p.nro,
        p.moneda,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
        p.sub_agente,
        p.asegurada
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE c.numero_documento = p_numero_documento
    ORDER BY p.creado_en DESC;
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
        c.razon_social AS contratante,
        p.asegurado,
        p.cia,
        p.ramo,
        p.ramos_producto AS producto,
        p.poliza,
        p.nro,
        p.moneda,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
        p.sub_agente,
        p.asegurada
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
        p.ejecutivo AS Ejecutivo,          -- corregido: antes p.ejecutivos
        p.poliza,
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
        p.ejecutivo AS ejecutivo,         
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
    moneda VARCHAR(10) DEFAULT 'S/.',
    importe DECIMAL(15,2) NULL,
    fecha_pago DATE NULL,
    factura VARCHAR(50) NULL,
    observacion VARCHAR(255) NULL,
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