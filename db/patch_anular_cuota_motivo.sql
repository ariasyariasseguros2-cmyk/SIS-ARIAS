-- Patch: motivo y usuario en la anulación individual de cuotas
-- Aplica solo el cambio de DB: nuevas columnas en cuotas

USE ariasyariaspe_bd_sisnet;

ALTER TABLE cuotas
    ADD COLUMN motivo_anulacion VARCHAR(200) NULL,
    ADD COLUMN usuario_anulacion VARCHAR(100) NULL,
    ADD COLUMN fecha_anulacion DATETIME NULL;
