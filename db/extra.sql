-- Tabla siniestros
CREATE TABLE IF NOT EXISTS siniestros (
                                          id INT AUTO_INCREMENT PRIMARY KEY,
                                          contratante VARCHAR(150) NULL COMMENT 'Nombre del contratante',
    poliza VARCHAR(50) NULL COMMENT 'Número de póliza',
    cia VARCHAR(100) NULL COMMENT 'Compañía aseguradora',
    fec_stro DATE NULL COMMENT 'Fecha del siniestro',
    causa VARCHAR(200) NULL COMMENT 'Causa del siniestro',
    siniestro_no VARCHAR(50) NULL COMMENT 'Número de siniestro',
    provision DECIMAL(15,2) NULL COMMENT 'Monto de provisión',
    estado VARCHAR(50) DEFAULT 'PENDIENTE' COMMENT 'Estado del siniestro',
    ejec VARCHAR(100) NULL COMMENT 'Ejecutivo responsable',
    ramo VARCHAR(120) NULL COMMENT 'Ramo del seguro',
    placa VARCHAR(20) NULL COMMENT 'Placa del vehículo (si aplica)',
    fec_gestion DATE NULL COMMENT 'Fecha de gestión',
    prox_gestion DATE NULL COMMENT 'Próxima fecha de gestión',

    -- Auditoría
    usuario_registro VARCHAR(50) NULL,
    usuario_edicion VARCHAR(50) NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,

    -- Índices
    INDEX idx_poliza (poliza),
    INDEX idx_contratante (contratante),
    INDEX idx_estado (estado),
    INDEX idx_fec_stro (fec_stro)
    );

-- SP: Insertar siniestro
DELIMITER $$
CREATE PROCEDURE sp_insert_siniestro(
    IN p_contratante VARCHAR(150),
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_fec_stro DATE,
    IN p_causa VARCHAR(200),
    IN p_siniestro_no VARCHAR(50),
    IN p_provision DECIMAL(15,2),
    IN p_estado VARCHAR(50),
    IN p_ejec VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_placa VARCHAR(20),
    IN p_fec_gestion DATE,
    IN p_prox_gestion DATE,
    IN p_usuario_registro VARCHAR(50)
)
BEGIN
INSERT INTO siniestros (
    contratante, poliza, cia, fec_stro, causa, siniestro_no,
    provision, estado, ejec, ramo, placa, fec_gestion, prox_gestion,
    usuario_registro
) VALUES (
             p_contratante, p_poliza, p_cia, p_fec_stro, p_causa, p_siniestro_no,
             p_provision, p_estado, p_ejec, p_ramo, p_placa, p_fec_gestion, p_prox_gestion,
             p_usuario_registro
         );

SELECT LAST_INSERT_ID() AS id;
END$$
DELIMITER ;

-- SP: Listar todos los siniestros
DELIMITER $$
CREATE PROCEDURE sp_list_siniestros()
BEGIN
SELECT
    id,
    contratante,
    poliza,
    cia,
    DATE_FORMAT(fec_stro, '%d/%m/%Y') AS fec_stro,
    causa,
    siniestro_no,
    FORMAT(provision, 2) AS provision,
    estado,
    ejec,
    ramo,
    placa,
    DATE_FORMAT(fec_gestion, '%d/%m/%Y') AS fec_gestion,
    DATE_FORMAT(prox_gestion, '%d/%m/%Y') AS prox_gestion,
    usuario_registro,
    usuario_edicion
FROM siniestros
ORDER BY fec_stro DESC;
END$$
DELIMITER ;

-- SP: Obtener siniestro por ID
DELIMITER $$
CREATE PROCEDURE sp_get_siniestro_by_id(IN p_id INT)
BEGIN
SELECT *
FROM siniestros
WHERE id = p_id
    LIMIT 1;
END$$
DELIMITER ;

-- SP: Listar siniestros por póliza
DELIMITER $$
CREATE PROCEDURE sp_list_siniestros_por_poliza(IN p_poliza VARCHAR(50))
BEGIN
SELECT
    id,
    contratante,
    cia,
    DATE_FORMAT(fec_stro, '%d/%m/%Y') AS fec_stro,
    causa,
    siniestro_no,
    FORMAT(provision, 2) AS provision,
    estado,
    placa
FROM siniestros
WHERE poliza = p_poliza
ORDER BY fec_stro DESC;
END$$
DELIMITER ;

-- SP: Actualizar siniestro
DELIMITER $$
CREATE PROCEDURE sp_update_siniestro(
    IN p_id INT,
    IN p_contratante VARCHAR(150),
    IN p_poliza VARCHAR(50),
    IN p_cia VARCHAR(100),
    IN p_fec_stro DATE,
    IN p_causa VARCHAR(200),
    IN p_siniestro_no VARCHAR(50),
    IN p_provision DECIMAL(15,2),
    IN p_estado VARCHAR(50),
    IN p_ejec VARCHAR(100),
    IN p_ramo VARCHAR(120),
    IN p_placa VARCHAR(20),
    IN p_fec_gestion DATE,
    IN p_prox_gestion DATE,
    IN p_usuario_edicion VARCHAR(50)
)
BEGIN
UPDATE siniestros
SET
    contratante = p_contratante,
    poliza = p_poliza,
    cia = p_cia,
    fec_stro = p_fec_stro,
    causa = p_causa,
    siniestro_no = p_siniestro_no,
    provision = p_provision,
    estado = p_estado,
    ejec = p_ejec,
    ramo = p_ramo,
    placa = p_placa,
    fec_gestion = p_fec_gestion,
    prox_gestion = p_prox_gestion,
    usuario_edicion = p_usuario_edicion
WHERE id = p_id;

SELECT ROW_COUNT() AS affected_rows;
END$$
DELIMITER ;

-- SP: Eliminar siniestro (físico)
DELIMITER $$
CREATE PROCEDURE sp_delete_siniestro(IN p_id INT)
BEGIN
DELETE FROM siniestros
WHERE id = p_id;

SELECT ROW_COUNT() AS affected_rows;
END$$
DELIMITER ;

-- SP: Buscar siniestros
DELIMITER $$
CREATE PROCEDURE sp_buscar_siniestros(IN p_texto VARCHAR(150))
BEGIN
SELECT
    id,
    contratante,
    poliza,
    cia,
    DATE_FORMAT(fec_stro, '%d/%m/%Y') AS fec_stro,
    siniestro_no,
    FORMAT(provision, 2) AS provision,
    estado,
    ramo
FROM siniestros
WHERE contratante LIKE CONCAT('%', p_texto, '%')
   OR poliza LIKE CONCAT('%', p_texto, '%')
   OR siniestro_no LIKE CONCAT('%', p_texto, '%')
   OR placa LIKE CONCAT('%', p_texto, '%')
ORDER BY fec_stro DESC;
END$$
DELIMITER ;
sp_update_siniestro