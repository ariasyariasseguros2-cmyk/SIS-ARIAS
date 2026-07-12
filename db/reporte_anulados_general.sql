-- ============================================================
-- Reporte de anulados genera, sp.
-- ============================================================

USE ariasyariaspe_bd_sisnet;

DELIMITER $$
DROP PROCEDURE IF EXISTS sp_reporte_anulados_general$$
CREATE PROCEDURE sp_reporte_anulados_general(
    IN p_search VARCHAR(150),
    IN p_desde  DATE,
    IN p_hasta  DATE
)
BEGIN
    DECLARE v_search VARCHAR(150);
    SET v_search = NULLIF(TRIM(COALESCE(p_search, '')), '');

    SELECT * FROM (
        -- Nivel 1: la fila de polizas (poliza/recibo/prima) anulada,
        -- o vigente pero con cuotas anuladas colgando de ella.
        SELECT
            'POLIZA' AS tipo,
            p.idPoliza AS poliza_id,
            NULL AS poliza_padre_id,
            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR), CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR), p.poliza) AS poliza,
            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.recibo), @SIS_KEY) AS CHAR), CAST(AES_DECRYPT(p.recibo, @SIS_KEY) AS CHAR), p.recibo) AS recibo,
            CASE WHEN p.anulado = 1 THEN 'POLIZA ANULADA'
                 WHEN p.prima_anulada = 1 THEN 'PRIMA ANULADA'
                 ELSE 'CON CUOTAS ANULADAS' END AS tipo_anulacion,
            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR), CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR), c.razon_social) AS contratante,
            p.cia AS compania,
            p.ramo,
            p.moneda,
            p.prima_total AS importe,
            pa.motivo,
            COALESCE(pa.usuario, p.usuario_edicion) AS usuario,
            pa.fecha_anulacion,
            (SELECT COUNT(*) FROM cuotas q1 WHERE q1.poliza_id = p.idPoliza AND q1.activo = 0) AS cuotas_anuladas_count
        FROM polizas p
        INNER JOIN clientes c ON c.idCliente = p.cliente_id
        LEFT JOIN (
            SELECT pa1.poliza_id, pa1.motivo, pa1.usuario, pa1.fecha_anulacion
            FROM poliza_anulaciones pa1
            INNER JOIN (
                SELECT poliza_id, MAX(idAnulacion) AS max_id
                FROM poliza_anulaciones
                GROUP BY poliza_id
            ) ultima ON ultima.poliza_id = pa1.poliza_id AND ultima.max_id = pa1.idAnulacion
        ) pa ON pa.poliza_id = p.idPoliza
        WHERE (
                p.anulado = 1
             OR p.prima_anulada = 1
             OR EXISTS (SELECT 1 FROM cuotas q0 WHERE q0.poliza_id = p.idPoliza AND q0.activo = 0)
              )

        UNION ALL

        -- Nivel 2: cuotas anuladas, colgando de su poliza/recibo (poliza_padre_id).
        SELECT
            'CUOTA' AS tipo,
            q.idCuota AS poliza_id,
            q.poliza_id AS poliza_padre_id,
            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(p.poliza), @SIS_KEY) AS CHAR), CAST(AES_DECRYPT(p.poliza, @SIS_KEY) AS CHAR), p.poliza) AS poliza,
            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(q.cupon), @SIS_KEY) AS CHAR), CAST(AES_DECRYPT(q.cupon, @SIS_KEY) AS CHAR), q.cupon) AS recibo,
            'CUOTA ANULADA' AS tipo_anulacion,
            COALESCE(CAST(AES_DECRYPT(FROM_BASE64(c.razon_social), @SIS_KEY) AS CHAR), CAST(AES_DECRYPT(c.razon_social, @SIS_KEY) AS CHAR), c.razon_social) AS contratante,
            p.cia AS compania,
            p.ramo,
            q.moneda,
            q.importe,
            q.motivo_anulacion AS motivo,
            q.usuario_anulacion AS usuario,
            q.fecha_anulacion,
            NULL AS cuotas_anuladas_count
        FROM cuotas q
        LEFT JOIN polizas p ON p.idPoliza = q.poliza_id
        LEFT JOIN clientes c ON c.idCliente = p.cliente_id
        WHERE q.activo = 0
    ) t
    WHERE (v_search IS NULL
        OR t.poliza LIKE CONCAT('%', v_search, '%')
        OR t.recibo LIKE CONCAT('%', v_search, '%')
        OR t.contratante LIKE CONCAT('%', v_search, '%'))
      AND (
            (p_desde IS NULL AND p_hasta IS NULL)
         OR (t.fecha_anulacion IS NOT NULL
             AND t.fecha_anulacion >= COALESCE(p_desde, '1900-01-01')
             AND t.fecha_anulacion <  DATE_ADD(COALESCE(p_hasta, '2900-12-31'), INTERVAL 1 DAY))
         OR (t.tipo = 'POLIZA' AND EXISTS (
                SELECT 1 FROM cuotas q3
                WHERE q3.poliza_id = t.poliza_id AND q3.activo = 0
                  AND q3.fecha_anulacion >= COALESCE(p_desde, '1900-01-01')
                  AND q3.fecha_anulacion <  DATE_ADD(COALESCE(p_hasta, '2900-12-31'), INTERVAL 1 DAY)
            ))
          )
    -- Agrupa cada cuota justo debajo de su poliza/recibo padre (arbol).
    ORDER BY COALESCE(t.poliza_padre_id, t.poliza_id), t.tipo DESC, t.fecha_anulacion DESC;
END$$
DELIMITER ;
