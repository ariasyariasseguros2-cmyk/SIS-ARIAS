-- Patch rapido: evitar recibos duplicados por cliente
-- Requiere @SIS_KEY configurada en la sesion

USE ariasyariaspe_bd_sisnet; -- nombre de la bd en produccion

-- 1) Crear indice unico si no existe
SET @idx_name := 'uk_polizas_cliente_recibo';
SET @idx_exists := (
    SELECT COUNT(*)
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'polizas'
      AND index_name = @idx_name
);

SET @sql := IF(
    @idx_exists = 0,
    'CREATE UNIQUE INDEX uk_polizas_cliente_recibo ON polizas (cliente_id, recibo)',
    'SELECT "Indice ya existe"'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2) Reemplazar SP con validacion de duplicado por recibo
DROP PROCEDURE IF EXISTS sp_insert_poliza_por_numero;
DELIMITER $$
CREATE PROCEDURE sp_insert_poliza_por_numero (
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

    IN p_sub_agente VARCHAR(150),
    IN p_ejecutivo VARCHAR(250),

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
    IN p_usuario_registro VARCHAR(100)
)
BEGIN
    DECLARE v_cliente_id INT;
    DECLARE v_exists INT DEFAULT 0;
    DECLARE v_msg VARCHAR(255);
    DECLARE v_key VARCHAR(50);
    DECLARE v_recibo_key VARCHAR(50);
    DECLARE v_poliza_id INT;
    DECLARE v_usuario_registro_nombre VARCHAR(100);

    SELECT idCliente INTO v_cliente_id
    FROM clientes
    WHERE (
            CAST(AES_DECRYPT(FROM_BASE64(numero_documento), @SIS_KEY) AS CHAR) COLLATE utf8mb4_0900_ai_ci = p_numero_documento COLLATE utf8mb4_0900_ai_ci
         OR CAST(AES_DECRYPT(numero_documento, @SIS_KEY) AS CHAR)            COLLATE utf8mb4_0900_ai_ci = p_numero_documento COLLATE utf8mb4_0900_ai_ci
         OR numero_documento COLLATE utf8mb4_0900_ai_ci = p_numero_documento COLLATE utf8mb4_0900_ai_ci
    )
      AND activo = 1
    LIMIT 1;

    IF v_cliente_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cliente no existe';
    END IF;

    -- Validar duplicado por recibo (por cliente)
    SET v_recibo_key = NULLIF(TRIM(IFNULL(p_recibo, '')), '');
    IF v_recibo_key IS NOT NULL THEN
        SELECT COUNT(*) INTO v_exists
        FROM polizas
        WHERE cliente_id = v_cliente_id
          AND TRIM(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR),
                CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR),
                recibo
              )) COLLATE utf8mb4_0900_ai_ci = v_recibo_key COLLATE utf8mb4_0900_ai_ci;

        IF v_exists > 0 THEN
            SET v_msg = CONCAT('El recibo ya existe para este cliente: ', v_recibo_key);
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    END IF;

    -- Normalizar clave de duplicado: primero contrato_nro, si no, recibo
    SET v_key = NULLIF(TRIM(IFNULL(p_contrato_nro, '')), '');
    IF v_key IS NULL THEN
        SET v_key = NULLIF(TRIM(IFNULL(p_recibo, '')), '');
    END IF;

    -- Validacion de duplicados: poliza + (contrato_nro|recibo), acotado por cliente
    IF COALESCE(p_poliza, '') <> '' AND COALESCE(v_key, '') <> '' THEN
        SELECT COUNT(*) INTO v_exists
        FROM polizas
        WHERE cliente_id = v_cliente_id
          AND TRIM(COALESCE(
                CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                poliza
              )) COLLATE utf8mb4_0900_ai_ci = TRIM(p_poliza) COLLATE utf8mb4_0900_ai_ci
          AND (
               TRIM(COALESCE(
                   CAST(AES_DECRYPT(FROM_BASE64(contrato_nro), @SIS_KEY) AS CHAR),
                   CAST(AES_DECRYPT(contrato_nro, @SIS_KEY) AS CHAR),
                   contrato_nro
               )) COLLATE utf8mb4_0900_ai_ci = v_key COLLATE utf8mb4_0900_ai_ci
            OR TRIM(COALESCE(
                   CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR),
                   CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR),
                   recibo
               )) COLLATE utf8mb4_0900_ai_ci = v_key COLLATE utf8mb4_0900_ai_ci
          );

        IF v_exists > 0 THEN
            SET v_msg = CONCAT('Poliza ya existe con mismo numero y contrato/recibo: ', p_poliza, ' / ', v_key);
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;
    END IF;

    SET v_usuario_registro_nombre = NULL;
    IF p_usuario_registro IS NOT NULL AND TRIM(p_usuario_registro) <> '' THEN
        SELECT COALESCE(NULLIF(TRIM(nombre), ''), username)
        INTO v_usuario_registro_nombre
        FROM usuarios
        WHERE username COLLATE utf8mb4_0900_ai_ci = p_usuario_registro COLLATE utf8mb4_0900_ai_ci
        LIMIT 1;
    END IF;
    IF v_usuario_registro_nombre IS NULL OR v_usuario_registro_nombre = '' THEN
        SET v_usuario_registro_nombre = p_usuario_registro;
    END IF;

    INSERT INTO polizas (
        cliente_id, asegurado, cia, ramo,
        poliza, recibo, contrato_nro, nro,
        moneda, fecha_emision, vig_desde, vig_hasta, ultimo_dia_pago, fecha_vencimiento, tipo_vigencia, endosatario, forma_pago,
        sub_agente, ejecutivo, tipo_doc,
        asegurada, motivo, prima_comercial, prima_neta, prima_comercial_igv, prima_total,
        porc_compania, imp_compania, porc_subagente, imp_subagente,
        ramos_producto, estado, usuario_registro, creado_en
    ) VALUES (
        v_cliente_id, p_asegurado, p_cia, p_ramo,
        p_poliza, p_recibo, p_contrato_nro, p_nro,
        p_moneda, p_fecha_emision, p_vig_desde, p_vig_hasta, p_ultimo_dia_pago, p_fecha_vencimiento, p_tipo_vigencia, p_endosatario, p_forma_pago,
        p_sub_agente, p_ejecutivo, p_tipo_doc,
        p_asegurada, p_motivo, p_prima_comercial, p_prima_neta, p_prima_comercial_igv, p_prima_total,
        p_porc_compania, p_imp_compania, p_porc_subagente, p_imp_subagente,
        p_ramos_producto, p_estado, v_usuario_registro_nombre, CONVERT_TZ(UTC_TIMESTAMP(), '+00:00', '-05:00')
    );

    SET v_poliza_id = LAST_INSERT_ID();

    IF p_pdf_path IS NOT NULL AND p_pdf_path <> '' THEN
        INSERT INTO poliza_archivos (poliza_id, numero_poliza, ruta_archivo, nombre_original, ramo, producto, usuario, compania)
        VALUES (v_poliza_id, p_poliza, p_pdf_path, SUBSTRING_INDEX(p_pdf_path, '/', -1), p_ramo, p_ramos_producto, v_usuario_registro_nombre, p_cia);
    END IF;
END$$
DELIMITER ;

