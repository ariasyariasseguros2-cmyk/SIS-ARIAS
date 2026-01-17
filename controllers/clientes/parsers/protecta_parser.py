import re
from typing import Dict, Optional, List


class ProtectaParser:
    """Parser específico para PDFs de Protecta"""

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """Detecta si el PDF es de Protecta."""
        indicators = [
            r'PROTECTA.*SECURITY',
            r'PROTECTA S\.A\.',
            r'protectasecurity\.pe',
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in indicators)

    def extract_contratante(self) -> Optional[str]:
        """Extrae el nombre del contratante."""
        # Buscar en la sección de datos del contratante
        seccion_match = re.search(
            r'(?:DATOS DEL CONTRATANTE|2\.\s*DATOS DEL CONTRATANTE)(.*?)(?:\n\n|3\.|Asegurados:|Vigencia de la Cobertura:)',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if seccion_match:
            seccion_texto = seccion_match.group(1)
            patterns = [
                r'Contratante\s*:\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&-]{4,79}?)(?:\n|Ruc:|RUC:)',
                r'Contratante\s*:\s*([^\n]{5,100}?)(?:\n|$)',
            ]

            for pattern in patterns:
                match = re.search(pattern, seccion_texto, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return None

    def extract_ruc(self) -> Optional[str]:
        """Extrae el RUC del contratante."""
        # Buscar en la sección de datos del contratante
        seccion_match = re.search(
            r'(?:DATOS DEL CONTRATANTE|2\.\s*DATOS DEL CONTRATANTE)(.*?)(?:\n\n|3\.|Asegurados:|Vigencia de la Cobertura:)',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if seccion_match:
            seccion_texto = seccion_match.group(1)
            match = re.search(r'Ruc\s*:\s*(\d{11})', seccion_texto, re.IGNORECASE)
            if match:
                ruc = match.group(1)
                if ruc != '20517207331':  # Excluir RUC de Protecta
                    return ruc

        return None

    def extract_dni(self) -> Optional[str]:
        """Extrae el DNI si es persona natural."""
        patterns = [
            r'DNI\s*:\s*(\d{8})',
            r'DNI\s*-\s*(\d{8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_direccion(self) -> Optional[str]:
        """Extrae dirección fiscal del contratante."""
        seccion_match = re.search(
            r'(?:DATOS DEL CONTRATANTE|2\.\s*DATOS DEL CONTRATANTE)(.*?)(?:\n\n|3\.|Asegurados:|Vigencia de la Cobertura:)',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if seccion_match:
            seccion_texto = seccion_match.group(1)
            patterns = [
                r'Direcci[oó]n Fiscal\s*:\s*([^\n]{10,150})',
                r'Direcci[oó]n\s*:\s*([^\n]{10,150})',
            ]

            for pattern in patterns:
                match = re.search(pattern, seccion_texto, re.IGNORECASE)
                if match:
                    direccion = match.group(1).strip()
                    # Excluir direcciones de Protecta
                    if not any(x in direccion for x in ['Domingo Orué', 'Surquillo', 'PROTECTA']):
                        return direccion

        return None

    def extract_email(self) -> Optional[str]:
        """Extrae email del contratante."""
        # Buscar en sección de contratante
        seccion_match = re.search(
            r'(?:DATOS DEL CONTRATANTE|2\.\s*DATOS DEL CONTRATANTE)(.*?)(?:\n\n|3\.|Asegurados:)',
            self.text,
            re.IGNORECASE | re.DOTALL
        )

        if seccion_match:
            seccion_texto = seccion_match.group(1)
            pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            match = re.search(pattern, seccion_texto)
            if match:
                email = match.group(0).lower()
                # Excluir emails de Protecta
                if 'protectasecurity.pe' not in email:
                    return email

        return None

    def extract_telefono(self) -> List[str]:
        """Extrae teléfonos."""
        phones = []
        patterns = [
            r'(?:^|\s)(9\d{8})(?:\s|$)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, self.text, re.MULTILINE)
            for match in matches:
                phone = match.group(1)
                phones.append(phone)

        return list(set(phones))[:2]  # Max 2 teléfonos

    def extract_all(self) -> Dict:
        """Extrae toda la información del PDF de Protecta."""
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
