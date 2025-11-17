from typing import Dict, List

def get_dashboard_data() -> Dict[str, List[int]]:
    months = [
        "Enero","Febrero","Marzo","Abril","Mayo","Junio",
        "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
    ]
    totals = [800,650,680,420,700,720,980,860,820,900,1050,780]
    title = "Pólizas Pendientes de Renovación 2025"
    return {"months": months, "totals": totals, "title": title}