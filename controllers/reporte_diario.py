from typing import Dict, List, Any
from flask import session
from models.db import get_connection
from utils.rbac import Roles

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

def get_reporte_diario_data(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Base query joining polizas and clientes (for contratante name)
        # Assuming polizas has most fields.
        # We need to adapt columns to what is needed in the report.
        sql = """
            SELECT 
                p.idPoliza,
                p.fecha_emision,
                p.poliza,
                c.razon_social as contratante,
                p.cia as compania,
                p.ramo,
                p.prima_neta,
                p.prima_comercial,
                p.comision,
                p.porcentaje_comision,
                p.moneda,
                p.vig_desde,
                p.vig_hasta,
                p.estado,
                p.sub_agente,
                p.usuario_registro
            FROM polizas p
            LEFT JOIN clientes c ON p.idCliente = c.idCliente
            WHERE 1=1
        """
        params = []

        # RLS Logic
        role = session.get('role_name')
        user = session.get('user')
        
        if role == Roles.SUB_AGENTE:
            # Filter by sub_agente (assuming sub_agente column stores username or name)
            # We'll use the same logic as in polizas.py
            cursor.execute("SELECT nombre FROM usuarios WHERE username = %s", (user,))
            u_row = cursor.fetchone()
            nombre_usuario = u_row['nombre'] if u_row else user
            
            sql += " AND (p.usuario_registro = %s OR p.sub_agente = %s)"
            params.extend([user, nombre_usuario])

        # Apply Filters
        if filters.get('desde'):
            sql += " AND p.fecha_emision >= %s"
            params.append(filters['desde'])
        
        if filters.get('hasta'):
            sql += " AND p.fecha_emision <= %s"
            params.append(filters['hasta'])

        if filters.get('poliza'):
            sql += " AND p.poliza LIKE %s"
            params.append(f"%{filters['poliza']}%")

        if filters.get('contratante'):
            sql += " AND c.razon_social LIKE %s"
            params.append(f"%{filters['contratante']}%")

        if filters.get('compania'):
            sql += " AND p.cia = %s"
            params.append(filters['compania'])
            
        if filters.get('ramo'):
            sql += " AND p.ramo = %s"
            params.append(filters['ramo'])

        if filters.get('usuario'):
             sql += " AND p.usuario_registro = %s"
             params.append(filters['usuario'])

        if filters.get('subagente'):
            # If user is SUB_AGENTE, this filter is redundant or must be validated
            if role != Roles.SUB_AGENTE:
                 sql += " AND p.sub_agente = %s"
                 params.append(filters['subagente'])

        if filters.get('estado') and filters['estado'] != 'general':
            if filters['estado'] == 'vigente':
                sql += " AND p.estado = 'VIGENTE'"
            elif filters['estado'] == 'vencida':
                 sql += " AND p.estado = 'VENCIDA'"

        # Sort by date desc
        sql += " ORDER BY p.fecha_emision DESC LIMIT 500"

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        
        # Post-process for currency formatting or extra fields if needed
        return rows

    except Exception as e:
        print(f"Error in get_reporte_diario_data: {e}")
        return []
    finally:
        conn.close()
