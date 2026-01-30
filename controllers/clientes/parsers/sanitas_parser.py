import re
from typing import Dict, Optional, List


class SanitasParser:


    def __init__(self, text: str):
        self.text = text
        self.normalized_text = self._normalize_text(text)

    # RUCs que deben ser ignorados (por ejemplo el RUC de la propia compañia)
    EXCLUDED_RUCS = {"20523470761"}

    def _normalize_text(self, text: str) -> str:
        text = re.sub(r'([a-zñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)


        text = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', text)


        text = re.sub(r'\s+', ' ', text)

        return text

    def _separate_uppercase_words(self, text: str) -> str:
        """Intenta separar palabras en mayúsculas pegadas usando patrones comunes."""
        if not text or text.count(' ') > len(text) / 10:
            return text  # Ya tiene suficientes espacios

        result = text

        # Lista de palabras a separar (ordenadas por longitud, más largas primero)
        words_to_separate = [
            # Palabras de empresas (más largas primero)
            'CONSTRUCCION', 'INGENIERIA', 'CONTRATISTAS', 'INVERSIONES', 'CORPORACION',
            'CONSULTORES', 'INTEGRALES', 'COMERCIAL', 'INDUSTRIA', 'SERVICIOS',
            'TRANSPORTES', 'FLUVIALES', 'MARITIMOS', 'TERRESTRES', 'GENERALES',
            'ASOCIADOS', 'SOCIEDAD', 'ANONIMA', 'CERRADA', 'EMPRESA', 'GROUP', 'PERU',

            # Nombres y apellidos comunes
            'ALEJANDRA', 'ALEJANDRO', 'FERNANDO', 'FRANCISCO', 'RODRIGUEZ', 'FERNANDEZ',
            'HERNANDEZ', 'MARTINEZ', 'GUTIERREZ', 'GONZALEZ', 'ANTONIO', 'CARLOS',
            'EDUARDO', 'GARCIA', 'RAMIREZ', 'SANCHEZ', 'VASQUEZ', 'JIMENEZ',
            'MORALES', 'HERRERA', 'MENDOZA', 'CASTILLO', 'CHAVEZ', 'ROMERO',
            'FLORES', 'TORRES', 'RIVERA', 'CASTRO', 'VARGAS', 'MEDINA',
            'SILVA', 'GOMEZ', 'ORTIZ', 'LOPEZ', 'REYES', 'MARIA', 'CRUZ',
            'PEREZ', 'RUIZ', 'DIAZ', 'RAMOS', 'ROJAS', 'SOTO',

            # Palabras de dirección (más largas primero)
            'PROLONGACION', 'URBANIZACION', 'AGRUPACION', 'COOPERATIVA', 'RESIDENCIAL',
            'CARRETERA', 'AUTOPISTA', 'TUPACAMARU', 'AVENIDA', 'MANZANA', 'EDIFICIO',
            'INTERIOR', 'JIRON', 'CALLE', 'PASAJE', 'PARQUE', 'SECTOR', 'NUMERO',
            'BLOCK', 'TORRE', 'TUPAC', 'AMARU', 'LOTE', 'ZONA', 'DPTO', 'PISO',

            # Abreviaturas
            'MZA', 'URB', 'NRO', 'INT', 'ASOC', 'AGRUP', 'COOP', 'EIRL', 'SAC', 'SRL',
        ]

        # Palabras cortas que solo se separan si están completas (word boundaries)
        short_words = ['DEL', 'LOS', 'LAS', 'CON', 'POR']

        # Separar palabras largas primero
        for word in words_to_separate:
            result = re.sub(f'({word})', r' \1 ', result, flags=re.IGNORECASE)

        for word in short_words:
            result = re.sub(fr'\b({word})\b', r' \1 ', result, flags=re.IGNORECASE)

        # Separar números de letras: MZA49 -> MZA 49
        result = re.sub(r'([A-Z])(\d)', r'\1 \2', result)
        result = re.sub(r'(\d)([A-Z])', r'\1 \2', result)


        # Limpiar espacios múltiples
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    def _clean_field(self, text: str) -> str:
        if not text:
            return ""

        # Guardar el texto original para comparación
        original = text

        # Separar texto pegado si es necesario
        if len(text) > 20 and text.count(' ') < max(3, len(text) / 15):
            # Primero aplicar separación básica
            text = re.sub(r'([a-zñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', text)

            if text.count(' ') < max(2, len(text) / 20):
                text = self._separate_uppercase_words(text)
                print(f"[DEBUG] Separación avanzada: '{original}' → '{text}'")

        text = re.sub(r'\s+', ' ', text)

        # eliminar carcateres raros
        text = text.strip(' \n\r\t:-.,')

        return text

    @staticmethod
    def can_parse(text: str) -> bool:
        """deteccion de etipo de pdf"""
        
        # Evitar falsos positivos con Crecer Seguros (que a veces menciona SCTR)
        # Patrón permisivo para "CRECER SEGUROS"
        crecer_pattern = r'C\s*R\s*E\s*C\s*E\s*R\s*S\s*E\s*G\s*U\s*R\s*O\s*S'
        if re.search(crecer_pattern, text, re.IGNORECASE):
            return False

        # Evitar falsos positivos con Protecta
        protecta_pattern = r'P\s*R\s*O\s*T\s*E\s*C\s*T\s*A'
        if re.search(protecta_pattern, text, re.IGNORECASE):
            return False

        indicators = [
            r'SANITAS.*PER[UÚ]',
            # r'LA POSITIVA', # Causaba conflicto con La Positiva EPS
            r'SCTR.*SALUD',
            r'CONSTANCIA.*SCTR',
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in indicators)

    def extract_contratante(self) -> Optional[str]:
        """extrae nombre del contratante , mediante posibles secciones  """
        patterns = [
            r'Contratante\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&\-\'\"]+?)(?:\s*(?:RUC|DNI|Direcci[oó]n|$))',

            r'DATOS\s+DEL\s+CONTRATANTE.*?Contratante\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][^\n]{10,100}?)(?:\s*(?:RUC|DNI|$))',

            r'certifica\s+que\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&\-]+?)\s+(?:identificad|con\s+RUC|de\s+ahora)',
        ]

        #test con texto normalizado
        for pattern in patterns:
            match = re.search(pattern, self.normalized_text, re.IGNORECASE | re.DOTALL)
            if match:
                nombre = match.group(1).strip()

                nombre = self._clean_field(nombre)

                # validacion de palabras invalidas
                if nombre and len(nombre) > 3:
                    palabras_invalidas = ['vigencia', 'conforme', 'decreto', 'constancia', 'certificado']
                    if not any(palabra in nombre.lower() for palabra in palabras_invalidas):
                        # cortar numeros pegados
                        nombre = re.sub(r'\s*\d{8,}.*$', '', nombre)
                        return self._clean_field(nombre)

        # test con texto original para descartar errores de normalizacion
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                nombre = match.group(1).strip()
                # Si el nombre está todo pegado, intentar separarlo
                if len(nombre) > 30 and nombre.count(' ') < 2:
                    nombre = re.sub(r'([a-zñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', nombre)

                nombre = self._clean_field(nombre)

                if nombre and len(nombre) > 3:
                    palabras_invalidas = ['vigencia', 'conforme', 'decreto']
                    if not any(palabra in nombre.lower() for palabra in palabras_invalidas):
                        return nombre


        return None

    def extract_ruc(self) -> Optional[str]:
        """Extrae el RUC del contratante.
        revisa en el texto extraido normalizado y no nornmalizado"""
        patterns = [
            r'RUC\s*[:\-]?\s*(\d{11})',
            r'Contratante.*?(\d{11})',
        ]
        for text in [self.normalized_text, self.text]:
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    ruc = match.group(1)
                    # Ignorar RUCs excluidos (por ejemplo el RUC de la compañia)
                    if ruc in self.EXCLUDED_RUCS:
                        continue
                    # Validar que sea un RUC válido
                    if ruc.startswith(('10', '20')):
                        return ruc


        rucs = re.findall(r'\b(\d{11})\b', self.text)
        for ruc in rucs:
            if ruc in self.EXCLUDED_RUCS:
                continue
            if ruc.startswith(('10', '20')):
                return ruc

        return None

    def extract_dni(self) -> Optional[str]:
#extrae dni si no es persona juridica
        patterns = [
            r'DNI\s*[:\-]?\s*(\d{8})',
            r'D\.N\.I\.?\s*[:\-]?\s*(\d{8})',
            r'(?:^|\s)(\d{8})(?:\s|$)',
        ]

        for text in [self.normalized_text, self.text]:
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    dni = match.group(1)
                    #evitar que sea una fecha
                    if not dni.startswith(('19', '20', '00')):
                        return dni

        return None

    def extract_direccion(self) -> Optional[str]:
        """Extrae dirección del contratante."""
        patterns = [
            # Con dos puntos
            r'Direcci[oó]n\s*[:\-]\s*([^\n]{10,500}?)(?:\s*(?:Distrito|Provincia|Departamento|Ubigeo|Tel[eé]fono|Email|$))',
            r'DOMICILIO\s*[:\-]\s*([^\n]{10,500}?)(?:\s*(?:Distrito|Provincia|$))',
            # Sin dos puntos, después de la palabra (agregado Ubigeo|Tel|Email a la lista de parada)
            r'Direcci[oó]n\s+([A-Z][^\n]{10,500}?)(?:\s*(?:Distrito|Provincia|Departamento|Ubigeo|Tel[eé]fono|Email|$))',
        ]

        # Intentar en texto normalizado primero
        for pattern in patterns:
            match = re.search(pattern, self.normalized_text, re.IGNORECASE)
            if match:
                direccion = self._clean_field(match.group(1))
                # Limpiar si hay información adicional pegada
                direccion = re.sub(r'\s*(?:Distrito|Provincia|Departamento|Tel[eé]fono|Email).*$', '', direccion, flags=re.IGNORECASE)
                
                # Limpiar sufijos de ubicación comunes que se pegan al final
                location_suffixes = [
                    r'\s*-\s*UCAYALI.*$',
                    r'\s*-\s*LIMA.*$',
                    r'\s*-\s*CORONEL PORTILLO.*$',
                    r'\s*-\s*CALLERIA.*$',
                    r'\s*-\s*MANANTAY.*$',
                    r'\s*-\s*YARINACOCHA.*$',
                    r'\s*-\s*AREQUIPA.*$',
                    r'\s*-\s*TRUJILLO.*$',
                    r'\s*-\s*CHICLAYO.*$',
                    r'\s*-\s*PIURA.*$',
                    r'\s*-\s*CUSCO.*$',
                    r'\s*-\s*IQUITOS.*$',
                    r'\s*-\s*TACNA.*$',
                    r'\s*-\s*HUANCAYO.*$',
                ]
                for suffix in location_suffixes:
                    direccion = re.sub(suffix, '', direccion, flags=re.IGNORECASE)

                if direccion and len(direccion) > 5:
                    return direccion

        # Intentar en texto original
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                direccion = match.group(1)
                # Separar texto pegado
                if len(direccion) > 40 and direccion.count(' ') < 3:
                    direccion = re.sub(r'([a-zñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', direccion)

                direccion = self._clean_field(direccion)
                if direccion and len(direccion) > 5:
                    return direccion

        return None

    def extract_ubicacion(self) -> Dict[str, Optional[str]]:
        """Extrae distrito, provincia y departamento."""
        result = {'distrito': None, 'provincia': None, 'departamento': None}

        # Usar texto normalizado para mejor detección
        text_upper = self.normalized_text.upper()
        text_orig = self.text.upper()

        # Patrones para extraer campos específicos
        patterns_distrito = [
            r'Distrito\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s]+?)(?:\s*(?:Provincia|Departamento|Ubigeo|$))',
        ]
        patterns_provincia = [
            r'Provincia\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s]+?)(?:\s*(?:Departamento|Ubigeo|$))',
        ]
        patterns_departamento = [
            r'Departamento\s*[:\-]?\s*([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ\s]+?)(?:\s*(?:Ubigeo|Tel|Email|$))',
        ]

        for text in [self.normalized_text, self.text]:
            if not result['distrito']:
                for pattern in patterns_distrito:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        result['distrito'] = self._clean_field(match.group(1)).title()
                        break

            if not result['provincia']:
                for pattern in patterns_provincia:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        result['provincia'] = self._clean_field(match.group(1)).upper()
                        break

            if not result['departamento']:
                for pattern in patterns_departamento:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        result['departamento'] = self._clean_field(match.group(1)).upper()
                        break

        # test para casos comunes en UCAYALI
        for text in [text_upper, text_orig]:
            if 'UCAYALI' in text:
                result['departamento'] = result['departamento'] or 'UCAYALI'
                if 'CORONEL PORTILLO' in text or 'CORONELPORTILLO' in text:
                    result['provincia'] = result['provincia'] or 'CORONEL PORTILLO'
                if 'CALLERIA' in text:
                    result['distrito'] = result['distrito'] or 'Calleria'
                elif 'MANANTAY' in text:
                    result['distrito'] = result['distrito'] or 'Manantay'
                elif 'YARINACOCHA' in text:
                    result['distrito'] = result['distrito'] or 'Yarinacocha'

            if 'LIMA' in text and not result['departamento']:
                result['departamento'] = 'LIMA'
                result['provincia'] = result['provincia'] or 'LIMA'

        return result

    def extract_email(self) -> Optional[str]:
        """Extrae email."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        # Buscar en ambos textos
        for text in [self.normalized_text, self.text]:
            matches = re.findall(pattern, text)
            # Excluir emails de Sanitas y La Positiva
            for email in matches:
                if not any(x in email.lower() for x in ['sanitas', 'positiva', 'mapfre']):
                    return email.lower()

        return None

    def extract_telefono(self) -> List[str]:
        """Extrae teléfonos."""
        phones = set()

        # patrones para diferentes formatos de celulares o telefonos

        patterns = [
            r'(?:^|\s|:)(9\d{8})(?:\s|$|,)',
            r'Tel[eé]fono\s*[:\-]?\s*(\d{9})',
            r'(?:^|\s)(\d{9})(?:\s|$)',
        ]

        for text in [self.normalized_text, self.text]:
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    phone = match.group(1)
                    # Validar que sea un celular peruano (empieza con 9)
                    if phone.startswith('9'):
                        phones.add(phone)

        return list(phones)[:2]

    def extract_all(self) -> Dict:
        """Eextrae info del pdf de Sanitas."""
        ruc = self.extract_ruc()
        dni = self.extract_dni()

        if ruc:
            tipo_documento = "RUC"
            numero_documento = ruc
            tipo_persona = "JURIDICA" if ruc.startswith('20') else "NATURAL"
        elif dni:
            tipo_documento = "DNI/CE"
            numero_documento = dni
            tipo_persona = "NATURAL"
        else:
            tipo_documento = "DNI/CE"
            numero_documento = ""
            tipo_persona = "NATURAL"

        nombre = self.extract_contratante()
        telefonos = self.extract_telefono()
        ubicacion = self.extract_ubicacion()

        return {
            'tipoPersona': tipo_persona,
            'razonSocial': nombre or "",
            'tipoDocumento': tipo_documento,
            'numeroDocumento': numero_documento,
            'direccion': self.extract_direccion() or "",
            'distrito': ubicacion.get('distrito') or "",
            'provincia': ubicacion.get('provincia') or "LIMA",
            'departamento': ubicacion.get('departamento') or "LIMA",
            'email': self.extract_email() or "",
            'telefono1': telefonos[0] if len(telefonos) > 0 else "",
            'telefono2': telefonos[1] if len(telefonos) > 1 else "",
        }
