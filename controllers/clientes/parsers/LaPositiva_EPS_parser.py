import re
from typing import Optional, List, Dict

class LaPositivaEPSParser:
    """Parser específico para La Positiva EPS."""

    def __init__(self, text: str):
        self.text = text

    @staticmethod
    def can_parse(text: str) -> bool:
        """Verifica si el texto corresponde a La Positiva EPS."""
        # Se busca "La Positiva"
        t = text.upper()
        return 'LA POSITIVA' in t

    def extract_ruc(self) -> Optional[str]:
        """Extrae RUC del documento."""
        # RUCs a ignorar (RUC de la aseguradora)
        
        
        # Intento 1: R.U.C.: : 20607778419
        # Buscamos 'R.U.C' seguido de cualquier cosa hasta encontrar 11 dígitos
        # Iteramos sobre todas las coincidencias para encontrar una que no esté ignorada
        matches = re.finditer(r'R\.U\.C\..*?(\d{11})', self.text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            ruc = match.group(1)
            if ruc :
                return ruc
                
        # Intento 2: Buscar cualquier RUC de 11 dígitos cerca de "Contratante"
        # Esto es útil si el formato cambia
        match_contratante = re.search(r'Contratante.*?(?:RUC|R\.U\.C).*?(\d{11})', self.text, re.IGNORECASE | re.DOTALL)
        if match_contratante:
             ruc = match_contratante.group(1)
             if ruc :
                 return ruc

        return None

    def extract_nombre(self) -> Optional[str]:
        """Extrae Razón Social (Contratante)."""
        # Contratante : INVERSIONES FORESTALES MENDOZA PEREZ E.I
        # Prioridad 1: Buscar "Contratante :" explícito (formato cabecera)
        # Usamos finditer para buscar todas y filtrar las malas (como ", en adelante")
        matches = re.finditer(r'Contratante\s*:\s*([^\n]+)', self.text, re.IGNORECASE)
        
        for match in matches:
            name = match.group(1).strip()
            
            # Filtros para evitar texto legal
            if "en adelante" in name.lower(): continue
            if name.startswith(','): continue
            if len(name) < 3: continue
            
            # Limpiar si se coló algo como "Asegurado" al final
            if "Asegurado" in name:
                name = name.split("Asegurado")[0].strip()
                
            return name

        # Fallback: Buscar "Contratante" sin dos puntos, pero con cuidado
        match = re.search(r'Contratante\s+([A-Z0-9\.\s]+)(?:\n|$|Asegurado)', self.text)
        if match:
            name = match.group(1).strip()
            if "en adelante" not in name.lower() and not name.startswith(',') and len(name) > 3:
                 return name

        return None

    def extract_direccion_y_ubicacion(self) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Extrae Dirección, Distrito, Provincia, Departamento.
        Maneja el caso donde headers y valores se mezclan.
        Retorna: (direccion, distrito, provincia, departamento)
        """
        direccion = None
        distrito = None
        provincia = None
        departamento = None

        # Caso específico reportado:
        # Dirección Distrito Gestor : JR. REQUENA ... : PUCALLPA ...
        # O
        # Dirección : JR. REQUENA ...
        # Distrito : PUCALLPA ...
        
        # Estrategia: Buscar "Dirección" y capturar hasta el final de la línea o hasta encontrar "Distrito" o ":" repetido
        
        # 1. Buscar la línea que contiene la dirección real (buscando patrones de calle comunes)
        # JR. REQUENA NRO. 118 URB. CERCADO DE
        lines = self.text.split('\n')
        
        dir_line_idx = -1
        
        # Patrones comunes de dirección
        calle_patterns = [r'JR\.', r'AV\.', r'CALLE', r'PJE\.', r'CARRETERA', r'MZ\.', r'LT\.', r'URB\.']
        
        for i, line in enumerate(lines):
            # Si encontramos "Dirección" en la línea, miramos esta línea o la siguiente
            if 'DIRECCIÓN' in line.upper() and 'DISTRITO' in line.upper():
                # Es el caso de headers pegados. La siguiente línea probablemente tenga los valores pegados.
                # O están en la misma línea si el extractor lo hizo así.
                
                # Verificamos si en esta misma linea hay datos
                if ':' in line:
                    # Dirección Distrito Gestor : DATA ... : DATA ...
                    parts = line.split(':')
                    if len(parts) > 2:
                        # parts[0] -> Dirección Distrito Gestor 
                        # parts[1] -> JR. REQUENA ... (termina en DE )
                        # parts[2] -> PUCALLPA ...
                        posible_dir = parts[1].strip()
                        # Limpiar el final si se pegó el siguiente label
                        posible_dir = re.sub(r'\s*(Distrito|Gestor|Localidad).*$', '', posible_dir, flags=re.IGNORECASE)
                        # A veces "DE" queda al final si es "CERCADO DE" y el siguiente : viene del distrito
                        direccion = posible_dir
                        
                        # Ubicación en la parte 2 o 3
                        resto = ":".join(parts[2:])
                        # Buscar patrón (DIST) (DEPTO)
                        match_ub = re.search(r'([^(]+)\(([^)]+)\)\s*\(([^)]+)\)', resto)
                        if match_ub:
                            provincia = match_ub.group(1).strip()
                            distrito = match_ub.group(2).strip()
                            departamento = match_ub.group(3).strip()
                        else:
                            # Intento simple
                            distrito = parts[2].strip()
                        return direccion, distrito, provincia, departamento

                # Si no había datos en esa línea, miramos la siguiente
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    # JR. REQUENA ... : PUCALLPA ...
                    parts = next_line.split(':')
                    if len(parts) >= 2:
                         # Asumimos formato: DIRECCION : UBICACION
                         # Pero a veces el primer : falta si es comienzo de línea
                         # Caso: JR. REQUENA ... : PUCALLPA ...
                         
                         # Si empieza con :
                         first_part = parts[0].strip()
                         if not first_part and len(parts) > 1:
                             first_part = parts[1].strip() # Caso : JR...
                             
                         # Detectar dónde corta la dirección
                         # Puede que parts[0] sea la dirección si no empezó con :
                         if any(re.search(p, next_line, re.IGNORECASE) for p in calle_patterns):
                             # Es una línea de datos
                             # Intentar separar por el último : o por patrón de ubicación
                             match_ub = re.search(r'\s+:\s*([^(]+)\(([^)]+)\)\s*\(([^)]+)\)', next_line)
                             if match_ub:
                                 # Encontramos la parte de ubicación al final
                                 direccion_part = next_line[:match_ub.start()].strip()
                                 # Limpiar caracteres iniciales como :
                                 direccion = re.sub(r'^[:\s]+', '', direccion_part)
                                 
                                 provincia = match_ub.group(1).strip()
                                 distrito = match_ub.group(2).strip()
                                 departamento = match_ub.group(3).strip()
                                 return direccion, distrito, provincia, departamento
            
            # Caso standard: Dirección : CALLE ...
            elif 'DIRECCIÓN' in line.upper() and ':' in line:
                 # Dirección : JR. ...
                 parts = line.split(':', 1)
                 if len(parts) > 1:
                     direccion = parts[1].strip()
                     # Si en la misma línea está Distrito
                     if 'DISTRITO' in direccion.upper():
                         direccion = direccion.split('DISTRITO')[0].strip()

        # Si falló lo anterior, búsqueda bruta por patrón de calle
        if not direccion:
            match = re.search(r'(?:JR\.|AV\.|CALLE|PJE\.|CARRETERA)[^:\n]+', self.text, re.IGNORECASE)
            if match:
                direccion = match.group(0).strip()
                # Limpiar si capturó de más
                if ':' in direccion:
                    direccion = direccion.split(':')[0].strip()
        
        # Búsqueda bruta de ubicación (DIST) (DEPTO)
        if not distrito:
            match = re.search(r'([A-Z\s]+)\s*\(([A-Z\s]+)\)\s*\(([A-Z\s]+)\)', self.text)
            if match:
                 # Verificar que no sea parte de un texto irrelevante
                 # Generalmente PUCALLPA (CALLARIA) (UCAYALI)
                 # 1: PROVINCIA/CIUDAD, 2: DISTRITO, 3: DEPARTAMENTO
                 provincia = match.group(1).strip()
                 distrito = match.group(2).strip()
                 departamento = match.group(3).strip()

        return direccion, distrito, provincia, departamento

    def extract_telefono(self) -> Optional[str]:
        """Extrae Teléfono."""
        # Teléfonos : 017654321
        match = re.search(r'Teléfonos?\s*:?\s*(\d+)', self.text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def extract_all(self) -> Dict:
        """Ejecuta toda la extracción."""
        direccion, distrito, provincia, departamento = self.extract_direccion_y_ubicacion()
        
        return {
            'numeroDocumento': self.extract_ruc(),
            'tipoDocumento': 'RUC',
            'razonSocial': self.extract_nombre(),
            'direccion': direccion,
            'telefono1': self.extract_telefono(),
            'distrito': distrito,
            'provincia': provincia,
            'departamento': departamento,
            'tipoPersona': 'JURIDICA' # Por defecto si es RUC
        }
