-- Fix de produccion para edicion de clientes (evita error 500 por UNIQUE en numero_documento)
-- Ejecutar en la base de datos de produccion.

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_update_cliente$$

CREATE PROCEDURE sp_update_cliente (
	IN p_idCliente INT,
	IN p_razon_social VARCHAR(255),
	IN p_tipo_documento VARCHAR(20),
	IN p_numero_documento VARCHAR(100),
	IN p_telefono VARCHAR(100),
	IN p_celular VARCHAR(20),
	IN p_telefono_sec VARCHAR(20),
	IN p_subagente VARCHAR(250),
	IN p_idProductor INT,
	IN p_email VARCHAR(255),
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
	DECLARE v_current_num_raw VARCHAR(100);
	DECLARE v_current_num_plain VARCHAR(100);
	DECLARE v_new_num_plain VARCHAR(100);
	DECLARE v_exists INT DEFAULT 0;

	SELECT numero_documento
	INTO v_current_num_raw
	FROM clientes
	WHERE idCliente = p_idCliente
	LIMIT 1;

	IF v_current_num_raw IS NULL THEN
		SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cliente no encontrado';
	END IF;

	SET v_current_num_plain = COALESCE(
		CAST(AES_DECRYPT(FROM_BASE64(v_current_num_raw), @SIS_KEY) AS CHAR(100)),
		CAST(AES_DECRYPT(v_current_num_raw, @SIS_KEY) AS CHAR(100)),
		v_current_num_raw
	);

	SET v_new_num_plain = NULLIF(TRIM(p_numero_documento), '');

	IF v_new_num_plain IS NOT NULL AND v_new_num_plain <> v_current_num_plain THEN
		SELECT COUNT(*)
		INTO v_exists
		FROM clientes c
		WHERE c.idCliente <> p_idCliente
		  AND COALESCE(
				CAST(AES_DECRYPT(FROM_BASE64(c.numero_documento), @SIS_KEY) AS CHAR(100)),
				CAST(AES_DECRYPT(c.numero_documento, @SIS_KEY) AS CHAR(100)),
				c.numero_documento
			  ) = v_new_num_plain;

		IF v_exists > 0 THEN
			SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El numero_documento ya existe';
		END IF;
	END IF;

	UPDATE clientes
	SET razon_social = CASE
						  WHEN p_razon_social IS NULL OR TRIM(p_razon_social) = '' THEN razon_social
						  ELSE TO_BASE64(AES_ENCRYPT(p_razon_social, @SIS_KEY))
					   END,
		tipo_documento = p_tipo_documento,
		numero_documento = CASE
							  WHEN v_new_num_plain IS NULL OR v_new_num_plain = v_current_num_plain THEN numero_documento
							  ELSE TO_BASE64(AES_ENCRYPT(v_new_num_plain, @SIS_KEY))
						   END,
		telefono = CASE
					  WHEN p_telefono IS NULL OR TRIM(p_telefono) = '' THEN telefono
					  ELSE TO_BASE64(AES_ENCRYPT(p_telefono, @SIS_KEY))
				   END,
		celular = p_celular,
		telefono_sec = p_telefono_sec,
		subagente = p_subagente,
		idProductor = p_idProductor,
		email = CASE
				   WHEN p_email IS NULL OR TRIM(p_email) = '' THEN email
				   ELSE TO_BASE64(AES_ENCRYPT(p_email, @SIS_KEY))
				END,
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

