from typing import Dict, List, Any
from models.db import get_connection
from datetime import datetime
from flask import session
from utils.rbac import Roles

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
        'total_policies': 0,
        'total_clients': 0,
        'active_clients': 0,
        'last_client_id': 0,
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

        user_filter = ""
        user_filter_args = []

        client_where = "WHERE 1=1"
        client_where_args = []

        if session.get('role_name') == Roles.SUB_AGENTE:
            user = session.get('user')
            nombre_usuario = user
            try:
                cur.execute(
                    "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) FROM usuarios WHERE username = %s LIMIT 1",
                    (user,),
                )
                u_row = cur.fetchone()
                if u_row and u_row[0]:
                    nombre_usuario = u_row[0]
            except Exception:
                nombre_usuario = user

            user_filter = " AND (LOWER(TRIM(sub_agente)) = LOWER(TRIM(%s)) OR LOWER(TRIM(sub_agente)) = LOWER(TRIM(%s))) "
            user_filter_args = [user, nombre_usuario]

            client_where += " AND (LOWER(TRIM(subagente)) = LOWER(TRIM(%s)) OR LOWER(TRIM(subagente)) = LOWER(TRIM(%s))) "
            client_where_args = [user, nombre_usuario]
        
        # 1. Total Clientes
        try:
            cur.execute(f"SELECT COUNT(*) FROM clientes {client_where}", client_where_args)
            res = cur.fetchone()
            if res: cards['total_clients'] = res[0]
        except Exception: pass

        # 1b. Clientes Activos
        try:
            cur.execute(f"SELECT COUNT(*) FROM clientes WHERE activo = 1" + (client_where.replace("WHERE 1=1", " AND (1=1)") if "1=1" in client_where else ""), client_where_args)
            res = cur.fetchone()
            if res: cards['active_clients'] = res[0]
        except Exception: pass

        # 1c. Último ID Cliente
        try:
            cur.execute("SELECT MAX(idCliente) FROM clientes")
            res = cur.fetchone()
            if res and res[0] is not None: cards['last_client_id'] = int(res[0])
        except Exception: pass
        
        # 2. Pólizas Activas (vigencia_hasta >= hoy)
        try:
            # Note: user_filter starts with AND, so we need WHERE clause first
            sql = f"SELECT COUNT(*) FROM polizas WHERE activo = 1 AND anulado = 0 AND vig_hasta >= CURDATE() {user_filter}"
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            if res: cards['active_policies'] = res[0]
        except Exception: pass
        
        # 2b. Pólizas Registradas (total no anuladas)
        try:
            sql = f"SELECT COUNT(*) FROM polizas WHERE anulado = 0 {user_filter}"
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            if res: cards['total_policies'] = res[0]
        except Exception: pass
        
        # 3. Renovaciones Pendientes (próximo mes)
        # vigencia_hasta BETWEEN FirstDayNextMonth AND LastDayNextMonth
        try:
            # Simplificado: entre hoy y hoy+30 días
            sql = f"SELECT COUNT(*) FROM polizas WHERE activo = 1 AND anulado = 0 AND vig_hasta BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY) {user_filter}"
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            if res: cards['pending_renewals'] = res[0]
        except Exception: pass
        
        # 4. Producción (Mes Actual vs Mes Anterior)
        try:
            # Mes Actual
            sql = f"""
                SELECT SUM(COALESCE(CAST(REPLACE(imp_compania, ',', '.') AS DECIMAL(15,2)), 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE()) 
                  AND YEAR(vig_desde) = YEAR(CURDATE())
            """
            cur.execute(sql)
            curr_res = cur.fetchone()
            curr_prod = float(curr_res[0] or 0)
            
            # Mes Anterior
            sql = f"""
                SELECT SUM(COALESCE(CAST(REPLACE(imp_compania, ',', '.') AS DECIMAL(15,2)), 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) 
                  AND YEAR(vig_desde) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
            """
            cur.execute(sql)
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

        # 5. Primas Netas y Comisiones (Soles y Dólares)
        try:
            sql = f"""
                SELECT SUM(COALESCE(CAST(REPLACE(imp_compania, ',', '.') AS DECIMAL(15,2)), 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE())
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND (moneda LIKE 'S%%' OR moneda = 'PEN')
            """
            cur.execute(sql)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['prima_neta_soles'] = f"{val:,.2f}"

            sql = f"""
                SELECT SUM(COALESCE(CAST(REPLACE(imp_compania, ',', '.') AS DECIMAL(15,2)), 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE())
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND (moneda LIKE 'D%%' OR moneda LIKE 'U%%' OR moneda = 'USD')
            """
            cur.execute(sql)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['prima_neta_dolares'] = f"{val:,.2f}"

            sql = f"""
                SELECT SUM(COALESCE(CAST(REPLACE(imp_compania, ',', '.') AS DECIMAL(15,2)), 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE())
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND (moneda LIKE 'S%%' OR moneda = 'PEN')
            """
            cur.execute(sql)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['comision_soles'] = f"{val:,.2f}"

            sql = f"""
                SELECT SUM(COALESCE(CAST(REPLACE(imp_compania, ',', '.') AS DECIMAL(15,2)), 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE())
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND (moneda LIKE 'D%%' OR moneda LIKE 'U%%' OR moneda = 'USD')
            """
            cur.execute(sql)
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

        user_filter = ""
        user_filter_args = []

        if session.get('role_name') == Roles.SUB_AGENTE:
            pass
        
        # Obtener producción de los últimos 12 meses usando imp_compania y vig_desde
        # Query puede variar según versión de MySQL, usaremos un loop simple en python para llenar huecos
        # O query agrupada
        sql = f"""
            SELECT 
                vig_desde, 
                imp_compania
            FROM polizas
            WHERE vig_desde IS NOT NULL
              AND vig_desde BETWEEN DATE('2025-12-01') AND DATE('2026-12-31')
            ORDER BY vig_desde ASC
        """
        cur.execute(sql)
        rows = cur.fetchall() or []
        
        data_map = {}
        for r in rows:
            d = r[0]
            val_raw = r[1]
            try:
                val = float(str(val_raw).replace(',', '.')) if val_raw is not None else 0.0
            except Exception:
                val = 0.0
            key = f"{d.year}-{d.month:02d}"
            data_map[key] = data_map.get(key, 0.0) + val
        
        # Generar etiquetas y totales para 2025-12 a 2026-12
        start_year, start_month = 2025, 12
        end_year, end_month = 2026, 12
        y, m = start_year, start_month
        meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        while True:
            key = f"{y}-{m:02d}"
            months_labels.append(f"{meses[m-1]} {y}")
            totals_data.append(data_map.get(key, 0.0))
            if y == end_year and m == end_month:
                break
            m += 1
            if m > 12:
                m = 1
                y += 1
            
        cur.close()
        cnx.close()
    except Exception as e:
        print(f"[Dashboard] Error fetching chart data: {e}")
        # Fallback data
        months_labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        totals_data = [0]*12

    return {"months": months_labels, "totals": totals_data, "title": "Producción Anual"}
