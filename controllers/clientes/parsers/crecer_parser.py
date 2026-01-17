import re
from typing import Dict, Optional, List


class CrecerParser:

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """Detecta si el PDF es de Crecer Seguros."""
        indicators = [
            r'CRECER SEGUROS',
            r'R\.U\.C\.\s*20600098633',
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in indicators)

    def extract_contratante(self) -> Optional[str]:
        """Extrae el nombre del contratante."""
        patterns = [

            r'SE[ÑN]OR\s*\(ES\)\s*:\s*([A-ZÁÉÍÓÚÑ][^\n:]{5,100}?)(?:\s*FECHA|\s*RUC|\s*:|$)',

            r'CONTRATANTE\s*:\s*([A-ZÁÉÍÓÚÑ][^\n:]{5,100}?)(?:\s*RUC|\s*DIRECCI[OÓ]?[NI]N?|\s*:|$)',

            r':{10,}.*?\b(\d{8,})\s+(\d{6,})\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ \.,&\']{10,80}?)\s+\d{8,11}\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                if match.lastindex == 3:
                    nombre = match.group(3).strip()
                else:
                    nombre = match.group(1).strip()
                nombre = re.sub(r'\s*:?\s*$', '', nombre)
                nombre = re.sub(r'\s+', ' ', nombre)
                return nombre
        return None

    def extract_ruc(self) -> Optional[str]:
        """RUC CONTRATANTE"""
        patterns = [
            r'SEÑOR.*?RUC\s*:\s*(\d{11})',
            r'(?:^|\n)RUC\s*:\s*(\d{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                ruc = match.group(1)
                # Excluir RUC de Crecer
                if ruc != '20600098633':
                    return ruc

        rucs = re.findall(r'\b(\d{11})\b', self.text)
        for ruc in rucs:
            if ruc != '20600098633' and ruc.startswith('20'):
                return ruc
        return None

    def extract_dni(self) -> Optional[str]:
        patterns = [
            r'DNI\s*[:\-]\s*(\d{8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_direccion(self) -> Optional[str]:
        """Extrae dirección del contratante."""
        patterns = [
            r'DIRECCI[OÓ]?[NI]N?\s*:\s*((?:AV|JR|CA|CALLE|JIRON|AVENIDA|MZ|MZA|LOTE).*?)(?:\s*ORDEN\s+COMPRA|\s*FORMA\s+DE\s+PAGO|\s*C[OÓ]DIGO)',
            r'Direcci[oó]?[ni]n?\s*:\s*((?:AV|JR|CA|CALLE|JIRON|AVENIDA|MZ|MZA|LOTE).*?)(?:\s*ORDEN\s+COMPRA|\s*FORMA\s+DE\s+PAGO|\s*C[oó]digo)',

            r'((?:AV|JR|CA|CALLE|JIRON|AVENIDA|MZ|MZA|LOTE)[^\n]{5,150}(?:\n[^\n]{1,100})?)\s*DIRECCI[OÓ]?[NI]N?\s*:',

            r'DIRECCI[OÓ]?[NI]N?\s*:\s*([A-ZÁÉÍÓÚÑ0-9][^\n]{10,150}?)(?:\s+\d{4,6}\s*-|\s*RUC|\s*ACTIVIDAD)',
            r'Direcci[oó]?[ni]n?\s*:\s*([A-ZÁÉÍÓÚÑ0-9][^\n]{10,150}?)(?:\s+\d{4,6}\s*-|\s*RUC|\s*ACTIVIDAD)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                direccion = match.group(1).strip()

                if not any(x in direccion for x in ['Jorge Basadre', 'SAN ISIDRO']):

                    direccion = re.sub(r'\s+', ' ', direccion)

                    direccion = re.sub(r'\(\s*\.\s*[A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+', '', direccion, flags=re.IGNORECASE)

                    direccion = re.sub(r'\(\s*\.\s*[A-ZÁÉÍÓÚÑ\s]+-?\s*$', '', direccion, flags=re.IGNORECASE)

                    direccion = re.sub(r'\s*(FORMA\s+DE\s+PAGO|ORDEN\s+COMPRA|C[OÓ]DIGO).*$', '', direccion, flags=re.IGNORECASE)

                    direccion = re.sub(r'\s+\d{4,6}\s*-\s*[A-Z].*$', '', direccion, flags=re.IGNORECASE)
                    return direccion.strip()
        return None

    def extract_email(self) -> Optional[str]:
        """Extrae email."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(pattern, self.text)

        for email in matches:
            if 'crecer' not in email.lower():
                return email.lower()
        return None

    def extract_ubicacion_geografica(self) -> Dict[str, str]:
        """Extrae distrito, provincia y departamento de la dirección."""
#( DISTRITO - PROVINCIA - DEPARTAMENTO) DISTRITO - PROVINCIA - DEPARTAMENTO)
        patterns = [
            # Con punto despues del paréntesis, permite saltos de línea (ANTES de DIRECCIÓN)
            r'\(\s*\.\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*\n?\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+)',
            #  Con punto, captura hasta ORDEN, FORMA, etc.
            r'\(\s*\.\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\s+ORDEN|\s+FORMA|\s*$)',
            #Sin punto
            r'\(\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*\)',
            #  despues de DIRECCIÓN (cuando pdfplumber invierte el orden)
            r'DIRECCI[OÓ]?[NI]N?\s*:.*?\n\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|$)',
            #  Distrito truncado en dirección + resto después
            r'\(\s*\.\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*$',  # Distrito truncado
        ]
        for pattern in patterns[:4]:
            match = re.search(pattern, self.text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:

                if match.lastindex == 2 and pattern == patterns[3]:

                    distrito_match = re.search(r'\(\s*\.\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*\n?\s*DIRECCI', self.text, re.IGNORECASE | re.DOTALL)
                    distrito = distrito_match.group(1).strip() if distrito_match else ""
                    provincia = match.group(1).strip()
                    departamento = match.group(2).strip()
                else:
                    distrito = match.group(1).strip()
                    provincia = match.group(2).strip() if match.lastindex >= 2 else ""
                    departamento = match.group(3).strip() if match.lastindex >= 3 else ""

                # Limpiar texto extra del departamento (como ORDEN COMPRA, FORMA DE PAGO, etc.)
                departamento = re.sub(r'\s*(ORDEN|COMPRA|FORMA|DE|PAGO).*$', '', departamento, flags=re.IGNORECASE).strip()

                # Validar que no sean campos del encabezado de Crecer
                if 'LIMA' not in distrito.upper() and 'ISIDRO' not in distrito.upper():
                    if provincia and departamento:  # Asegurar que al menos tenemos provincia y departamento
                        return {
                            'distrito': distrito.title() if distrito else '',
                            'provincia': provincia.title(),
                            'departamento': departamento.title()
                        }

        return {'distrito': '', 'provincia': '', 'departamento': ''}

    def extract_telefono(self) -> List[str]:
        """Extrae telefono."""
        phones = []
        pattern = r'(?:^|\s)(9\d{8})(?:\s|$)'
        matches = re.finditer(pattern, self.text, re.MULTILINE)

        for match in matches:
            phones.append(match.group(1))

        return list(set(phones))[:2]

    def extract_all(self) -> Dict:
        """Extrae toda la información del PDF de Crecer."""
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
        ubicacion = self.extract_ubicacion_geografica()

        return {
            'tipoPersona': tipo_persona,
            'razonSocial': nombre or "",
            'tipoDocumento': tipo_documento,
            'numeroDocumento': numero_documento,
            'direccion': self.extract_direccion() or "",
            'distrito': ubicacion['distrito'],
            'provincia': ubicacion['provincia'],
            'departamento': ubicacion['departamento'],
            'email': self.extract_email() or "",
            'telefono1': telefonos[0] if len(telefonos) > 0 else "",
            'telefono2': telefonos[1] if len(telefonos) > 1 else "",
        }
