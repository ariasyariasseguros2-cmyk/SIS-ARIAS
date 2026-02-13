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
