use ariasyariaspe_bd_sisnet;

SET @k = 'MiPassphraseSegura$$2025';

UPDATE clientes
SET razon_social = TO_BASE64(AES_ENCRYPT(razon_social, @k))
WHERE razon_social IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(razon_social), @k) IS NULL;

UPDATE clientes
SET numero_documento = TO_BASE64(AES_ENCRYPT(numero_documento, @k))
WHERE numero_documento IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(numero_documento), @k) IS NULL;

UPDATE clientes
SET telefono = TO_BASE64(AES_ENCRYPT(telefono, @k))
WHERE telefono IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(telefono), @k) IS NULL;

UPDATE clientes
SET email = TO_BASE64(AES_ENCRYPT(email, @k))
WHERE email IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(email), @k) IS NULL;
  SET @k = 'MiPassphraseSegura$$2025';

UPDATE polizas
SET asegurado = TO_BASE64(AES_ENCRYPT(asegurado, @k))
WHERE asegurado IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(asegurado), @k) IS NULL;

UPDATE polizas
SET poliza = TO_BASE64(AES_ENCRYPT(poliza, @k))
WHERE poliza IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(poliza), @k) IS NULL;

UPDATE polizas
SET recibo = TO_BASE64(AES_ENCRYPT(recibo, @k))
WHERE recibo IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(recibo), @k) IS NULL;

UPDATE polizas
SET contrato_nro = TO_BASE64(AES_ENCRYPT(contrato_nro, @k))
WHERE contrato_nro IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(contrato_nro), @k) IS NULL;

UPDATE polizas
SET nro = TO_BASE64(AES_ENCRYPT(nro, @k))
WHERE nro IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(nro), @k) IS NULL;
SET @k = 'MiPassphraseSegura$$2025';

UPDATE siniestros
SET email = TO_BASE64(AES_ENCRYPT(email, @k))
WHERE email IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(email), @k) IS NULL;

UPDATE siniestros
SET telefonos = TO_BASE64(AES_ENCRYPT(telefonos, @k))
WHERE telefonos IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(telefonos), @k) IS NULL;

UPDATE siniestros
SET poliza = TO_BASE64(AES_ENCRYPT(poliza, @k))
WHERE poliza IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(poliza), @k) IS NULL;

UPDATE siniestros
SET banco = TO_BASE64(AES_ENCRYPT(banco, @k))
WHERE banco IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(banco), @k) IS NULL;
  SET @k = 'MiPassphraseSegura$$2025';

UPDATE cuotas
SET poliza = TO_BASE64(AES_ENCRYPT(poliza, @k))
WHERE poliza IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(poliza), @k) IS NULL;

UPDATE cuotas
SET cupon = TO_BASE64(AES_ENCRYPT(cupon, @k))
WHERE cupon IS NOT NULL
  AND AES_DECRYPT(FROM_BASE64(cupon), @k) IS NULL;
  SET @k = 'MiPassphraseSegura$$2025';
SELECT
  idCliente,
  CAST(AES_DECRYPT(FROM_BASE64(razon_social), @k) AS CHAR) AS razon_social,
  tipo_documento,
  CAST(AES_DECRYPT(FROM_BASE64(numero_documento), @k) AS CHAR) AS numero_documento,
  CAST(AES_DECRYPT(FROM_BASE64(telefono), @k) AS CHAR) AS telefono,
  CAST(AES_DECRYPT(FROM_BASE64(email), @k) AS CHAR) AS email
FROM clientes
WHERE activo = 1;



