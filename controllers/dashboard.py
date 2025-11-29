from typing import Dict, List

def get_rows() -> List[dict]:
    return [
        {"id": 1, "nombre": "Cliente Demo 1", "estado": "Activo"},
        {"id": 2, "nombre": "Cliente Demo 2", "estado": "Pendiente"},
        {"id": 3, "nombre": "Cliente Demo 3", "estado": "Suspendido"},
        {"id": 4, "nombre": "Cliente Demo 4", "estado": "Activo"},
        {"id": 5, "nombre": "Cliente Demo 5", "estado": "Pendiente"},
    ]

def get_dashboard_data() -> Dict[str, List[int]]:
    months = [
        "Enero","Febrero","Marzo","Abril","Mayo","Junio",
        "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
    ]
    totals = [800,650,680,420,700,720,980,860,820,900,1050,780]
    title = "Pólizas Pendientes de Renovación 2025"
    return {"months": months, "totals": totals, "title": title}