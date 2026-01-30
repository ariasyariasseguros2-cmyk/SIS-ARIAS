import re
from typing import Dict, Optional

class CrecerPensionParser:
    """
    Parser especializado para el formato de 'Crecer Seguros' que incluye
    'DATOS DEL CONTRATANTE' en una estructura de tabla clara.
    """

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """
        Detecta si el texto corresponde al formato de Crecer Pensiones.
        Busca 'DATOS DE LA COMPAÑÍA DE SEGUROS' y 'DATOS DEL CONTRATANTE'
        o variantes como 'CRECER SEGUROS' + 'PENSIONES'.
        """
        # Normalizar para búsqueda insensible a mayúsculas y espacios múltiples
        # Se usa regex para permitir variaciones en espacios y tildes
        # Se permite cualquier cantidad de espacios entre letras para manejar kerning excesivo (e.g. D A T O S)
        
        # Patrón para "DATOS DE LA COMPAÑÍA DE SEGUROS" extremadamente permisivo con espacios
        # D A T O S   D E   L A ...
        company_header = r'D\s*A\s*T\s*O\s*S\s*D\s*E\s*L\s*A\s*C\s*O\s*M\s*P\s*A\s*[ÑN]\s*[IÍ]\s*A'
        
        # Patrón para "DATOS DEL CONTRATANTE" extremadamente permisivo con espacios
        contractor_header = r'D\s*A\s*T\s*O\s*S\s*D\s*E\s*L\s*C\s*O\s*N\s*T\s*R\s*A\s*T\s*A\s*N\s*T\s*E'
        
        # Patrón para "CRECER SEGUROS"
        crecer_pattern = r'C\s*R\s*E\s*C\s*E\s*R\s*S\s*E\s*G\s*U\s*R\s*O\s*S'
        
        # Patrón para "PENSIONES"
        pensiones_pattern = r'P\s*E\s*N\s*S\s*I\s*O\s*N\s*E\s*S'

        has_company_header = bool(re.search(company_header, text, re.IGNORECASE))
        has_contractor_header = bool(re.search(contractor_header, text, re.IGNORECASE))
        has_crecer = bool(re.search(crecer_pattern, text, re.IGNORECASE))
        has_pensiones = bool(re.search(pensiones_pattern, text, re.IGNORECASE))
        
        # Estrategia 1: Encabezados claros
        if has_company_header and has_contractor_header:
            return True
            
        # Estrategia 2: Crecer + Pensiones + Contratante (backup)
        if has_crecer and (has_pensiones or has_contractor_header):
            return True
            
        return False

    def extract_all(self) -> Dict:
        """Extrae toda la información del cliente."""
        return {
            'tipoPersona': 'JURIDICA' if self._is_juridica() else 'NATURAL',
            'razonSocial': self.extract_razon_social(),
            'tipoDocumento': 'RUC',
            'numeroDocumento': self.extract_ruc(),
            'direccion': self.extract_direccion(),
            'distrito': self.extract_distrito(),
            'provincia': self.extract_provincia(),
            'departamento': self.extract_departamento(),
            'email': '',
            'telefono1': '',
        }

    def _get_contratante_block(self) -> str:
        """
        Obtiene el bloque de texto correspondiente a 'DATOS DEL CONTRATANTE'.
        Corta desde 'DATOS DEL CONTRATANTE' hasta el siguiente encabezado o fin.
        """
        # Patrón robusto para encontrar el inicio del bloque
        pattern = r'D\s*A\s*T\s*O\s*S\s*D\s*E\s*L\s*C\s*O\s*N\s*T\s*R\s*A\s*T\s*A\s*N\s*T\s*E'
        match = re.search(pattern, self.text, re.IGNORECASE)
        if match:
            return self.text[match.start():]
            
        # Fallback a patrón simple si el robusto falla (poco probable pero por seguridad)
        simple_pattern = r'DATOS\s+DEL\s+CONTRATANTE'
        match = re.search(simple_pattern, self.text, re.IGNORECASE)
        if match:
            return self.text[match.start():]
            
        return ""

    def _clean_value(self, value: str) -> str:
        """Limpia el valor extraído de espacios extraños y saltos de línea."""
        if not value:
            return ""
        # Reemplazar saltos de línea con espacios
        value = value.replace('\n', ' ')
        # Eliminar espacios múltiples
        value = re.sub(r'\s+', ' ', value)
        return value.strip()

    def _clean_address_value(self, value: str) -> str:
        """
        Limpia y repara direcciones que vienen pegadas.
        Ej: AvenidaTUPACAMARUMZA.49LOTE.07A.H.C.TUBINOCONH.CENEPA
        """
        val = self._clean_value(value)
        
        # 1. Separar minúscula de mayúscula (ej: AvenidaTUPAC -> Avenida TUPAC)
        val = re.sub(r'([a-z])([A-Z])', r'\1 \2', val)

        # 2. Separar número de letra mayúscula (ej: 07A.H. -> 07 A.H.)
        val = re.sub(r'(\d)([A-Z])', r'\1 \2', val)
        
        # 3. Separar después de punto si sigue texto (ej: MZA.49 -> MZA. 49)
        val = re.sub(r'\.([A-Za-z0-9])', r'. \1', val)
        
        # 4. Separar palabras clave comunes si están pegadas
        # Quitamos 'AV' porque rompía 'Avenida'. Usamos 'AV.' si es necesario.
        keywords = ['MZA', 'LOTE', 'BLOCK', 'KM', 'INT', 'DPTO', 'URB', 'JR', 'CALLE', 'PSJE', 'CON', r'A\.H\.?', r'AV\.']
        for kw in keywords:
            # Reemplazar la keyword por " keyword "
            val = re.sub(r'(' + kw + r')', r' \1 ', val, flags=re.IGNORECASE)
            
        # Limpiar espacios dobles generados
        val = re.sub(r'\s+', ' ', val).strip()
        
        # Correcciones específicas de OCR/Pegado
        val = val.replace(' .', '.') # Corregir espacios antes de punto si se generaron
        val = val.replace(' ,', ',')
        
        return val

    def _clean_company_name(self, value: str) -> str:
        """
        Limpia y repara nombres de empresas pegados.
        Ej: TRANSPORTESFLUVIALESYSERVICIOS...
        """
        val = self._clean_value(value)
        
        # 1. Separar minúscula de mayúscula
        val = re.sub(r'([a-z])([A-Z])', r'\1 \2', val)
        
        # 2. Separar palabras clave comunes
        # Usamos raw strings para evitar SyntaxWarning con \.
        keywords = [
            r'EMPRESA', r'TRANSPORTES', r'SERVICIOS', r'SOCIEDAD', r'ANONIMA', r'CERRADA', 
            r'S\.A\.C', r'S\.R\.L', r'E\.I\.R\.L', r'S\.A', r'LTDA', r'CONSORCIO', r'GRUPO', 
            r'COMERCIAL', r'DISTRIBUIDORA', r'CONSTRUCTORA', r'INGENIERIA', r'MINERA',
            r'MARIA', r'ALEJANDRA', r'SAN', r'JUAN', r'DE', r'LA', r'LOS', r'EL'
        ]
        
        # Ordenar por longitud descendente para que palabras compuestas o más largas
        # tengan prioridad y no sean rotas por subcadenas (ej. evitar que 'LA' rompa 'FLUVIALES')
        keywords.sort(key=len, reverse=True)
        
        # Crear un único patrón regex optimizado
        pattern = r'(' + '|'.join(keywords) + r')'
        val = re.sub(pattern, r' \1 ', val, flags=re.IGNORECASE)
            
        # Limpiar espacios dobles
        val = re.sub(r'\s+', ' ', val).strip()
        val = val.replace(' .', '.')
        val = val.replace(' ,', ',')
        
        # Arreglos estéticos para siglas que pudieron separarse
        val = re.sub(r'S\.\s+A\.\s+C', 'S.A.C', val, flags=re.IGNORECASE)
        val = re.sub(r'S\.\s+R\.\s+L', 'S.R.L', val, flags=re.IGNORECASE)
        val = re.sub(r'S\.\s+A\.', 'S.A.', val, flags=re.IGNORECASE)
        
        return val
    
    def _clean_location_value(self, value: str) -> str:
        """
        Limpia y repara nombres de ubicación (Distrito, Provincia, Departamento).
        Maneja casos pegados como CORONELPORTILLO.
        """
        val = self._clean_address_value(value) # Reutiliza limpieza básica de dirección
        
        # Lista de palabras geográficas que suelen pegarse o necesitar separación
        geo_keywords = [
            r'CORONEL', r'PORTILLO', r'MARISCAL', r'CACERES', r'LEONCIO', r'PRADO',
            r'DANIEL', r'ALCIDES', r'CARRION', r'VICTOR', r'FAJARDO',
            r'SAN', r'SANTA', r'MARIA', r'JESUS', r'CARMEN', r'ALTO', r'BAJO', r'GRANDE',
            r'NUEVO', r'VIEJO', r'PUERTO', r'VILLA', r'CIUDAD',
            r'DE', r'DEL', r'LA', r'LAS', r'LOS', r'EL'
        ]
        
        # Ordenar por longitud descendente para evitar que 'EL' rompa 'CORONEL' o 'DANIEL'
        geo_keywords.sort(key=len, reverse=True)
        
        # Crear un único patrón regex
        pattern = r'(' + '|'.join(geo_keywords) + r')'
        val = re.sub(pattern, r' \1 ', val, flags=re.IGNORECASE)
            
        # Limpiar espacios dobles
        val = re.sub(r'\s+', ' ', val).strip()
        
        return val

    def extract_razon_social(self) -> str:
        block = self._get_contratante_block()
        # Regex robusta para "Razón Social" (permite espacios intercalados)
        # R a z ó n   S o c i a l
        header_pattern = r'R\s*a\s*z\s*[oó]\s*n\s*S\s*o\s*c\s*i\s*a\s*l'
        
        # Busca Razón Social seguida del valor hasta el salto de línea o RUC
        match = re.search(header_pattern + r'\s+(.+?)(?=\n|R\s*U\s*C)', block, re.IGNORECASE)
        
        if match:
            return self._clean_company_name(match.group(1))
        return ""

    def extract_ruc(self) -> str:
        block = self._get_contratante_block()
        # Busca RUC seguido de 11 dígitos
        # R U C
        header_pattern = r'R\s*U\s*C'
        match = re.search(header_pattern + r'\s+(\d{11})', block, re.IGNORECASE)
        if match:
            return match.group(1)
        return ""

    def extract_direccion(self) -> str:
        block = self._get_contratante_block()
        # Busca Dirección hasta Distrito o salto de línea
        # D i r e c c i ó n
        header_pattern = r'D\s*i\s*r\s*e\s*c\s*c\s*i\s*[oó]\s*n'
        # D i s t r i t o
        next_header = r'D\s*i\s*s\s*t\s*r\s*i\s*t\s*o'
        
        match = re.search(header_pattern + r'\s+(.+?)(?=\n|' + next_header + ')', block, re.IGNORECASE)
        if match:
            return self._clean_address_value(match.group(1))
        return ""

    def extract_distrito(self) -> str:
        block = self._get_contratante_block()
        header_pattern = r'D\s*i\s*s\s*t\s*r\s*i\s*t\s*o'
        next_header = r'P\s*r\s*o\s*v\s*i\s*n\s*c\s*i\s*a'
        
        match = re.search(header_pattern + r'\s+(.+?)(?=\n|' + next_header + ')', block, re.IGNORECASE)
        if match:
            return self._clean_location_value(match.group(1))
        return ""

    def extract_provincia(self) -> str:
        block = self._get_contratante_block()
        header_pattern = r'P\s*r\s*o\s*v\s*i\s*n\s*c\s*i\s*a'
        next_header = r'D\s*e\s*p\s*a\s*r\s*t\s*a\s*m\s*e\s*n\s*t\s*o'
        
        match = re.search(header_pattern + r'\s+(.+?)(?=\n|' + next_header + ')', block, re.IGNORECASE)
        if match:
            return self._clean_location_value(match.group(1))
        return ""

    def extract_departamento(self) -> str:
        block = self._get_contratante_block()
        header_pattern = r'D\s*e\s*p\s*a\s*r\s*t\s*a\s*m\s*e\s*n\s*t\s*o'
        next_header = r'T\s*e\s*l\s*[ée]\s*f\s*o\s*n\s*o'
        
        match = re.search(header_pattern + r'\s+(.+?)(?=\n|' + next_header + '|$)', block, re.IGNORECASE)
        if match:
            return self._clean_location_value(match.group(1))
        return ""

    def _is_juridica(self) -> bool:
        ruc = self.extract_ruc()
        return ruc.startswith('20')
