from models.db import get_connection
import datetime

def _birthday_for_year(fecha_nacimiento, year):
    """Construye la fecha de cumpleanos para un anio; 29/02 cae a 28/02 en anios no bisiestos."""
    if fecha_nacimiento.month == 2 and fecha_nacimiento.day == 29:
        try:
            return datetime.date(year, 2, 29)
        except ValueError:
            return datetime.date(year, 2, 28)
    return datetime.date(year, fecha_nacimiento.month, fecha_nacimiento.day)


def get_cumpleanos_data(mes=None, estado=None, dias=7, orden='calendario'):
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

        cur.execute(query, params)
        db_rows = cur.fetchall()
        cur.close()
        cnx.close()
        
        today = datetime.date.today()
        try:
            dias_proximos = int(dias)
        except (TypeError, ValueError):
            dias_proximos = 7
        dias_proximos = max(1, min(dias_proximos, 60))

        estado_solicitado = (estado or '').strip().lower()

        for dr in db_rows:
            f_nac = dr.get('fecha_nacimiento')
            edad_actual = None
            dia_nac = None
            mes_nac = None
            fec_str = ""
            fecha_proximo_cumple = None
            dias_para_cumple = None
            estado_cumple = ''
            
            if f_nac:
                # Calcular edad actual cumplida
                # True/False se convierte en 1/0 para la resta
                edad_actual = today.year - f_nac.year - int((today.month, today.day) < (f_nac.month, f_nac.day))
                
                dia_nac = f_nac.day
                mes_nac = f_nac.month

                cumple_este_anio = _birthday_for_year(f_nac, today.year)
                if cumple_este_anio < today:
                    fecha_proximo_cumple = _birthday_for_year(f_nac, today.year + 1)
                else:
                    fecha_proximo_cumple = cumple_este_anio

                dias_para_cumple = (fecha_proximo_cumple - today).days
                if dias_para_cumple == 0:
                    estado_cumple = 'hoy'
                elif dias_para_cumple <= dias_proximos:
                    estado_cumple = 'proximo'
                elif fecha_proximo_cumple.month == today.month:
                    estado_cumple = 'mes_actual'
                else:
                    estado_cumple = 'futuro'
                
                if hasattr(f_nac, 'strftime'):
                    fec_str = f_nac.strftime('%d-%m-%Y')
                else:
                    fec_str = str(f_nac)

            if estado_solicitado:
                if estado_solicitado == 'proximos':
                    if not (dias_para_cumple is not None and 1 <= dias_para_cumple <= dias_proximos):
                        continue
                elif estado_solicitado == 'hoy':
                    if dias_para_cumple != 0:
                        continue
                elif estado_solicitado == 'mes_actual':
                    if mes_nac != today.month:
                        continue
                elif estado_solicitado == 'todos':
                    pass
                elif estado_cumple != estado_solicitado:
                    continue

            rows.append({
                'idCliente': dr.get('idCliente'),
                'razon_social': dr.get('razon_social'),
                'tipo_documento': dr.get('tipo_documento'),
                'numero_documento': dr.get('numero_documento'),
                'fecha_nacimiento': fec_str,
                'dia': dia_nac,
                'mes': mes_nac,
                'edad': edad_actual,
                'fecha_proximo_cumple': fecha_proximo_cumple.strftime('%d-%m-%Y') if fecha_proximo_cumple else '',
                'dias_para_cumple': dias_para_cumple,
                'estado_cumple': estado_cumple,
                'email': dr.get('email'),
                'telefono': dr.get('telefono') or dr.get('celular', '')
            })

        if (orden or '').strip().lower() == 'cercania':
            rows.sort(key=lambda x: (x.get('dias_para_cumple') is None, x.get('dias_para_cumple') or 9999, x.get('mes') or 13, x.get('dia') or 32))
            
    except Exception as e:
        print(f"Error en get_cumpleanos_data: {e}")
        rows = []

    return rows

