"""
Parser genérico para PDFs que no coinciden con ningún formato específico.
"""
import re
from typing import Dict, Optional, List


class GenericParser:
    """Parser genérico para formatos no específicos."""

    def __init__(self, text: str):
        self.text = text

    def extract_ruc(self) -> Optional[str]:
        """Extrae RUC del documento."""
        rucs_aseguradoras = ['20517207331', '20418896915', '20332970411', '20202380621', '20100053455', '20600098633']
        rucs_encontrados = re.findall(r'RUC\s*-?\s*:?\s*(\d{11})', self.text, re.IGNORECASE)

        for ruc in rucs_encontrados:
            if ruc not in rucs_aseguradoras:
                return ruc

        return None

    def extract_dni(self) -> Optional[str]:
        """Extrae DNI del documento."""
        patterns = [
            r'DNI\s*-?\s*:?\s*(\d{8})',
            r'D\.N\.I\s*-?\s*:?\s*(\d{8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def extract_nombre(self) -> Optional[str]:
        """Extrae nombre o razón social."""
        patterns = [
            r'(?:Contratante|Raz[oó]n Social|Cliente|Asegurado)\s*:?\s*([A-ZÁÉÍÓÚÑ][^\n]{5,100}?)(?:\s+RUC|\s+DNI|\n)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                nombre = re.sub(r'\s+(RUC|DNI).*$', '', nombre)
                if len(nombre) > 5:
                    return nombre

        return None

    def extract_email(self) -> Optional[str]:
        """Extrae email."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(pattern, self.text)

        # Excluir emails de aseguradoras
        dominios_aseguradoras = ['protectasecurity.pe', 'mapfre.com.pe', 'pacifico.com.pe', 'lapositiva.com.pe', 'sanitas.pe', 'crecer.pe']

        for email in matches:
            if not any(dominio in email.lower() for dominio in dominios_aseguradoras):
                return email.lower()

        return None

    def extract_telefono(self) -> List[str]:
        """Extrae teléfonos."""
        phones = []
        pattern = r'(?:^|\s)(9\d{8})(?:\s|$)'
        matches = re.finditer(pattern, self.text, re.MULTILINE)

        for match in matches:
            phones.append(match.group(1))

        return list(set(phones))[:2]

    def extract_direccion(self) -> Optional[str]:
        """Extrae dirección."""
        patterns = [
            r'Direcci[oó]n\s+Fiscal\s*:?\s*([^\n]{10,150})',
            r'(?:Direcci[oó]n|Domicilio)\s*:?\s*([^\n]{10,150})',
            r'(?:AV|AVENIDA|JR|CALLE)\s+[A-ZÁÉÍÓÚÑ][^\n]{10,100}',
        ]

        palabras_aseguradoras = ['Protecta', 'Pacífico', 'Mapfre', 'Positiva', 'Surquillo', 'Orué', 'Crecer', 'San Isidro', 'Jorge Basadre']

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                direccion = match.group(1) if '(' in pattern else match.group(0)
                direccion = direccion.strip()

                if not any(palabra in direccion for palabra in palabras_aseguradoras):
                    return direccion

        return None

    def extract_all(self) -> Dict:
        """Extrae toda la informacion con parser generico."""
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

        nombre = self.extract_nombre()
        telefonos = self.extract_telefono()

        return {
            'tipoPersona': tipo_persona,
            'razonSocial': nombre or "",
            'tipoDocumento': tipo_documento,
            'numeroDocumento': numero_documento,
            'direccion': self.extract_direccion() or "",
            'distrito': "",
            'provincia': "",
            'departamento': "",
            'email': self.extract_email() or "",
            'telefono1': telefonos[0] if len(telefonos) > 0 else "",
            'telefono2': telefonos[1] if len(telefonos) > 1 else "",
        }
