-- Módulo Solicitudes (trámites internos / TI)
-- cliente, poliza, para y cc se guardan cifrados con AES_ENCRYPT(...,@SIS_KEY) + TO_BASE64,
-- igual que el resto del sistema (ver db/encrytar.sql). El resto son campos de contexto
-- en texto plano, igual que polizas.cia / polizas.ramo / polizas.sub_agente.

CREATE TABLE IF NOT EXISTS solicitudes (
    idSolicitud INT AUTO_INCREMENT PRIMARY KEY,
    -- numero_ti (p.ej. "0000000001") no se guarda: MySQL no permite que una columna
    -- generada referencie al auto_increment. Se formatea en Python: f"{idSolicitud:010d}".

    -- Flujo / gestión
    tipo_operacion VARCHAR(30) NOT NULL,
    fecha_solicitud DATE NOT NULL,
    ubicacion VARCHAR(20) NOT NULL DEFAULT 'CLIENTE',
    prioridad VARCHAR(10) NOT NULL DEFAULT 'NORMAL',
    medio VARCHAR(20) NOT NULL DEFAULT 'CORREO',
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
    gestor VARCHAR(150) NOT NULL,
    fecha_asignacion_gestor DATE NULL,
    fecha_asignacion_estado DATE NULL,
    fecha_proxima_gestion DATE NULL,

    -- Contexto del trámite (todo opcional, es solo referencia hasta que se emita la póliza real)
    cliente VARCHAR(255) NULL,               -- cifrado
    compania VARCHAR(100) NULL,
    ramo VARCHAR(120) NULL,
    numero_tramite_cia VARCHAR(50) NULL,
    poliza VARCHAR(50) NULL,                 -- cifrado
    subagente VARCHAR(250) NULL,
    ejecutivo VARCHAR(250) NULL,

    -- Correo asociado a la solicitud
    para VARCHAR(1000) NULL,                 -- cifrado
    cc VARCHAR(1000) NULL,                   -- cifrado
    asunto VARCHAR(255) NULL,
    motivo VARCHAR(255) NULL,
    contenido TEXT NULL,

    registrado_por VARCHAR(100) NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activo TINYINT(1) NOT NULL DEFAULT 1
);

CREATE INDEX idx_solicitudes_listado ON solicitudes (activo, estado, fecha_solicitud);
CREATE INDEX idx_solicitudes_gestor ON solicitudes (gestor);
CREATE INDEX idx_solicitudes_proxima_gestion ON solicitudes (fecha_proxima_gestion);

CREATE TABLE IF NOT EXISTS solicitud_archivos (
    idArchivo INT AUTO_INCREMENT PRIMARY KEY,
    solicitud_id INT NOT NULL,
    ruta_archivo VARCHAR(255) NOT NULL,
    nombre_original VARCHAR(255) NULL,
    usuario VARCHAR(100) NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (solicitud_id) REFERENCES solicitudes(idSolicitud) ON DELETE CASCADE
);
