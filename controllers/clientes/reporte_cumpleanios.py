from models.db import get_connection
import datetime

def get_cumpleanos_data(mes=None):
    print(f"DEBUG: get_cumpleanos_data mes={mes}")
    rows = []
    try:
        cnx = get_connection()
        cur = cnx.cursor(dictionary=True)
        
        # Consulta para obtener clientes activos con fecha de nacimiento
        # Seleccionamos: razon social, numero de documento, fecha de nacimiento, email, telefono
        query = """
            SELECT 
                idCliente, 
                razon_social, 
                tipo_documento, 
                numero_documento, 
                fecha_nacimiento,
                email,
                telefono,
                celular
            FROM clientes 
            WHERE (activo = 1 OR activo IS NULL) AND fecha_nacimiento IS NOT NULL
        """
        
        params = []
        if mes and str(mes).isdigit():
            m = int(mes)
            if 1 <= m <= 12:
                # Filtrar solo por el mes indicado
                query += " AND MONTH(fecha_nacimiento) = %s"
                params.append(m)
        
        # Ordenar por mes y día para ver los cumpleaños en orden de calendario
        query += " ORDER BY MONTH(fecha_nacimiento), DAY(fecha_nacimiento)"

        print(f"DEBUG: query={query} params={params}")
        cur.execute(query, params)
        db_rows = cur.fetchall()
        print(f"DEBUG: found rows count={len(db_rows)}")
        cur.close()
        cnx.close()
        
        today = datetime.date.today()

        for dr in db_rows:
            f_nac = dr.get('fecha_nacimiento')
            edad_actual = None
            dia_nac = None
            mes_nac = None
            fec_str = ""
            
            if f_nac:
                # Calcular edad actual cumplida
                # True/False se convierte en 1/0 para la resta
                edad_actual = today.year - f_nac.year - int((today.month, today.day) < (f_nac.month, f_nac.day))
                
                dia_nac = f_nac.day
                mes_nac = f_nac.month
                
                if hasattr(f_nac, 'strftime'):
                    fec_str = f_nac.strftime('%d-%m-%Y')
                else:
                    fec_str = str(f_nac)

            rows.append({
                'idCliente': dr.get('idCliente'),
                'razon_social': dr.get('razon_social'),
                'tipo_documento': dr.get('tipo_documento'),
                'numero_documento': dr.get('numero_documento'),
                'fecha_nacimiento': fec_str,
                'dia': dia_nac,
                'mes': mes_nac,
                'edad': edad_actual,
                'email': dr.get('email'),
                'telefono': dr.get('telefono') or dr.get('celular', '')
            })
            
    except Exception as e:
        print(f"Error en get_cumpleanos_data: {e}")
        rows = []

    return rows

