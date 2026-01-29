"""
Controlador para extraer información de clientes desde archivos PDF.
Soporta múltiples formatos de PDF de diferentes aseguradoras con detección automática.
"""
import re
import pdfplumber
import PyPDF2
from typing import Dict

# Importar parsers especializados
try:
    from controllers.clientes.parsers import (
        MapfreParser,
        ProtectaParser,
        PacificoParser,
        SanitasParser,
        CrecerParser,
        GenericParser,
        LaPositivaEPSParser
    )
except ImportError:
    # Fallback si no se pueden importar
    MapfreParser = None
    ProtectaParser = None
    PacificoParser = None
    SanitasParser = None
    CrecerParser = None
    GenericParser = None
    LaPositivaEPSParser = None


class PDFClienteExtractor:
    """
    Clase para extraer información de clientes desde PDFs.
    Detecta automáticamente el formato y usa el parser correspondiente.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text_content = ""
        self.extracted_data = {}
        self.detected_company = None

    def extract_text(self) -> str:
        """Extrae todo el texto del PDF usando pdfplumber y PyPDF2 como fallback."""
        try:
            # Intento principal con pdfplumber (mejor para tablas y estructura)
            with pdfplumber.open(self.pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                self.text_content = "\n".join(text_parts)
                return self.text_content
        except Exception as e:
            print(f"Error con pdfplumber: {e}, intentando con PyPDF2...")

            # Fallback con PyPDF2
            try:
                with open(self.pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text_parts = []
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    self.text_content = "\n".join(text_parts)
                    return self.text_content
            except Exception as e2:
                print(f"Error con PyPDF2: {e2}")
                return ""

    def detect_company(self) -> str:
        """
        Detecta automáticamente qué aseguradora es el PDF.
        Retorna: 'mapfre', 'protecta', 'pacifico', 'sanitas', 'crecer' o 'generic'
        """
        text_lower = self.text_content.lower()

        # Detectar Mapfre (primero para evitar conflictos)
        if MapfreParser and MapfreParser.can_parse(self.text_content):
            self.detected_company = 'mapfre'
            return 'mapfre'

        # Detectar Protecta
        if ProtectaParser and ProtectaParser.can_parse(self.text_content):
            self.detected_company = 'protecta'
            return 'protecta'

        # Detectar Pacífico
        if PacificoParser and PacificoParser.can_parse(self.text_content):
            self.detected_company = 'pacifico'
            return 'pacifico'

        # Detectar Crecer (antes de Sanitas porque puede tener "crecer" en el nombre)
        if CrecerParser and CrecerParser.can_parse(self.text_content):
            self.detected_company = 'crecer'
            return 'crecer'

        # Detectar La Positiva (antes de Sanitas para evitar falsos positivos)
        if LaPositivaEPSParser and LaPositivaEPSParser.can_parse(self.text_content):
            self.detected_company = 'lapositiva'
            return 'lapositiva'

        # Detectar Sanitas
        if SanitasParser and SanitasParser.can_parse(self.text_content):
            self.detected_company = 'sanitas'
            return 'sanitas'

        # Detectar Rimac
        if 'rimac seguros' in text_lower or 'rimac' in text_lower:
            self.detected_company = 'rimac'
            return 'rimac'

        # Default: parser genérico
        self.detected_company = 'generic'
        return 'generic'

    def extract_all(self) -> Dict:
        """
        Extrae toda la información usando el parser apropiado según la aseguradora detectada.
        """
        if not self.text_content:
            self.extract_text()

        # Detectar qué aseguradora es
        company = self.detect_company()

        #print(f"[PDF Extractor] Aseguradora detectada: {company}")

        # Usar el parser específico
        try:
            if company == 'mapfre' and MapfreParser:
                parser = MapfreParser(self.text_content)
                self.extracted_data = parser.extract_all()
            elif company == 'protecta' and ProtectaParser:
                parser = ProtectaParser(self.text_content)
                self.extracted_data = parser.extract_all()
            elif company == 'pacifico' and PacificoParser:
                parser = PacificoParser(self.text_content)
                self.extracted_data = parser.extract_all()
            elif company == 'sanitas' and SanitasParser:
                parser = SanitasParser(self.text_content)
                self.extracted_data = parser.extract_all()
            elif company == 'crecer' and CrecerParser:
                parser = CrecerParser(self.text_content)
                self.extracted_data = parser.extract_all()
            elif company == 'lapositiva' and LaPositivaEPSParser:
                parser = LaPositivaEPSParser(self.text_content)
                self.extracted_data = parser.extract_all()
            else:
                # Usar parser genérico para otras aseguradoras
                if GenericParser:
                    parser = GenericParser(self.text_content)
                    self.extracted_data = parser.extract_all()
                else:
                    # Fallback al método anterior si no hay parsers disponibles
                    self.extracted_data = self._extract_generic_fallback()
            print(f"[PDF Extractor] Datos extraídos: {self.extracted_data}")
            print(f"[PDF Extractor] Aseguradora detectada: {company}")
        except Exception as e:
            print(f"[PDF Extractor] Error con parser específico: {e}")
            # Fallback al método genérico
            if GenericParser:
                parser = GenericParser(self.text_content)
                self.extracted_data = parser.extract_all()
            else:
                self.extracted_data = self._extract_generic_fallback()

        # Agregar campo de detección
        self.extracted_data['_detected_company'] = company

        return self.extracted_data

    def _extract_generic_fallback(self) -> Dict:
        """Método de fallback si no hay parsers disponibles."""
        return {
            'tipoPersona': 'NATURAL',
            'razonSocial': "",
            'tipoDocumento': "DNI/CE",
            'numeroDocumento': "",
            'direccion': "",
            'distrito': "",
            'provincia': "LIMA",
            'departamento': "LIMA",
            'email': "",
            'telefono1': "",
            'telefono2': "",
            'subAgente': "",
            'contactoNombre': "",
            'contactoEmail': "",
            'contactoTelefono': "",
        }


def process_pdf_file(file_path: str) -> Dict:
    """
    Función principal para procesar un archivo PDF y extraer información del cliente.

    Args:
        file_path: Ruta al archivo PDF

    Returns:
        Dict con los datos extraídos del cliente
    """
    try:
        extractor = PDFClienteExtractor(file_path)
        data = extractor.extract_all()

        # Información de debug
        debug_info = f"Aseguradora detectada: {extractor.detected_company}\n"
        debug_info += f"Primeros 500 caracteres:\n{extractor.text_content[:500]}"

        return {
            'ok': True,
            'data': data,
            'raw_text': debug_info,
            'detected_company': extractor.detected_company
        }
    except Exception as e:
        return {
            'ok': False,
            'error': str(e),
            'data': {}
        }
