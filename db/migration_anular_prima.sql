-- ============================================================
-- MIGRACIÓN: Anulación de Prima específica
-- Aplica solo los cambios necesarios a una BD existente.
-- NO recrea tablas ni borra datos.
-- ============================================================

USE ariasyariaspe_bd_sisnet;
SET @SIS_KEY = 'tu_clave_aqui';

-- ------------------------------------------------------------
-- 1. Nueva columna en polizas
-- ------------------------------------------------------------
ALTER TABLE polizas
    ADD COLUMN prima_anulada TINYINT(1) NOT NULL DEFAULT 0 AFTER anulado;

-- ------------------------------------------------------------
-- 2. SP: sp_anular_prima (nuevo)
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_anular_prima;
DELIMITER $$
CREATE PROCEDURE sp_anular_prima(
    IN p_prima_id   INT,
    IN p_usuario    VARCHAR(100),
    IN p_motivo     VARCHAR(200),
    IN p_fecha      DATE
)
BEGIN
    DECLARE v_usuario_nombre VARCHAR(100);
    DECLARE v_poliza_numero  VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
    DECLARE v_recibo_prima   VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
    DECLARE v_affected       INT DEFAULT 0;

    -- Resolver nombre de usuario
    SET v_usuario_nombre = NULL;
    IF p_usuario IS NOT NULL AND TRIM(p_usuario) <> '' THEN
        SELECT COALESCE(NULLIF(TRIM(nombre), ''), username)
        INTO v_usuario_nombre
        FROM usuarios
        WHERE username = p_usuario
        LIMIT 1;
    END IF;
    IF v_usuario_nombre IS NULL OR v_usuario_nombre = '' THEN
        SET v_usuario_nombre = p_usuario;
    END IF;

    -- Obtener número de póliza y recibo de la prima
    SELECT
        TRIM(COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
            CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
            poliza
        )),
        TRIM(COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
            CAST(AES_DECRYPT(recibo, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
            recibo
        ))
    INTO v_poliza_numero, v_recibo_prima
    FROM polizas
    WHERE idPoliza = p_prima_id
    LIMIT 1;

    -- Marcar prima como anulada (prima_anulada=1, anulado permanece en 0
    -- para que la póliza siga visible en el listado de pólizas activas)
    UPDATE polizas
    SET prima_anulada   = 1,
        estado          = 'ANULADA',
        motivo          = p_motivo,
        usuario_edicion = v_usuario_nombre
    WHERE idPoliza      = p_prima_id
      AND activo        = 1
      AND prima_anulada = 0;

    SET v_affected = ROW_COUNT();

    IF v_affected > 0 THEN
        INSERT INTO poliza_anulaciones (poliza_id, poliza_numero, usuario, motivo, fecha_anulacion)
        VALUES (p_prima_id, v_poliza_numero, v_usuario_nombre, p_motivo, COALESCE(p_fecha, CURDATE()));
    END IF;

    -- Anular cuotas de esta prima filtrando por idCuota (PK) via subquery.
    -- El doble nivel de subquery evita el error de MySQL al UPDATE/SELECT
    -- de la misma tabla, y satisface safe mode sin necesidad de desactivarlo.
    UPDATE cuotas
    SET activo          = 0,
        anular          = 0,
        usuario_edicion = v_usuario_nombre
    WHERE idCuota IN (
        SELECT id FROM (
            SELECT idCuota AS id
            FROM cuotas
            WHERE activo = 1
              AND (
                    poliza_id = p_prima_id
                    OR (
                        v_recibo_prima IS NOT NULL
                        AND TRIM(v_recibo_prima) <> ''
                        AND TRIM(COALESCE(
                                CAST(AES_DECRYPT(FROM_BASE64(cupon), @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                CAST(AES_DECRYPT(cupon, @SIS_KEY) AS CHAR CHARACTER SET utf8mb4),
                                cupon
                            )) COLLATE utf8mb4_0900_ai_ci = (v_recibo_prima COLLATE utf8mb4_0900_ai_ci)
                    )
              )
        ) AS _ids
    );

    SELECT v_affected AS affected_rows;
END$$
DELIMITER ;

-- ------------------------------------------------------------
-- 3. SP: sp_list_primas_por_poliza (agrega prima_anulada al SELECT)
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_list_primas_por_poliza;
DELIMITER $$
CREATE PROCEDURE sp_list_primas_por_poliza(IN p_poliza VARCHAR(50))
BEGIN
    SELECT
        p.idPoliza,
        p.prima_anulada,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
            p.recibo
        ) AS recibo,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
            p.recibo
        ) AS cupon,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
            p.poliza
        ) AS poliza,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
            c.razon_social
        ) AS contratante,
        p.cia AS compania,
        p.ramo,
        p.tipo_doc AS tipo,
        p.prima_comercial,
        p.prima_neta,
        p.prima_comercial_igv,
        p.prima_comercial_igv AS importe,
        p.moneda,
        DATE_FORMAT(p.fecha_vencimiento, '%d/%m/%Y') AS fecha_vencimiento,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(p.nro), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(p.nro, @SIS_KEY) AS CHAR),
            p.nro
        ) AS nro_operacion,
        p.motivo AS motivo
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE (
            CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR) COLLATE utf8mb4_0900_ai_ci = p_poliza COLLATE utf8mb4_0900_ai_ci
         OR CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR)            COLLATE utf8mb4_0900_ai_ci = p_poliza COLLATE utf8mb4_0900_ai_ci
         OR p.poliza COLLATE utf8mb4_0900_ai_ci = p_poliza COLLATE utf8mb4_0900_ai_ci
    )
      AND p.activo = 1 AND p.anulado = 0
    ORDER BY p.creado_en DESC;
END$$
DELIMITER ;

-- ------------------------------------------------------------
-- 4. SP: sp_list_primas_por_cliente_id (agrega prima_anulada al SELECT)
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_list_primas_por_cliente_id;
DELIMITER $$
CREATE PROCEDURE sp_list_primas_por_cliente_id(IN p_cliente_id INT)
BEGIN
    SELECT
        p.idPoliza,
        p.prima_anulada,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR),
            p.recibo
        ) AS recibo,
        p.ejecutivo AS Ejecutivo,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR),
            p.poliza
        ) AS poliza,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR),
            c.razon_social
        ) AS contratante,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(p.asegurado), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(p.asegurado, @SIS_KEY) AS CHAR),
            p.asegurado
        ) AS Asegurado,
        p.cia AS compania,
        p.ramo,
        p.tipo_doc AS tipo,
        p.prima_comercial,
        p.prima_neta,
        p.prima_comercial_igv,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_inicio,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_fin,
        COALESCE(
            CAST(AES_DECRYPT(FROM_BASE64(p.nro), @SIS_KEY) AS CHAR),
            CAST(AES_DECRYPT(p.nro, @SIS_KEY) AS CHAR),
            p.nro
        ) AS nro_operacion,
        p.motivo AS motivo
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    WHERE p.cliente_id = p_cliente_id AND p.activo = 1 AND p.anulado = 0
    ORDER BY p.creado_en DESC;
END$$
DELIMITER ;

-- ------------------------------------------------------------
-- 5. SP: sp_reporte_vencimientos (excluir primas anuladas)
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_reporte_vencimientos;
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
        p.idPoliza,
        p.cia AS compania,
        p.ramo,
        p.ramos_producto AS producto,
        c.tipo_documento,
        COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR), c.numero_documento) AS numero_documento,
        COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR), c.razon_social) AS contratante,
        COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR), p.poliza) AS poliza,
        COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR), p.recibo) AS aviso_cobranza,
        (
            SELECT COALESCE(CAST(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) AS CHAR), q.cupon)
            FROM cuotas q
            WHERE q.poliza_id = p.idPoliza
              AND q.activo = 1
            ORDER BY q.fecha_vencimiento DESC, q.idCuota DESC
            LIMIT 1
        ) AS cupon,
        DATE_FORMAT(p.vig_desde, '%d/%m/%Y') AS vig_desde,
        DATE_FORMAT(p.vig_hasta, '%d/%m/%Y') AS vig_hasta,
        (
            SELECT DATE_FORMAT(MAX(q.fecha_pago), '%d/%m/%Y')
            FROM cuotas q
            WHERE q.poliza_id = p.idPoliza
              AND (
                    (p.recibo IS NULL OR TRIM(p.recibo) = '')
                    OR (q.cupon IS NOT NULL AND TRIM(q.cupon) = TRIM(p.recibo))
                  )
        ) AS fecha_pago,
        (
            SELECT COUNT(*)
            FROM cuotas q
            WHERE q.activo = 1
              AND q.poliza_id = p.idPoliza
        ) AS cuotas_count,
        p.moneda,
        p.prima_neta AS prima_neta,
        p.prima_comercial_igv AS prima_total,
        p.estado
    FROM polizas p
    INNER JOIN clientes c ON c.idCliente = p.cliente_id
    LEFT JOIN usuarios ur ON ur.username = p.usuario_registro OR ur.nombre = p.usuario_registro
    WHERE p.activo = 1 AND p.anulado = 0 AND COALESCE(p.prima_anulada, 0) = 0
    AND (
        p_usuarios IS NULL
        OR p_usuarios = ''
        OR FIND_IN_SET(COALESCE(ur.username, p.usuario_registro), p_usuarios)
        OR FIND_IN_SET(COALESCE(NULLIF(TRIM(ur.nombre), ''), p.usuario_registro), p_usuarios)
    )
    AND (p_estado IS NULL OR p_estado = '' OR p.estado = p_estado)
    AND (
        (p_fecha_desde IS NULL AND p_fecha_hasta IS NULL)
        OR (p.vig_hasta BETWEEN COALESCE(p_fecha_desde, '1900-01-01') AND COALESCE(p_fecha_hasta, '2900-12-31'))
    )
    AND (p_ramo IS NULL OR p_ramo = '' OR FIND_IN_SET(p.ramo, p_ramo))
    ORDER BY p.vig_hasta ASC;
END$$
DELIMITER ;

-- ------------------------------------------------------------
-- Verificación rápida
-- ------------------------------------------------------------
SELECT
    CASE WHEN COUNT(*) > 0 THEN 'OK: columna prima_anulada existe'
         ELSE 'ERROR: columna prima_anulada NO existe'
    END AS check_columna
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME   = 'polizas'
  AND COLUMN_NAME  = 'prima_anulada';

SELECT
    ROUTINE_NAME,
    CASE WHEN ROUTINE_NAME IS NOT NULL THEN 'OK: SP existe' ELSE 'FALTA' END AS estado
FROM information_schema.ROUTINES
WHERE ROUTINE_SCHEMA = DATABASE()
  AND ROUTINE_TYPE   = 'PROCEDURE'
  AND ROUTINE_NAME IN ('sp_anular_prima', 'sp_list_primas_por_poliza', 'sp_list_primas_por_cliente_id', 'sp_reporte_vencimientos')
ORDER BY ROUTINE_NAME;
