from typing import Dict, List, Any
from models.db import get_connection
from datetime import datetime

def get_rows() -> List[dict]:
    # Placeholder for table rows if needed, or we can fetch latest policies
    return [
        {"id": 1, "nombre": "Cliente Demo 1", "estado": "Activo"},
        {"id": 2, "nombre": "Cliente Demo 2", "estado": "Pendiente"},
        {"id": 3, "nombre": "Cliente Demo 3", "estado": "Suspendido"},
        {"id": 4, "nombre": "Cliente Demo 4", "estado": "Activo"},
        {"id": 5, "nombre": "Cliente Demo 5", "estado": "Pendiente"},
    ]

def get_dashboard_cards() -> Dict[str, Any]:
    cards = {
        'total_production': '$0.00',
        'prod_diff': 0,
        'active_policies': 0,
        'total_clients': 0,
        'pending_renewals': 0,
        # New cards
        'prima_neta_soles': '0.00',
        'prima_neta_dolares': '0.00',
        'comision_soles': '0.00',
        'comision_dolares': '0.00'
    }
    
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        
        # 1. Total Clientes
        try:
            cur.execute("SELECT COUNT(*) FROM clientes")
            res = cur.fetchone()
            if res: cards['total_clients'] = res[0]
        except Exception: pass
        
        # 2. Pólizas Activas (vigencia_hasta >= hoy)
        try:
            cur.execute("SELECT COUNT(*) FROM polizas WHERE vig_hasta >= CURDATE()")
            res = cur.fetchone()
            if res: cards['active_policies'] = res[0]
        except Exception: pass
        
        # 3. Renovaciones Pendientes (próximo mes)
        # vigencia_hasta BETWEEN FirstDayNextMonth AND LastDayNextMonth
        try:
            # Simplificado: entre hoy y hoy+30 días
            cur.execute("SELECT COUNT(*) FROM polizas WHERE vig_hasta BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)")
            res = cur.fetchone()
            if res: cards['pending_renewals'] = res[0]
        except Exception: pass
        
        # 4. Producción (Mes Actual vs Mes Anterior)
        # Asumiendo prima_total como campo de monto y fecha_emision como fecha
        # Si no existe prima_total, usar prima_neta
        try:
            # Mes Actual
            cur.execute("""
                SELECT SUM(prima_total) FROM polizas 
                WHERE MONTH(fecha_emision) = MONTH(CURDATE()) 
                  AND YEAR(fecha_emision) = YEAR(CURDATE())
            """)
            curr_res = cur.fetchone()
            curr_prod = float(curr_res[0] or 0)
            
            # Mes Anterior
            cur.execute("""
                SELECT SUM(prima_total) FROM polizas 
                WHERE MONTH(fecha_emision) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) 
                  AND YEAR(fecha_emision) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
            """)
            prev_res = cur.fetchone()
            prev_prod = float(prev_res[0] or 0)
            
            cards['total_production'] = f"${curr_prod:,.2f}"
            
            if prev_prod > 0:
                diff = ((curr_prod - prev_prod) / prev_prod) * 100
                cards['prod_diff'] = round(diff, 1)
            else:
                cards['prod_diff'] = 100 if curr_prod > 0 else 0
                
        except Exception as e:
            print(f"[Dashboard] Error calculating production: {e}")
            pass

        # 5. Primas Netas y Comisiones (Soles y Dólares) - Mes Actual
        # Se asume moneda: 'PEN'/'Soles' y 'USD'/'Dólares'
        # Se asume campos: prima_neta, imp_subagente (comision)
        try:
            # Prima Neta Soles
            cur.execute("""
                SELECT SUM(prima_neta) FROM polizas 
                WHERE (moneda LIKE 'S%' OR moneda = 'PEN')
                  AND MONTH(fecha_emision) = MONTH(CURDATE()) 
                  AND YEAR(fecha_emision) = YEAR(CURDATE())
            """)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['prima_neta_soles'] = f"{val:,.2f}"

            # Prima Neta Dólares
            cur.execute("""
                SELECT SUM(prima_neta) FROM polizas 
                WHERE (moneda LIKE 'D%' OR moneda LIKE 'U%' OR moneda = 'USD')
                  AND MONTH(fecha_emision) = MONTH(CURDATE()) 
                  AND YEAR(fecha_emision) = YEAR(CURDATE())
            """)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['prima_neta_dolares'] = f"{val:,.2f}"

            # Comisión Soles (imp_subagente)
            cur.execute("""
                SELECT SUM(imp_subagente) FROM polizas 
                WHERE (moneda LIKE 'S%' OR moneda = 'PEN')
                  AND MONTH(fecha_emision) = MONTH(CURDATE()) 
                  AND YEAR(fecha_emision) = YEAR(CURDATE())
            """)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['comision_soles'] = f"{val:,.2f}"

            # Comisión Dólares (imp_subagente)
            cur.execute("""
                SELECT SUM(imp_subagente) FROM polizas 
                WHERE (moneda LIKE 'D%' OR moneda LIKE 'U%' OR moneda = 'USD')
                  AND MONTH(fecha_emision) = MONTH(CURDATE()) 
                  AND YEAR(fecha_emision) = YEAR(CURDATE())
            """)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['comision_dolares'] = f"{val:,.2f}"

        except Exception as e:
            print(f"[Dashboard] Error calculating premiums/commissions: {e}")

        cur.close()
        cnx.close()
    except Exception as e:
        print(f"[Dashboard] Error fetching cards data: {e}")
        
    return cards

def get_dashboard_data() -> Dict[str, Any]:
    # Chart data: Last 12 months production
    months_labels = []
    totals_data = []
    
    try:
        cnx = get_connection()
        cur = cnx.cursor()
        
        # Obtener producción de los últimos 12 meses
        # Query puede variar según versión de MySQL, usaremos un loop simple en python para llenar huecos
        # O query agrupada
        cur.execute("""
            SELECT 
                DATE_FORMAT(fecha_emision, '%Y-%m') as m, 
                SUM(prima_total) as total
            FROM polizas
            WHERE fecha_emision >= DATE_SUB(CURDATE(), INTERVAL 11 MONTH)
            GROUP BY DATE_FORMAT(fecha_emision, '%Y-%m')
            ORDER BY m ASC
        """)
        rows = cur.fetchall() or []
        
        data_map = {r[0]: float(r[1] or 0) for r in rows}
        
        # Generar últimos 12 meses labels
        curr = datetime.now()
        for i in range(11, -1, -1):
            d = curr.replace(day=1) # Aproximación, mejor usar relativedelta si estuviera disponible
            # Hack simple para restar meses
            year = curr.year
            month = curr.month - i
            while month <= 0:
                month += 12
                year -= 1
            
            key = f"{year}-{month:02d}"
            # Label legible: "Ene 2025"
            label_obj = datetime(year, month, 1)
            # Spanish months hardcoded to avoid locale issues
            meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
            label = f"{meses[month-1]} {year}"
            
            months_labels.append(label)
            totals_data.append(data_map.get(key, 0.0))
            
        cur.close()
        cnx.close()
    except Exception as e:
        print(f"[Dashboard] Error fetching chart data: {e}")
        # Fallback data
        months_labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        totals_data = [0]*12

    return {"months": months_labels, "totals": totals_data, "title": "Producción Anual"}