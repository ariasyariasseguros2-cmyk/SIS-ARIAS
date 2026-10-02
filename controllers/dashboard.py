from typing import Dict, List, Any
from models.db import get_connection
from datetime import datetime, date
from flask import session, url_for
from utils.rbac import Roles


# ============================================================
# HELPERS DEL DASHBOARD
# ============================================================
def get_rows() -> List[dict]:
    """
    Mantiene compatibilidad con route.py.
    Si actualmente no utilizas esta función para el dashboard,
    devuelve las filas básicas.
    """

    return [
        {
            "id": 1,
            "nombre": "Cliente Demo 1",
            "estado": "Activo"
        },
        {
            "id": 2,
            "nombre": "Cliente Demo 2",
            "estado": "Pendiente"
        },
        {
            "id": 3,
            "nombre": "Cliente Demo 3",
            "estado": "Suspendido"
        },
        {
            "id": 4,
            "nombre": "Cliente Demo 4",
            "estado": "Activo"
        },
        {
            "id": 5,
            "nombre": "Cliente Demo 5",
            "estado": "Pendiente"
        },
    ]


def get_dashboard_data() -> Dict[str, Any]:
    """
    Datos del gráfico del dashboard.

    Mantiene la compatibilidad con route.py.

    Genera:
    - prima neta soles
    - comisión soles
    - prima total soles
    - prima neta dólares
    - comisión dólares
    - prima total dólares

    por cada mes del año actual.
    """

    months_labels = []

    totals_prima_soles = []
    totals_comision_soles = []
    totals_prima_total_soles = []

    totals_prima_usd = []
    totals_comision_usd = []
    totals_prima_total_usd = []

    chart_error = None

    cnx = None
    cur = None

    try:

        cnx = get_connection()
        cur = cnx.cursor()

        # ====================================================
        # FILTRO DEL USUARIO
        # ====================================================

        user_filter, user_filter_args = (
            _get_dashboard_user_filter(
                cur,
                "p"
            )
        )

        # ====================================================
        # NORMALIZAR MONEDA
        # ====================================================

        moneda_norm = """
            UPPER(
                REPLACE(
                    REPLACE(
                        TRIM(
                            REPLACE(
                                CONVERT(
                                    p.moneda USING latin1
                                ),
                                _latin1 0xA0,
                                ' '
                            )
                        ),
                        ' ',
                        ''
                    ),
                    '.',
                    ''
                )
            )
        """

        moneda_bucket = f"""
            CASE

                WHEN
                    {moneda_norm} IN (
                        'US$',
                        'USD',
                        '$',
                        'DOLARES'
                    )
                    OR {moneda_norm} LIKE 'DOL%'
                THEN 'US$'

                WHEN
                    {moneda_norm} IN (
                        'S/',
                        'SOLES',
                        'PEN'
                    )
                    OR {moneda_norm} LIKE 'S/%'
                    OR {moneda_norm} LIKE 'SOL%'
                THEN 'S/'

                ELSE {moneda_norm}

            END
        """

        # ====================================================
        # CONSULTA
        # ====================================================

        sql = f"""
            SELECT

                MONTH(p.vig_desde) AS mes,

                ({moneda_bucket}) AS moneda_bucketed,

                SUM(
                    COALESCE(
                        p.prima_neta,
                        0
                    )
                ) AS total_prima_neta,

                SUM(
                    COALESCE(
                        p.imp_compania,
                        0
                    )
                ) AS total_comision,

                SUM(
                    COALESCE(
                        p.prima_comercial_igv,
                        0
                    )
                ) AS total_prima_total

            FROM polizas p

            WHERE

                p.vig_desde IS NOT NULL

                AND YEAR(p.vig_desde)
                    = YEAR(CURDATE())

                AND p.activo = 1

                AND (
                    p.anulado = 0
                    OR p.anulado IS NULL
                )

                AND COALESCE(
                    p.prima_anulada,
                    0
                ) = 0

                {user_filter}

            GROUP BY
                MONTH(p.vig_desde),
                ({moneda_bucket})

            ORDER BY
                MONTH(p.vig_desde)
        """

        cur.execute(
            sql,
            user_filter_args
        )

        rows = cur.fetchall() or []

        # ====================================================
        # MAPAS
        # ====================================================

        prima_map_soles = {}
        comision_map_soles = {}
        prima_total_map_soles = {}

        prima_map_usd = {}
        comision_map_usd = {}
        prima_total_map_usd = {}

        # ====================================================
        # PROCESAR
        # ====================================================

        for row in rows:

            mes = int(
                row[0]
            )

            moneda = (
                str(
                    row[1] or ''
                ).strip()
            )

            prima_neta = float(
                row[2] or 0
            )

            comision = float(
                row[3] or 0
            )

            prima_total = float(
                row[4] or 0
            )

            if moneda == 'S/':

                prima_map_soles[mes] = (
                    prima_map_soles.get(
                        mes,
                        0.0
                    )
                    + prima_neta
                )

                comision_map_soles[mes] = (
                    comision_map_soles.get(
                        mes,
                        0.0
                    )
                    + comision
                )

                prima_total_map_soles[mes] = (
                    prima_total_map_soles.get(
                        mes,
                        0.0
                    )
                    + prima_total
                )

            elif moneda == 'US$':

                prima_map_usd[mes] = (
                    prima_map_usd.get(
                        mes,
                        0.0
                    )
                    + prima_neta
                )

                comision_map_usd[mes] = (
                    comision_map_usd.get(
                        mes,
                        0.0
                    )
                    + comision
                )

                prima_total_map_usd[mes] = (
                    prima_total_map_usd.get(
                        mes,
                        0.0
                    )
                    + prima_total
                )

        # ====================================================
        # MESES
        # ====================================================

        meses = [
            "Ene",
            "Feb",
            "Mar",
            "Abr",
            "May",
            "Jun",
            "Jul",
            "Ago",
            "Sep",
            "Oct",
            "Nov",
            "Dic"
        ]

        current_year = datetime.now().year

        # ====================================================
        # GENERAR 12 MESES
        # ====================================================

        for month_index in range(1, 13):

            months_labels.append(
                f"{meses[month_index - 1]} {current_year}"
            )

            totals_prima_soles.append(
                prima_map_soles.get(
                    month_index,
                    0.0
                )
            )

            totals_comision_soles.append(
                comision_map_soles.get(
                    month_index,
                    0.0
                )
            )

            totals_prima_total_soles.append(
                prima_total_map_soles.get(
                    month_index,
                    0.0
                )
            )

            totals_prima_usd.append(
                prima_map_usd.get(
                    month_index,
                    0.0
                )
            )

            totals_comision_usd.append(
                comision_map_usd.get(
                    month_index,
                    0.0
                )
            )

            totals_prima_total_usd.append(
                prima_total_map_usd.get(
                    month_index,
                    0.0
                )
            )

    except Exception as e:

        print(
            "[Dashboard] "
            f"Error fetching chart data: {e}"
        )

        chart_error = str(e)

        # ====================================================
        # FALLBACK
        # ====================================================

        current_year = datetime.now().year

        meses = [
            "Ene",
            "Feb",
            "Mar",
            "Abr",
            "May",
            "Jun",
            "Jul",
            "Ago",
            "Sep",
            "Oct",
            "Nov",
            "Dic"
        ]

        months_labels = [
            f"{m} {current_year}"
            for m in meses
        ]

        totals_prima_soles = [0] * 12
        totals_comision_soles = [0] * 12
        totals_prima_total_soles = [0] * 12

        totals_prima_usd = [0] * 12
        totals_comision_usd = [0] * 12
        totals_prima_total_usd = [0] * 12

    finally:

        try:
            if cur:
                cur.close()
        except Exception:
            pass

        try:
            if cnx:
                cnx.close()
        except Exception:
            pass

    return {
        "error": chart_error,

        "months": months_labels,

        "totals_prima_soles":
            totals_prima_soles,

        "totals_comision_soles":
            totals_comision_soles,

        "totals_prima_total_soles":
            totals_prima_total_soles,

        "totals_prima_usd":
            totals_prima_usd,

        "totals_comision_usd":
            totals_comision_usd,

        "totals_prima_total_usd":
            totals_prima_total_usd,

        "title":
            "Producción vs Comisión",
    }

def _get_dashboard_user_filter(cur, alias="p"):
    """
    Devuelve:
        user_filter
        user_filter_args

    Para SUB_AGENTE permite encontrar pólizas por:
    - username
    - nombre del usuario
    - sub_agente
    - usuario_registro
    """

    user_filter = ""
    user_filter_args: List[Any] = []

    if session.get('role_name') == Roles.SUB_AGENTE:

        user = session.get('user') or ''
        nombre_usuario = user

        try:
            cur.execute(
                """
                SELECT COALESCE(
                    NULLIF(TRIM(nombre), ''),
                    username
                )
                FROM usuarios
                WHERE username = %s
                LIMIT 1
                """,
                (user,)
            )

            row = cur.fetchone()

            if row and row[0]:
                nombre_usuario = row[0]

        except Exception:
            nombre_usuario = user

        user_filter = f"""
            AND (
                LOWER(
                    TRIM(
                        REPLACE(
                            CONVERT({alias}.sub_agente USING latin1),
                            _latin1 0xA0,
                            ' '
                        )
                    )
                ) = LOWER(TRIM(%s))

                OR

                LOWER(
                    TRIM(
                        REPLACE(
                            CONVERT({alias}.sub_agente USING latin1),
                            _latin1 0xA0,
                            ' '
                        )
                    )
                ) = LOWER(TRIM(%s))

                OR

                LOWER(
                    TRIM(
                        REPLACE(
                            CONVERT({alias}.usuario_registro USING latin1),
                            _latin1 0xA0,
                            ' '
                        )
                    )
                ) = LOWER(TRIM(%s))

                OR

                LOWER(
                    TRIM(
                        REPLACE(
                            CONVERT({alias}.usuario_registro USING latin1),
                            _latin1 0xA0,
                            ' '
                        )
                    )
                ) = LOWER(TRIM(%s))
            )
        """

        user_filter_args = [
            user,
            nombre_usuario,
            user,
            nombre_usuario
        ]

    return user_filter, user_filter_args


# ============================================================
# CLASIFICACIÓN ÚNICA DE RAMOS
# ============================================================

def _dashboard_bucket_sql(alias="p", ramo_alias="r"):
    """
    IMPORTANTE:

    Esta clasificación se utiliza EXACTAMENTE igual para:

    - tarjeta Renovaciones
    - SOAT
    - Seguros Generales
    - Seguros Personales
    - lista de renovaciones

    Así evitamos que el contador diga una cantidad y
    al entrar al detalle no aparezca nada.
    """

    return f"""
        CASE

            /* =================================================
               SOAT
               ================================================= */
            WHEN UPPER(
                TRIM(
                    COALESCE({alias}.ramo, '')
                )
            ) = 'SOAT'
            THEN 'soat'


            /* =================================================
               PERSONALES / RRHH

               Primero usamos ramos.grupo.
               Si no existe el JOIN, usamos el nombre del ramo.
               ================================================= */
            WHEN UPPER(
                TRIM(
                    COALESCE({ramo_alias}.grupo, '')
                )
            ) LIKE '%RRHH%'
            THEN 'personales'

            WHEN UPPER(
                TRIM(
                    COALESCE({alias}.ramo, '')
                )
            ) IN (
                'ACCIDENTES PERSONALES',
                'ASISTENCIA MEDICA FAMILIAR',
                'EPS',
                'SCTR',
                'VIDA - LEY',
                'VIDA LEY',
                'VIDA',
                'VIAJE',
                'FORMACION LABORAL',
                'FOLA',
                'ONCOLOGICO',
                'SALUD'
            )
            THEN 'personales'


            /* =================================================
               TODO LO DEMÁS = GENERALES
               ================================================= */
            ELSE 'generales'

        END
    """


# ============================================================
# RENOVACIÓN: CRITERIO ÚNICO
# ============================================================

def _dashboard_renewal_sql(alias="p"):
    """
    Devuelve la condición para considerar una póliza
    como 'por renovar'.

    REGLA:

    ANUAL:
        vence hoy o dentro de 1 día.

    OTROS TIPOS:
        vence hoy o dentro de 10 días.

    NO RENOVABLE / EVENTUAL / FLOTANTE:
        nunca entran.

    Además:
        - activa
        - no anulada
        - prima no anulada
        - vig_hasta >= hoy
    """

    return f"""
        {alias}.activo = 1

        AND (
            {alias}.anulado = 0
            OR {alias}.anulado IS NULL
        )

        AND COALESCE(
            {alias}.prima_anulada,
            0
        ) = 0

        AND {alias}.vig_hasta IS NOT NULL

        AND {alias}.vig_hasta >= CURDATE()

        AND UPPER(
            TRIM(
                COALESCE(
                    {alias}.tipo_vigencia,
                    ''
                )
            )
        ) NOT IN (
            'NO RENOVABLE',
            'EVENTUAL',
            'FLOTANTE'
        )

        AND (
            (
                UPPER(
                    TRIM(
                        COALESCE(
                            {alias}.tipo_vigencia,
                            ''
                        )
                    )
                ) = 'ANUAL'

                AND {alias}.vig_hasta <= DATE_ADD(
                    CURDATE(),
                    INTERVAL 1 DAY
                )
            )

            OR

            (
                UPPER(
                    TRIM(
                        COALESCE(
                            {alias}.tipo_vigencia,
                            ''
                        )
                    )
                ) <> 'ANUAL'

                AND {alias}.vig_hasta <= DATE_ADD(
                    CURDATE(),
                    INTERVAL 10 DAY
                )
            )
        )
    """


# ============================================================
# GET DASHBOARD CARDS
# ============================================================

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

        'prima_neta_soles': '0.00',
        'prima_neta_dolares': '0.00',

        'comision_soles': '0.00',
        'comision_dolares': '0.00',

        'total_commission': '$0.00',
        'comision_diff': 0
    }

    cnx = None
    cur = None

    try:

        cnx = get_connection()
        cur = cnx.cursor()

        # ====================================================
        # FILTRO DEL USUARIO
        # ====================================================

        user_filter, user_filter_args = _get_dashboard_user_filter(
            cur,
            "p"
        )

        # ====================================================
        # CLIENTES
        # ====================================================

        client_where = "WHERE 1 = 1"
        client_where_args: List[Any] = []

        if session.get('role_name') == Roles.SUB_AGENTE:

            user = session.get('user') or ''
            nombre_usuario = user

            try:
                cur.execute(
                    """
                    SELECT COALESCE(
                        NULLIF(TRIM(nombre), ''),
                        username
                    )
                    FROM usuarios
                    WHERE username = %s
                    LIMIT 1
                    """,
                    (user,)
                )

                row = cur.fetchone()

                if row and row[0]:
                    nombre_usuario = row[0]

            except Exception:
                nombre_usuario = user

            client_where += """
                AND (
                    LOWER(TRIM(subagente)) = LOWER(TRIM(%s))
                    OR
                    LOWER(TRIM(subagente)) = LOWER(TRIM(%s))
                )
            """

            client_where_args = [
                user,
                nombre_usuario
            ]

        # ====================================================
        # TOTAL CLIENTES
        # ====================================================

        try:

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM clientes
                {client_where}
                """,
                client_where_args
            )

            row = cur.fetchone()

            if row:
                cards['total_clients'] = int(row[0] or 0)

        except Exception as e:
            print(
                f"[Dashboard] Error total_clients: {e}"
            )

        # ====================================================
        # CLIENTES ACTIVOS
        # ====================================================

        try:

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM clientes
                {client_where}
                AND activo = 1
                """,
                client_where_args
            )

            row = cur.fetchone()

            if row:
                cards['active_clients'] = int(row[0] or 0)

        except Exception as e:
            print(
                f"[Dashboard] Error active_clients: {e}"
            )

        # ====================================================
        # ÚLTIMO ID CLIENTE
        # ====================================================

        try:

            cur.execute(
                """
                SELECT MAX(idCliente)
                FROM clientes
                """
            )

            row = cur.fetchone()

            if row and row[0] is not None:
                cards['last_client_id'] = int(row[0])

        except Exception as e:
            print(
                f"[Dashboard] Error last_client_id: {e}"
            )

        # ====================================================
        # PÓLIZAS ACTIVAS
        # ====================================================

        try:

            sql = f"""
                SELECT COUNT(*)
                FROM polizas p
                WHERE
                    p.activo = 1

                    AND (
                        p.anulado = 0
                        OR p.anulado IS NULL
                    )

                    AND COALESCE(
                        p.prima_anulada,
                        0
                    ) = 0

                    AND p.vig_hasta >= CURDATE()

                    {user_filter}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            if row:
                cards['active_policies'] = int(row[0] or 0)

        except Exception as e:
            print(
                f"[Dashboard] Error active_policies: {e}"
            )

        # ====================================================
        # TOTAL PÓLIZAS
        # ====================================================

        try:

            sql = f"""
                SELECT COUNT(*)
                FROM polizas p
                WHERE
                    p.activo = 1

                    AND (
                        p.anulado = 0
                        OR p.anulado IS NULL
                    )

                    AND COALESCE(
                        p.prima_anulada,
                        0
                    ) = 0

                    {user_filter}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            if row:
                cards['total_policies'] = int(row[0] or 0)

        except Exception as e:
            print(
                f"[Dashboard] Error total_policies: {e}"
            )

        # ====================================================
        # RENOVACIONES
        #
        # IMPORTANTE:
        # AHORA USA EXACTAMENTE EL MISMO CRITERIO QUE
        # get_distribution_by_group()
        #
        # Por eso:
        #
        # Renovaciones = SOAT + Generales + Personales
        #
        # ====================================================

        try:

            renewal_sql = _dashboard_renewal_sql("p")

            sql = f"""
                SELECT COUNT(*)
                FROM polizas p
                LEFT JOIN ramos r
                    ON LOWER(TRIM(p.ramo))
                    =
                    LOWER(TRIM(r.nombre))

                WHERE
                    {renewal_sql}

                    {user_filter}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            if row:
                cards['pending_renewals'] = int(
                    row[0] or 0
                )

        except Exception as e:

            print(
                f"[Dashboard] Error pending_renewals: {e}"
            )

        # ====================================================
        # PRODUCCIÓN Y COMISIÓN
        # ====================================================

        try:

            # -------------------------------
            # PRODUCCIÓN MES ACTUAL
            # -------------------------------

            sql = f"""
                SELECT
                    SUM(
                        COALESCE(
                            p.prima_neta,
                            0
                        )
                    )
                FROM polizas p
                WHERE
                    p.vig_desde IS NOT NULL

                    AND MONTH(p.vig_desde)
                        = MONTH(CURDATE())

                    AND YEAR(p.vig_desde)
                        = YEAR(CURDATE())

                    AND p.activo = 1

                    AND (
                        p.anulado = 0
                        OR p.anulado IS NULL
                    )

                    AND COALESCE(
                        p.prima_anulada,
                        0
                    ) = 0

                    {user_filter}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            curr_prod = float(
                row[0] or 0
            ) if row else 0.0

            # -------------------------------
            # PRODUCCIÓN MES ANTERIOR
            # -------------------------------

            sql = f"""
                SELECT
                    SUM(
                        COALESCE(
                            p.prima_neta,
                            0
                        )
                    )
                FROM polizas p
                WHERE
                    p.vig_desde IS NOT NULL

                    AND MONTH(p.vig_desde)
                        = MONTH(
                            DATE_SUB(
                                CURDATE(),
                                INTERVAL 1 MONTH
                            )
                        )

                    AND YEAR(p.vig_desde)
                        = YEAR(
                            DATE_SUB(
                                CURDATE(),
                                INTERVAL 1 MONTH
                            )
                        )

                    AND p.activo = 1

                    AND (
                        p.anulado = 0
                        OR p.anulado IS NULL
                    )

                    AND COALESCE(
                        p.prima_anulada,
                        0
                    ) = 0

                    {user_filter}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            prev_prod = float(
                row[0] or 0
            ) if row else 0.0

            cards['total_production'] = (
                f"${curr_prod:,.2f}"
            )

            if prev_prod > 0:

                cards['prod_diff'] = round(
                    (
                        (curr_prod - prev_prod)
                        / prev_prod
                    ) * 100,
                    1
                )

            else:

                cards['prod_diff'] = (
                    100
                    if curr_prod > 0
                    else 0
                )

            # -------------------------------
            # COMISIÓN MES ACTUAL
            # -------------------------------

            sql = f"""
                SELECT
                    SUM(
                        COALESCE(
                            p.imp_compania,
                            0
                        )
                    )
                FROM polizas p
                WHERE
                    p.vig_desde IS NOT NULL

                    AND MONTH(p.vig_desde)
                        = MONTH(CURDATE())

                    AND YEAR(p.vig_desde)
                        = YEAR(CURDATE())

                    AND p.activo = 1

                    AND (
                        p.anulado = 0
                        OR p.anulado IS NULL
                    )

                    AND COALESCE(
                        p.prima_anulada,
                        0
                    ) = 0

                    {user_filter}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            curr_com = float(
                row[0] or 0
            ) if row else 0.0

            # -------------------------------
            # COMISIÓN MES ANTERIOR
            # -------------------------------

            sql = f"""
                SELECT
                    SUM(
                        COALESCE(
                            p.imp_compania,
                            0
                        )
                    )
                FROM polizas p
                WHERE
                    p.vig_desde IS NOT NULL

                    AND MONTH(p.vig_desde)
                        = MONTH(
                            DATE_SUB(
                                CURDATE(),
                                INTERVAL 1 MONTH
                            )
                        )

                    AND YEAR(p.vig_desde)
                        = YEAR(
                            DATE_SUB(
                                CURDATE(),
                                INTERVAL 1 MONTH
                            )
                        )

                    AND p.activo = 1

                    AND (
                        p.anulado = 0
                        OR p.anulado IS NULL
                    )

                    AND COALESCE(
                        p.prima_anulada,
                        0
                    ) = 0

                    {user_filter}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            prev_com = float(
                row[0] or 0
            ) if row else 0.0

            cards['total_commission'] = (
                f"${curr_com:,.2f}"
            )

            if prev_com > 0:

                cards['comision_diff'] = round(
                    (
                        (curr_com - prev_com)
                        / prev_com
                    ) * 100,
                    1
                )

            else:

                cards['comision_diff'] = (
                    100
                    if curr_com > 0
                    else 0
                )

        except Exception as e:

            print(
                f"[Dashboard] Error production/commission: {e}"
            )

        # ====================================================
        # MONEDA
        # ====================================================

        try:

            moneda_norm = """
                UPPER(
                    REPLACE(
                        REPLACE(
                            TRIM(
                                REPLACE(
                                    CONVERT(
                                        p.moneda USING latin1
                                    ),
                                    _latin1 0xA0,
                                    ' '
                                )
                            ),
                            ' ',
                            ''
                        ),
                        '.',
                        ''
                    )
                )
            """

            moneda_bucket = f"""
                CASE

                    WHEN
                        {moneda_norm} IN (
                            'US$',
                            'USD',
                            '$',
                            'DOLARES'
                        )
                        OR {moneda_norm} LIKE 'DOL%'
                    THEN 'US$'

                    WHEN
                        {moneda_norm} IN (
                            'S/',
                            'SOLES',
                            'PEN'
                        )
                        OR {moneda_norm} LIKE 'S/%'
                        OR {moneda_norm} LIKE 'SOL%'
                    THEN 'S/'

                    ELSE {moneda_norm}

                END
            """

            base_where = f"""
                FROM polizas p
                WHERE
                    p.vig_desde IS NOT NULL

                    AND MONTH(p.vig_desde)
                        = MONTH(CURDATE())

                    AND YEAR(p.vig_desde)
                        = YEAR(CURDATE())

                    AND p.activo = 1

                    AND (
                        p.anulado = 0
                        OR p.anulado IS NULL
                    )

                    AND COALESCE(
                        p.prima_anulada,
                        0
                    ) = 0

                    {{currency_filter}}

                    {user_filter}
            """

            # -------------------------------
            # PRIMA SOLES
            # -------------------------------

            sql = f"""
                SELECT SUM(
                    COALESCE(p.prima_neta, 0)
                )
                {base_where.format(
                    currency_filter=f"""
                        AND ({moneda_bucket}) = 'S/'
                    """
                )}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            cards['prima_neta_soles'] = (
                f"{float(row[0] or 0):,.2f}"
                if row else "0.00"
            )

            # -------------------------------
            # PRIMA DÓLARES
            # -------------------------------

            sql = f"""
                SELECT SUM(
                    COALESCE(p.prima_neta, 0)
                )
                {base_where.format(
                    currency_filter=f"""
                        AND ({moneda_bucket}) = 'US$'
                    """
                )}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            cards['prima_neta_dolares'] = (
                f"{float(row[0] or 0):,.2f}"
                if row else "0.00"
            )

            # -------------------------------
            # COMISIÓN SOLES
            # -------------------------------

            sql = f"""
                SELECT SUM(
                    COALESCE(p.imp_compania, 0)
                )
                {base_where.format(
                    currency_filter=f"""
                        AND ({moneda_bucket}) = 'S/'
                    """
                )}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            cards['comision_soles'] = (
                f"{float(row[0] or 0):,.2f}"
                if row else "0.00"
            )

            # -------------------------------
            # COMISIÓN DÓLARES
            # -------------------------------

            sql = f"""
                SELECT SUM(
                    COALESCE(p.imp_compania, 0)
                )
                {base_where.format(
                    currency_filter=f"""
                        AND ({moneda_bucket}) = 'US$'
                    """
                )}
            """

            cur.execute(
                sql,
                user_filter_args
            )

            row = cur.fetchone()

            cards['comision_dolares'] = (
                f"{float(row[0] or 0):,.2f}"
                if row else "0.00"
            )

        except Exception as e:

            print(
                f"[Dashboard] Error currency metrics: {e}"
            )

    except Exception as e:

        print(
            f"[Dashboard] Error fetching cards data: {e}"
        )

    finally:

        try:
            if cur:
                cur.close()
        except Exception:
            pass

        try:
            if cnx:
                cnx.close()
        except Exception:
            pass

    return cards


# ============================================================
# DISTRIBUCIÓN POR GRUPO
# ============================================================

def get_distribution_by_group() -> Dict[str, Any]:

    result = {
        'generales': {
            'vigentes': 0,
            'renovar': 0
        },

        'soat': {
            'vigentes': 0,
            'renovar': 0
        },

        'personales': {
            'vigentes': 0,
            'renovar': 0
        }
    }

    cnx = None
    cur = None

    try:

        cnx = get_connection()
        cur = cnx.cursor()

        user_filter, user_filter_args = (
            _get_dashboard_user_filter(
                cur,
                "p"
            )
        )

        bucket_sql = _dashboard_bucket_sql(
            "p",
            "r"
        )

        # ====================================================
        # CRITERIO DE RENOVACIÓN
        # ====================================================

        renewal_sql = _dashboard_renewal_sql("p")

        sql = f"""
            SELECT

                {bucket_sql} AS bucket,

                COUNT(*) AS renovar

            FROM polizas p

            LEFT JOIN ramos r
                ON LOWER(TRIM(p.ramo))
                =
                LOWER(TRIM(r.nombre))

            WHERE

                {renewal_sql}

                {user_filter}

            GROUP BY
                {bucket_sql}

            ORDER BY
                bucket
        """

        cur.execute(
            sql,
            user_filter_args
        )

        rows = cur.fetchall() or []

        for row in rows:

            bucket = (
                str(row[0] or '')
                .strip()
                .lower()
            )

            renovar = int(
                row[1] or 0
            )

            if bucket in result:

                result[bucket]['renovar'] = renovar

        # ====================================================
        # VIGENTES QUE NO ESTÁN EN RENOVACIÓN
        # ====================================================

        sql = f"""
            SELECT

                {bucket_sql} AS bucket,

                COUNT(*) AS vigentes

            FROM polizas p

            LEFT JOIN ramos r
                ON LOWER(TRIM(p.ramo))
                =
                LOWER(TRIM(r.nombre))

            WHERE

                p.activo = 1

                AND (
                    p.anulado = 0
                    OR p.anulado IS NULL
                )

                AND COALESCE(
                    p.prima_anulada,
                    0
                ) = 0

                AND p.vig_hasta IS NOT NULL

                AND p.vig_hasta >= CURDATE()

                AND NOT (
                    {renewal_sql}
                )

                {user_filter}

            GROUP BY
                {bucket_sql}

            ORDER BY
                bucket
        """

        cur.execute(
            sql,
            user_filter_args
        )

        rows = cur.fetchall() or []

        for row in rows:

            bucket = (
                str(row[0] or '')
                .strip()
                .lower()
            )

            vigentes = int(
                row[1] or 0
            )

            if bucket in result:

                result[bucket]['vigentes'] = vigentes

    except Exception as e:

        print(
            f"[Dashboard] Error distribution: {e}"
        )

    finally:

        try:
            if cur:
                cur.close()
        except Exception:
            pass

        try:
            if cnx:
                cnx.close()
        except Exception:
            pass

    return result


# ============================================================
# LISTA DE RENOVACIONES
# ============================================================

def get_pending_renewals_list(
    bucket: str,
    limit: int = 500
) -> List[dict]:

    if bucket not in (
        'generales',
        'soat',
        'personales'
    ):
        return []

    safe_limit = max(
        1,
        min(
            int(limit or 500),
            2000
        )
    )

    rows_out: List[dict] = []

    cnx = None
    cur = None

    try:

        cnx = get_connection()

        cur = cnx.cursor(
            dictionary=True
        )

        user_filter, user_filter_args = (
            _get_dashboard_user_filter(
                cur,
                "p"
            )
        )

        # ====================================================
        # MISMA CLASIFICACIÓN QUE EL CONTADOR
        # ====================================================

        bucket_sql = _dashboard_bucket_sql(
            "p",
            "r"
        )

        # ====================================================
        # MISMO CRITERIO DE RENOVACIÓN
        # ====================================================

        renewal_sql = _dashboard_renewal_sql(
            "p"
        )

        sql = f"""
            SELECT

                p.idPoliza,

                COALESCE(
                    CAST(
                        AES_DECRYPT(
                            FROM_BASE64(p.poliza),
                            @SIS_KEY
                        ) AS CHAR
                    ),
                    CAST(
                        AES_DECRYPT(
                            p.poliza,
                            @SIS_KEY
                        ) AS CHAR
                    ),
                    p.poliza
                ) AS poliza,

                COALESCE(
                    CAST(
                        AES_DECRYPT(
                            FROM_BASE64(p.recibo),
                            @SIS_KEY
                        ) AS CHAR
                    ),
                    CAST(
                        AES_DECRYPT(
                            p.recibo,
                            @SIS_KEY
                        ) AS CHAR
                    ),
                    p.recibo
                ) AS recibo,

                p.ramo,

                r.grupo,

                p.tipo_vigencia,

                p.vig_desde,

                p.vig_hasta,

                {bucket_sql} AS bucket,

                EXISTS (
                    SELECT 1
                    FROM cuotas c
                    WHERE
                        c.poliza_id = p.idPoliza

                        AND COALESCE(
                            c.activo,
                            1
                        ) = 1

                        AND TRIM(
                            COALESCE(
                                c.factura,
                                ''
                            )
                        ) = ''
                ) AS missing_invoice

            FROM polizas p

            LEFT JOIN ramos r
                ON LOWER(TRIM(p.ramo))
                =
                LOWER(TRIM(r.nombre))

            WHERE

                {renewal_sql}

                AND ({bucket_sql}) = %s

                {user_filter}

            ORDER BY
                p.vig_hasta ASC,
                p.idPoliza ASC

            LIMIT %s
        """

        params = (
            [bucket]
            +
            user_filter_args
            +
            [safe_limit]
        )

        cur.execute(
            sql,
            params
        )

        rows = cur.fetchall() or []

        # ====================================================
        # FORMATEAR RESULTADOS
        # ====================================================

        for r in rows:

            vig_desde = r.get(
                'vig_desde'
            )

            vig_hasta = r.get(
                'vig_hasta'
            )

            poliza = (
                str(
                    r.get('poliza')
                    or ''
                ).strip()
            )

            if not poliza:

                poliza = (
                    f"ID {r.get('idPoliza')}"
                )

            recibo = (
                str(
                    r.get('recibo')
                    or ''
                ).strip()
            )

            if isinstance(
                vig_desde,
                (datetime, date)
            ):

                vig_desde_txt = (
                    vig_desde.strftime(
                        '%d/%m/%Y'
                    )
                )

            else:

                vig_desde_txt = (
                    str(vig_desde)
                    if vig_desde
                    else ''
                )

            if isinstance(
                vig_hasta,
                (datetime, date)
            ):

                vig_hasta_txt = (
                    vig_hasta.strftime(
                        '%d/%m/%Y'
                    )
                )

            else:

                vig_hasta_txt = (
                    str(vig_hasta)
                    if vig_hasta
                    else ''
                )

            rows_out.append({

                'idPoliza':
                    r.get('idPoliza'),

                'poliza':
                    poliza,

                'recibo':
                    recibo,

                'ramo':
                    (
                        str(
                            r.get('ramo')
                            or ''
                        ).strip()
                    ),

                'grupo':
                    (
                        str(
                            r.get('grupo')
                            or ''
                        ).strip()
                    ),

                'tipo_vigencia':
                    (
                        str(
                            r.get(
                                'tipo_vigencia'
                            )
                            or ''
                        ).strip()
                    ),

                'vig_desde':
                    vig_desde_txt,

                'vig_hasta':
                    vig_hasta_txt,

                'missing_invoice':
                    bool(
                        r.get(
                            'missing_invoice'
                        )
                    )
            })

    except Exception as e:

        print(
            "[Dashboard] "
            f"Error pending renewals list: {e}"
        )

    finally:

        try:
            if cur:
                cur.close()
        except Exception:
            pass

        try:
            if cnx:
                cnx.close()
        except Exception:
            pass

    return rows_out