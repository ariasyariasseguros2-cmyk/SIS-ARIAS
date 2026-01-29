import re
from typing import Optional, List, Dict, Any

class LaPositivaVidaParser:
    """Parser específico para La Positiva Vida."""

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """Verifica si el texto corresponde a La Positiva Vida."""
        t = text.upper()
        # Verificar logo o título específico
        # "Proforma de Cobertura" es muy específico de este documento
        # También "La Positiva Vida" en el texto
        if 'LA POSITIVA VIDA' in t:
            return True
        if 'PROFORMA DE COBERTURA' in t and 'LA POSITIVA' in t:
            return True
        return False

    def extract_ruc(self) -> Optional[str]:
        """Extrae RUC del documento."""
        # Pattern: R.U.C.: \n : 10475087611
        # Also handling typical variations
        match = re.search(r'R\.U\.C\.(?:\s*:)?\s*(?::)?\s*(\d{11})', self.text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
        
        # Try multiline if the above failed (though DOTALL should handle it, explicit structure check helps)
        # R.U.C.: 
        # : 10475087611
        match_multi = re.search(r'R\.U\.C\.(?:\s*:)?\s*\n\s*(?::)?\s*(\d{11})', self.text, re.IGNORECASE)
        if match_multi:
            return match_multi.group(1)
            
        return None

    @staticmethod
    def clean_text(text: str) -> str:
        """Limpia caracteres extraños y corrige codificación común (especialmente Ñ)."""
        if not text:
            return ""
        
        # Correcciones de encoding UTF-8 mal interpretado (Latin1)
        text = text.replace('Ã‘', 'Ñ').replace('Ã±', 'ñ')
        
        # Correcciones de CID codes específicos para Ñ
        text = text.replace('(cid:209)', 'Ñ').replace('(cid:241)', 'ñ')
        
        # Correcciones de otros caracteres comunes
        text = text.replace('Ã¡', 'á').replace('Ã©', 'é').replace('Ãí', 'í').replace('Ã³', 'ó').replace('Ãº', 'ú')
        text = text.replace('ÃÁ', 'Á').replace('Ã‰', 'É').replace('ÃÍ', 'Í').replace('Ã“', 'Ó').replace('Ãš', 'Ú')
        
        # Limpieza general de CIDs restantes
        text = re.sub(r'\(cid:\d+\)', '', text)
        
        return text.strip()

    def extract_nombre(self) -> Optional[str]:
        """Extrae Nombre/Razón Social (Contratante)."""
        # Contratante : SARAVIA TRUJILLO, JULIA
        match = re.search(r'Contratante\s*:\s*([^\n]+)', self.text, re.IGNORECASE)
        if match:
            return self.clean_text(match.group(1))
        return None

    def extract_direccion(self) -> Optional[str]:
        """Extrae Dirección."""
        print("DEBUG: Iniciando extraccion de direccion (LaPositivaVida)...")
        lines = self.text.split('\n')
        
        stop_keywords = [
            'DISTRITO', 'TELÉFONO', 'TELEFONO', 'TELØFONO', 'OFICINA', 
            'PÓLIZA', 'POLIZA', 'VIGENCIA', 'CONTRATANTE', 'ASEGURADO', 
            'GESTOR', 'MONEDA', 'RAMO', 'HASTA', 'LOCALIDAD', 'SEDE',
            'PAGINA', 'PÁGINA', 'FECHA', 'IMPORTES', 'DESCRIPCIÓN', 'DESCRIPCION',
            'WWW', '.COM', 'HTTP', 'HTTPS'
        ]

        def clean_and_validate(val: str) -> Optional[str]:
            # First apply global cleaning (encoding fixes, CID removal)
            v = LaPositivaVidaParser.clean_text(val)
            
            # Remove leading colons/dots/spaces/pipes
            v = re.sub(r'^[:\.\-\s\|]+', '', v).strip()
            
            if len(v) < 3: return None
            
            v_upper = v.upper()
            
            # Specific check for legal text (more robust)
            if 'PUEDE' in v_upper or 'PUEDEN' in v_upper: return None
            if 'TRAVÉS' in v_upper or 'TRAVES' in v_upper: return None
            if 'UBICARLAS' in v_upper: return None
            
            # Check if any stop keyword is inside the string (start of next field)
            earliest_idx = len(v)
            found_stop = False
            
            for kw in stop_keywords:
                # Check for keyword at start
                if v_upper.startswith(kw):
                    return None
                
                # Check for keyword in middle (preceded by space)
                idx = v_upper.find(' ' + kw)
                if idx != -1:
                    earliest_idx = min(earliest_idx, idx)
                    found_stop = True
            
            if found_stop:
                v = v[:earliest_idx].strip()
                if len(v) < 3: return None
                
            return v

        for i, line in enumerate(lines):
            # ANCHOR REMOVED to be more flexible with layout (e.g. indentation, hidden chars)
            # BUT added explicit exclusions for legal text lines
            if 'CAMBIO DE' in line.upper(): continue
            
            # Search for "Dirección" followed by separators (colon, space, dot, etc.)
            # Expanded wildcard {1,20}? (NON-GREEDY) to handle CID encoding like Direcci(cid:243)n
            # preventing it from eating into the value if the value contains 'n' (e.g. CENTRO)
            match = re.search(r'Direcci.{1,20}?n\s*[:\s\.\-\|]*(.*)', line, re.IGNORECASE)
            
            if match:
                raw_val = match.group(1)
                print(f"DEBUG: Linea candidata: '{line.strip()}' -> Valor raw: '{raw_val}'")
                
                # Attempt 1: Value is on the same line
                cleaned = clean_and_validate(raw_val)
                if cleaned:
                    print(f"DEBUG: Direccion encontrada en misma linea: '{cleaned}'")
                    return cleaned
                
                # Attempt 2: Value is on next lines
                print("DEBUG: Valor en linea vacio o invalido, buscando en siguientes lineas...")
                for offset in range(1, 4):
                    if i + offset < len(lines):
                        next_line = lines[i+offset]
                        cleaned_next = clean_and_validate(next_line)
                        if cleaned_next:
                            print(f"DEBUG: Direccion encontrada en linea +{offset}: '{cleaned_next}'")
                            return cleaned_next
                        else:
                            # If next line is effectively empty, keep searching
                            if not next_line.strip():
                                continue
                            # If it has content but was rejected (e.g. legal text or stop keyword), 
                            # stop searching for THIS "Dirección" match.
                            print(f"DEBUG: Linea +{offset} rechazada, deteniendo busqueda para este match: '{next_line.strip()}'")
                            break
                            
        print("DEBUG: No se encontro ninguna direccion valida.")
        return None

    def extract_distrito_info(self) -> Dict[str, str]:
        """Extrae Distrito y Departamento/Provincia si está disponible."""
        # Distrito: CHAGLLA (HUANUCO)
        info = {'distrito': '', 'departamento': 'LIMA', 'provincia': 'LIMA'}
        
        # Match "Distrito : VALUE" stopping at newline or "Localidad" or "Sede"
        match = re.search(r'Distrito\s*:\s*(.*?)(?:\s+Localidad|\s+Sede|\n|$)', self.text, re.IGNORECASE)
        if match:
            full_val = match.group(1).strip()
            full_val = self.clean_text(full_val)
            
            # Check for (DEPARTMENT) e.g. CHAGLLA (HUANUCO)
            m_dept = re.match(r'^(.*?)\s*\((.*?)\)$', full_val)
            if m_dept:
                info['distrito'] = m_dept.group(1).strip()
                dept = m_dept.group(2).strip()
                info['departamento'] = dept
                # Assume Provincia is same as Dept if not specified, or just leave as default LIMA?
                # Usually better to set Provincia = Dept if we don't know
                info['provincia'] = dept 
            else:
                info['distrito'] = full_val
        
        return info

    def extract_telefono(self) -> Optional[str]:
        """Extrae Teléfono."""
        # Teléfonos: 017654321
        match = re.search(r'Tel[ée]fonos?\s*:\s*([^\n]+)', self.text, re.IGNORECASE)
        if match:
            # Clean up text to get only numbers/separators
            raw = match.group(1).strip()
            # If there are other fields on the line like "Sede(s)"
            # Teléfonos : 017654321 Sede(s) : ...
            raw = re.split(r'\s+Sede', raw, flags=re.IGNORECASE)[0]
            return raw.strip()
        return None

    def extract_all(self) -> Dict[str, Any]:
        """Extrae toda la información disponible."""
        dist_info = self.extract_distrito_info()
        ruc = self.extract_ruc()
        
        return {
            'numeroDocumento': ruc or '',
            'razonSocial': self.extract_nombre() or '',
            'direccion': self.extract_direccion() or '',
            'distrito': dist_info['distrito'],
            'provincia': dist_info['provincia'],
            'departamento': dist_info['departamento'],
            'telefono1': self.extract_telefono() or '',
            # Default values
            'tipoPersona': 'JURIDICA' if ruc and ruc.startswith('20') else 'NATURAL',
            'tipoDocumento': 'RUC',
            'email': '',
            'telefono2': '',
            'subAgente': '',
            'contactoNombre': '',
            'contactoEmail': '',
            'contactoTelefono': '',
        }
