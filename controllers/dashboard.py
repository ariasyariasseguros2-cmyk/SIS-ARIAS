from typing import Dict, List, Any
from models.db import get_connection
from datetime import datetime, date
from flask import session, url_for
from utils.rbac import Roles


def get_expired_policy_notifications(limit: int = 10) -> List[dict]:
    """Retorna notificaciones de polizas vencidas para la campana del layout."""
    if not session.get('user'):
        return []

    safe_limit = max(1, min(int(limit or 10), 50))
    notifications: List[dict] = []

    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)

        user_filter = ""
        user_filter_args: List[Any] = []

        if session.get('role_name') == Roles.SUB_AGENTE:
            user = session.get('user')
            nombre_usuario = user
            try:
                cur.execute(
                    "SELECT COALESCE(NULLIF(TRIM(nombre), ''), username) AS nombre FROM usuarios WHERE username = %s LIMIT 1",
                    (user,),
                )
                u_row = cur.fetchone() or {}
                if u_row.get('nombre'):
                    nombre_usuario = u_row['nombre']
            except Exception:
                nombre_usuario = user

            user_filter = (
                " AND ("
                "LOWER(TRIM(REPLACE(CONVERT(sub_agente USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(sub_agente USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(usuario_registro USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(usuario_registro USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s))"
                ") "
            )
            user_filter_args = [user, nombre_usuario, user, nombre_usuario]

        sql = f"""
            SELECT
                idPoliza,
                cliente_id,
                COALESCE(
                    CAST(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) AS CHAR),
                    CAST(AES_DECRYPT(poliza, @SIS_KEY) AS CHAR),
                    poliza
                ) AS poliza,
                CASE
                    WHEN vig_hasta < CURDATE() THEN 'VENCIDA'
                    ELSE 'POR_VENCER'
                END AS notif_tipo,
                vig_hasta
            FROM polizas
            WHERE COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
              AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0'
              AND vig_hasta IS NOT NULL
              AND (
                    vig_hasta < CURDATE()
                    OR (
                        vig_hasta >= CURDATE()
                        AND YEAR(vig_hasta) = YEAR(CURDATE())
                        AND MONTH(vig_hasta) = MONTH(CURDATE())
                    )
                  )
              {user_filter}
            ORDER BY
                CASE WHEN vig_hasta < CURDATE() THEN 0 ELSE 1 END,
                vig_hasta ASC
            LIMIT %s
        """
        cur.execute(sql, [*user_filter_args, safe_limit])
        rows = cur.fetchall() or []
        cur.close()
        cnx.close()

        today = date.today()
        for r in rows:
            poliza_num = (r.get('poliza') or '').strip() or f"ID {r.get('idPoliza')}"
            vig_hasta = r.get('vig_hasta')
            notif_tipo = (r.get('notif_tipo') or 'VENCIDA').upper()

            vig_date = None
            if isinstance(vig_hasta, datetime):
                vig_date = vig_hasta.date()
            elif isinstance(vig_hasta, date):
                vig_date = vig_hasta

            if vig_date:
                fecha_txt = vig_date.strftime('%d/%m/%Y')
                if notif_tipo == 'POR_VENCER':
                    dias = max(0, (vig_date - today).days)
                    time_txt = "Vence hoy" if dias == 0 else (f"Vence en {dias} dia" if dias == 1 else f"Vence en {dias} dias")
                    message_txt = f"Poliza {poliza_num} por vencer el {fecha_txt}"
                else:
                    dias = max(0, (today - vig_date).days)
                    time_txt = f"Hace {dias} dia" if dias == 1 else f"Hace {dias} dias"
                    message_txt = f"Poliza {poliza_num} vencida el {fecha_txt}"
            else:
                fecha_txt = str(vig_hasta or '-')
                if notif_tipo == 'POR_VENCER':
                    time_txt = "Por vencer"
                    message_txt = f"Poliza {poliza_num} por vencer el {fecha_txt}"
                else:
                    time_txt = "Vencida"
                    message_txt = f"Poliza {poliza_num} vencida el {fecha_txt}"

            notifications.append({
                'message': message_txt,
                'time': time_txt,
                'poliza_num': poliza_num,
                'notif_tipo': 'por_vencer' if notif_tipo == 'POR_VENCER' else 'vencida',
                'url': url_for('main.open_polizas_from_notification', poliza_id=r.get('idPoliza')),
            })
    except Exception as e:
        print(f"[notifications] Error loading expired policies: {e}")
        return []

    return notifications

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
        'comision_dolares': '0.00',
        'total_commission': '$0.00',
        'comision_diff': 0
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

            user_filter = (
                " AND ("
                "LOWER(TRIM(REPLACE(CONVERT(sub_agente USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(sub_agente USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(usuario_registro USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(usuario_registro USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s))"
                ") "
            )
            user_filter_args = [user, nombre_usuario, user, nombre_usuario]

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
            sql = f"SELECT COUNT(*) FROM polizas WHERE COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1' AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0' AND vig_hasta >= CURDATE() {user_filter}"
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            if res: cards['active_policies'] = res[0]
        except Exception: pass
        
        # 2b. Pólizas Registradas (no anuladas; excluye eliminadas lógicamente)
        try:
            sql = f"SELECT COUNT(*) FROM polizas WHERE COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1' AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0' {user_filter}"
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            if res: cards['total_policies'] = res[0]
        except Exception: pass
        
        # 3. Renovaciones Pendientes (próximo mes)
        # vigencia_hasta BETWEEN FirstDayNextMonth AND LastDayNextMonth
        try:
            # Simplificado: entre hoy y hoy+30 días
            sql = f"SELECT COUNT(*) FROM polizas WHERE COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1' AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0' AND vig_hasta BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY) {user_filter}"
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            if res: cards['pending_renewals'] = res[0]
        except Exception: pass
        
        # 4. Producción y Comisión (Mes Actual vs Mes Anterior)
        try:
            # Mes Actual - Producción
            sql = f"""
                SELECT SUM(COALESCE(prima_neta, 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE()) 
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0' {user_filter}
            """
            cur.execute(sql, user_filter_args)
            curr_res = cur.fetchone()
            curr_prod = float(curr_res[0] or 0)
            
            # Mes Anterior - Producción
            sql = f"""
                SELECT SUM(COALESCE(prima_neta, 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) 
                  AND YEAR(vig_desde) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0' {user_filter}
            """
            cur.execute(sql, user_filter_args)
            prev_res = cur.fetchone()
            prev_prod = float(prev_res[0] or 0)
            
            cards['total_production'] = f"${curr_prod:,.2f}"
            
            if prev_prod > 0:
                diff = ((curr_prod - prev_prod) / prev_prod) * 100
                cards['prod_diff'] = round(diff, 1)
            else:
                cards['prod_diff'] = 100 if curr_prod > 0 else 0

            # Mes Actual - Comisión
            sql = f"""
                SELECT SUM(COALESCE(imp_compania, 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE()) 
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0' {user_filter}
            """
            cur.execute(sql, user_filter_args)
            curr_com_res = cur.fetchone()
            curr_com = float(curr_com_res[0] or 0)

            # Mes Anterior - Comisión
            sql = f"""
                SELECT SUM(COALESCE(imp_compania, 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) 
                  AND YEAR(vig_desde) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0' {user_filter}
            """
            cur.execute(sql, user_filter_args)
            prev_com_res = cur.fetchone()
            prev_com = float(prev_com_res[0] or 0)

            cards['total_commission'] = f"${curr_com:,.2f}"

            if prev_com > 0:
                diff_com = ((curr_com - prev_com) / prev_com) * 100
                cards['comision_diff'] = round(diff_com, 1)
            else:
                cards['comision_diff'] = 100 if curr_com > 0 else 0
                
        except Exception as e:
            print(f"[Dashboard] Error calculating production/commission metrics: {e}")
            pass

        # 5. Primas Netas y Comisiones por Moneda
        try:
            moneda_norm = "UPPER(REPLACE(REPLACE(TRIM(REPLACE(CONVERT(moneda USING latin1), _latin1 0xA0, ' ')), ' ', ''), '.', ''))"
            moneda_bucket = (
                f"CASE "
                f"WHEN {moneda_norm} IN ('US$', 'USD', '$', 'DOLARES') OR {moneda_norm} LIKE 'DOL%' THEN 'US$' "
                f"WHEN {moneda_norm} IN ('S/', 'SOLES', 'PEN') OR {moneda_norm} LIKE 'S/%' OR {moneda_norm} LIKE 'SOL%' THEN 'S/' "
                f"ELSE {moneda_norm} "
                f"END"
            )
            sql = f"""
                SELECT SUM(COALESCE(prima_neta, 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE())
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0'
                  AND {moneda_bucket} = 'S/'
                  {user_filter}
            """
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['prima_neta_soles'] = f"{val:,.2f}"

            sql = f"""
                SELECT SUM(COALESCE(prima_neta, 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE())
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0'
                  AND {moneda_bucket} = 'US$'
                  {user_filter}
            """
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['prima_neta_dolares'] = f"{val:,.2f}"

            sql = f"""
                SELECT SUM(COALESCE(imp_compania, 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE())
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0'
                  AND {moneda_bucket} = 'S/'
                  {user_filter}
            """
            cur.execute(sql, user_filter_args)
            res = cur.fetchone()
            val = float(res[0] or 0)
            cards['comision_soles'] = f"{val:,.2f}"

            sql = f"""
                SELECT SUM(COALESCE(imp_compania, 0)) FROM polizas 
                WHERE vig_desde IS NOT NULL
                  AND MONTH(vig_desde) = MONTH(CURDATE())
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0'
                  AND {moneda_bucket} = 'US$'
                  {user_filter}
            """
            cur.execute(sql, user_filter_args)
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
    # Chart data: prima neta y comision mensual del año actual
    months_labels = []
    
    totals_prima_soles = []
    totals_comision_soles = []
    totals_prima_total_soles = []
    totals_prima_usd = []
    totals_comision_usd = []
    totals_prima_total_usd = []
    chart_error = None
    
    try:
        cnx = get_connection()
        cur = cnx.cursor()

        user_filter = ""
        user_filter_args = []

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

            user_filter = (
                " AND ("
                "LOWER(TRIM(REPLACE(CONVERT(sub_agente USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(sub_agente USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(usuario_registro USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s)) "
                "OR LOWER(TRIM(REPLACE(CONVERT(usuario_registro USING latin1), _latin1 0xA0, ' '))) = LOWER(TRIM(%s))"
                ") "
            )
            user_filter_args = [user, nombre_usuario, user, nombre_usuario]

        moneda_norm = "UPPER(REPLACE(REPLACE(TRIM(REPLACE(CONVERT(p.moneda USING latin1), _latin1 0xA0, ' ')), ' ', ''), '.', ''))"
        moneda_bucket = (
            f"CASE "
            f"WHEN {moneda_norm} IN ('US$', 'USD', '$', 'DOLARES') OR {moneda_norm} LIKE 'DOL%' THEN 'US$' "
            f"WHEN {moneda_norm} IN ('S/', 'SOLES', 'PEN') OR {moneda_norm} LIKE 'S/%' OR {moneda_norm} LIKE 'SOL%' THEN 'S/' "
            f"ELSE {moneda_norm} "
            f"END"
        )

        poliza_plain = (
            "TRIM(COALESCE("
            "CONVERT(AES_DECRYPT(FROM_BASE64(poliza), @SIS_KEY) USING utf8mb4), "
            "CONVERT(AES_DECRYPT(poliza, @SIS_KEY) USING utf8mb4), "
            "poliza"
            ") COLLATE utf8mb4_0900_ai_ci)"
        )
        recibo_plain = (
            "TRIM(COALESCE("
            "CONVERT(AES_DECRYPT(FROM_BASE64(recibo), @SIS_KEY) USING utf8mb4), "
            "CONVERT(AES_DECRYPT(recibo, @SIS_KEY) USING utf8mb4), "
            "recibo, "
            "''"
            ") COLLATE utf8mb4_0900_ai_ci)"
        )
        sql = f"""
            SELECT
                MONTH(p.vig_desde) AS mes,
                ({moneda_bucket}) AS moneda_bucketed,
                SUM(COALESCE(prima_neta, 0)) AS total_prima_neta,
                SUM(COALESCE(imp_compania, 0)) AS total_comision,
                SUM(COALESCE(prima_comercial_igv, prima_total, 0)) AS total_prima_total
            FROM polizas p
            INNER JOIN (
                SELECT
                    MAX(idPoliza) AS idPoliza
                FROM polizas
                WHERE vig_desde IS NOT NULL
                  AND YEAR(vig_desde) = YEAR(CURDATE())
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(activo USING latin1), _latin1 0xA0, ' ')), ''), '0') = '1'
                  AND COALESCE(NULLIF(TRIM(REPLACE(CONVERT(anulado USING latin1), _latin1 0xA0, ' ')), ''), '0') = '0'
                  {user_filter}
                GROUP BY ({poliza_plain}), ({recibo_plain})
            ) d ON d.idPoliza = p.idPoliza
            GROUP BY MONTH(p.vig_desde), ({moneda_bucket})
            ORDER BY MONTH(p.vig_desde)
        """
        cur.execute(sql, user_filter_args)
        rows = cur.fetchall() or []

        # Data maps for each currency
        prima_map_soles = {}
        comision_map_soles = {}
        prima_total_map_soles = {}
        prima_map_usd = {}
        comision_map_usd = {}
        prima_total_map_usd = {}

        for r in rows:
            mes = int(r[0])
            moneda = r[1]
            p_neta = float(r[2] or 0)
            comision = float(r[3] or 0)
            p_total = float(r[4] or 0)

            if moneda == 'S/':
                prima_map_soles[mes] = p_neta
                comision_map_soles[mes] = comision
                prima_total_map_soles[mes] = p_total
            elif moneda == 'US$':
                prima_map_usd[mes] = p_neta
                comision_map_usd[mes] = comision
                prima_total_map_usd[mes] = p_total
        
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        current_year = datetime.now().year
        for month_index in range(1, 13):
            months_labels.append(f"{meses[month_index - 1]} {current_year}")
            
            totals_prima_soles.append(prima_map_soles.get(month_index, 0.0))
            totals_comision_soles.append(comision_map_soles.get(month_index, 0.0))
            totals_prima_total_soles.append(prima_total_map_soles.get(month_index, 0.0))
            
            totals_prima_usd.append(prima_map_usd.get(month_index, 0.0))
            totals_comision_usd.append(comision_map_usd.get(month_index, 0.0))
            totals_prima_total_usd.append(prima_total_map_usd.get(month_index, 0.0))
            
        cur.close()
        cnx.close()
    except Exception as e:
        print(f"[Dashboard] Error fetching chart data: {e}")
        chart_error = str(e)
        # Fallback data
        current_year = datetime.now().year
        meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        months_labels = [f"{m} {current_year}" for m in meses]
        totals_prima_soles = [0] * 12
        totals_comision_soles = [0] * 12
        totals_prima_total_soles = [0] * 12
        totals_prima_usd = [0] * 12
        totals_comision_usd = [0] * 12
        totals_prima_total_usd = [0] * 12

    return {
        "error": chart_error,
        "months": months_labels,
        "totals_prima_soles": totals_prima_soles,
        "totals_comision_soles": totals_comision_soles,
        "totals_prima_total_soles": totals_prima_total_soles,
        "totals_prima_usd": totals_prima_usd,
        "totals_comision_usd": totals_comision_usd,
        "totals_prima_total_usd": totals_prima_total_usd,
        "title": "Producción vs Comisión",
    }
