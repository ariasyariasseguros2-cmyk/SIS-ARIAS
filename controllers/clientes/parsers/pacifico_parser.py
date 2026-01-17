"""
Parser especializado para PDFs de PACÍFICO SEGUROS.
Maneja formatos de Vida Ley, SCTR y facturas.
"""
import re
from typing import Dict, Optional, List


class PacificoParser:
    """Parser específico para PDFs de Pacífico Seguros."""

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """Detecta si el PDF es de Pacífico."""
        indicators = [
            r'PACÍFICO.*SEGUROS',
            r'PACIFICO.*SEGUROS',
            r'R\.U\.C\.\s*20332970411',
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in indicators)

    def extract_contratante(self) -> Optional[str]:
        """Extrae el nombre del contratante."""
        patterns = [
            # Formato factura - hasta FECHA o salto de línea
            r'CONTRATANTE\s*:\s*([A-ZÁÉÍÓÚÑ][^\n:]{5,100}?)(?:\s+FECHA|\s+RUC|\n)',
            # Formato liquidación - capturar SOLO hasta el número de cliente (evita duplicado)
            r'Contratante\s*:\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&\']{5,80}?)(?:\s+\d{5,})',
            # Fallback - hasta salto de línea pero limita a mayúsculas y espacios comunes
            r'Contratante\s*:\s*([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&\']{5,80}?)(?:\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                # Limpiar números de cliente al final
                nombre = re.sub(r'\s+\d{5,}.*$', '', nombre)
                # Limpiar "Contratante :" si aparece dentro
                nombre = re.sub(r'\s*Contratante\s*:.*$', '', nombre, flags=re.IGNORECASE)
                # Limpiar espacios extras
                nombre = re.sub(r'\s+', ' ', nombre)
                # Evitar nombres muy cortos o que sean solo números
                if len(nombre) > 5 and not nombre.isdigit():
                    return nombre.strip()
        return None

    def extract_ruc(self) -> Optional[str]:
        """Extrae el RUC del contratante."""
        # Buscar RUC cerca del contratante
        patterns = [
            r'CONTRATANTE.*?RUC.*?[NºN°:]*\s*(\d{11})',
            r'RUC Nº\s*:\s*(\d{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.DOTALL)
            if match:
                ruc = match.group(1)
                # Excluir RUC de Pacífico
                if ruc != '20332970411':
                    return ruc

        # Fallback: buscar todos los RUC y tomar el que no sea de Pacífico
        rucs_encontrados = re.findall(r'\b(\d{11})\b', self.text)
        rucs_filtrados = [ruc for ruc in rucs_encontrados if ruc != '20332970411' and ruc.startswith('20')]

        return rucs_filtrados[0] if rucs_filtrados else None

    def extract_dni(self) -> Optional[str]:
        """Extrae el DNI si es persona natural."""
        patterns = [
            r'DNI\s*[:\-]\s*(\d{8})',
            r'D\.N\.I\s*[:\-]\s*(\d{8})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_direccion(self) -> Optional[str]:
        """Extrae dirección del contratante."""
        patterns = [
            # Formato con dos puntos
            r'DIRECCI[OÓ]N\s*:\s*([^\n]{10,200}?)(?:\s+Direcci[oó]n|\s+RUC|\s+Tel[eé]fono|\n)',
            r'Direcci[oó]n\s*:\s*([^\n]{10,200}?)(?:\s+Direcci[oó]n|\s+RUC|\s+Tel[eé]fono|\n)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                direccion = match.group(1).strip()
                # Excluir direcciones de Pacífico
                if not any(x in direccion for x in ['Juan de Arona', 'San Isidro', 'PACÍFICO', 'Pacifico']):
                    # Limpiar texto duplicado como "Dirección :"
                    direccion = re.sub(r'\s*Direcci[oó]n\s*:.*$', '', direccion, flags=re.IGNORECASE)

                    # Limpiar ubicación geográfica al final
                    # Patrón 1: DISTRITO PROVINCIA DEPARTAMENTO UC (ej: MANANTAY CORONEL PORTILLO UC)
                    direccion = re.sub(r'\s+[A-ZÁÉÍÓÚÑ]{4,}\s+[A-ZÁÉÍÓÚÑ\s]{8,}?\s+UC\s*$', '', direccion, flags=re.IGNORECASE)
                    # Patrón 2: Cualquier combinación de 2-3 palabras en mayúsculas seguidas de UC
                    direccion = re.sub(r'\s+([A-ZÁÉÍÓÚÑ]{4,}\s+){1,3}UC\s*$', '', direccion, flags=re.IGNORECASE)
                    # Patrón 3: DISTRITO - PROVINCIA - DEPARTAMENTO
                    direccion = re.sub(r'\s+[A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+-\s*[A-ZÁÉÍÓÚÑ\s]+$', '', direccion, flags=re.IGNORECASE)

                    # Limpiar espacios extras
                    direccion = re.sub(r'\s+', ' ', direccion)

                    if len(direccion) > 10:
                        return direccion.strip()
        return None

    def extract_email(self) -> Optional[str]:
        """Extrae email."""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(pattern, self.text)

        # Excluir emails de Pacífico
        for email in matches:
            if 'pacifico' not in email.lower():
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

    def extract_ubicacion_geografica(self) -> Dict[str, str]:
        """Extrae distrito, provincia y departamento de la dirección."""
        # Buscar patrones comunes en direcciones de Pacífico
        # Formato: DISTRITO PROVINCIA DEPARTAMENTO UC o DISTRITO - PROVINCIA - DEPARTAMENTO
        patterns = [
            # Patrón principal: DISTRITO PROVINCIA UC (ej: MANANTAY CORONEL PORTILLO UC)
            # Captura: DISTRITO (1 palabra) + PROVINCIA (resto hasta UC)
            r'([A-ZÁÉÍÓÚÑ]{4,})\s+([A-ZÁÉÍÓÚÑ\s]+?)\s+UC',
            # Con departamento explícito: DISTRITO PROVINCIA DEPARTAMENTO
            r'([A-ZÁÉÍÓÚÑ]{4,})\s+([A-ZÁÉÍÓÚÑ\s]+?)\s+([A-ZÁÉÍÓÚÑ]{4,})\s+UC',
            # Con guiones
            r'([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)\s*-\s*([A-ZÁÉÍÓÚÑ\s]+?)(?:\s+UC|\s+Direcci[oó]n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.MULTILINE)
            if match:
                if match.lastindex == 2:
                    # Patrón 1: DISTRITO PROVINCIA UC (sin departamento explícito)
                    distrito = match.group(1).strip()
                    provincia = match.group(2).strip()

                    # Limpiar UC de la provincia ANTES de inferir
                    provincia = re.sub(r'\s*UC.*$', '', provincia, flags=re.IGNORECASE).strip()

                    # Para Perú, si no hay departamento explícito, intentar inferirlo
                    departamento = ''
                    if 'CORONEL PORTILLO' in provincia.upper():
                        departamento = 'Ucayali'
                    elif 'LIMA' in provincia.upper():
                        departamento = 'Lima'
                    # Agregar más casos según sea necesario

                elif match.lastindex == 3:
                    distrito = match.group(1).strip()
                    provincia = match.group(2).strip()
                    departamento = match.group(3).strip()

                    # Limpiar UC de provincia y departamento
                    provincia = re.sub(r'\s*UC.*$', '', provincia, flags=re.IGNORECASE).strip()
                    departamento = re.sub(r'\s*UC.*$', '', departamento, flags=re.IGNORECASE).strip()
                else:
                    continue

                # Limpiar posibles restos adicionales (Dirección, RUC, etc.)
                provincia = re.sub(r'\s*(Direcci[oó]n|RUC|Tel).*$', '', provincia, flags=re.IGNORECASE).strip()
                if departamento:
                    departamento = re.sub(r'\s*(Direcci[oó]n|RUC|Tel).*$', '', departamento, flags=re.IGNORECASE).strip()

                # Validar que no sean textos de la aseguradora
                if 'PACIFICO' not in distrito.upper() and 'SEGUROS' not in distrito.upper():
                    # Validar longitud mínima (departamento puede estar vacío si se infiere)
                    if len(distrito) >= 4 and len(provincia) >= 4:
                        return {
                            'distrito': distrito.title(),
                            'provincia': provincia.title(),
                            'departamento': departamento.title() if departamento else ''
                        }

        return {'distrito': '', 'provincia': '', 'departamento': ''}

    def extract_all(self) -> Dict:
        """Extrae toda la información del PDF de Pacífico."""
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
