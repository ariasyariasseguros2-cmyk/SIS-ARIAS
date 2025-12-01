from typing import Dict, List

def get_filters() -> Dict[str, List[Dict[str, str]]]:
    # Datos de ejemplo; cámbialos por consultas a BD si corresponde
    return {
        "companias": [
            {"id": "mapfre", "nombre": "MAPFRE"},
            {"id": "positiva", "nombre": "La Positiva"},
            {"id": "pacifico", "nombre": "Pacífico"},
        ],
        "ramos": [
            {"id": "autos", "nombre": "AUTOS"},
            {"id": "vida", "nombre": "VIDA"},
            {"id": "eps", "nombre": "EPS"},
            {"id": "hogar", "nombre": "HOGAR"},
        ],
        "usuarios": [
            {"id": "jramos", "nombre": "Jhordiño Ramos"},
            {"id": "marias", "nombre": "María Santos"},
            {"id": "cvaldez", "nombre": "Carlos Valdez"},
        ],
        "subagentes": [
            {"id": "sub01", "nombre": "SUB01"},
            {"id": "sub02", "nombre": "SUB02"},
            {"id": "sub03", "nombre": "SUB03"},
        ],
        "estados": [
            {"id": "general", "nombre": "GENERAL"},
            {"id": "vigente", "nombre": "VIGENTE"},
            {"id": "vencida", "nombre": "VENCIDA"},
        ],
        "grupos_economicos": [
            {"id": "ge01", "nombre": "Grupo Económico 01"},
            {"id": "ge02", "nombre": "Grupo Económico 02"},
        ],
        "grupos_riesgo": [
            {"id": "alto", "nombre": "ALTO"},
            {"id": "medio", "nombre": "MEDIO"},
            {"id": "bajo", "nombre": "BAJO"},
        ],
        "incluye_endosos": [
            {"id": "NO", "nombre": "NO"},
            {"id": "SI", "nombre": "SI"},
        ],
    }