# módulo: controllers/cliente.py
def get_clientes_data():
    rows = [
        {
            "id": 1,
            "razon_social": "FLORES AMASIFUEN JUAN ENRIQUE",
            "doc": "DNI/CE",
            "n_doc": "76389670",
            "tel": "958607386",
            "subagente": "AAS",
            "email": "enriquefloresamasifuen@gmail.com",
            "direccion": "JR. LIDIA PINEDO CC.NN SAN FRANCISCO MZ. II LT. 03",
            "estado": "Activo"
        },
        {
            "id": 2,
            "razon_social": "NEGOCIOS Y SERVICIOS JEFF EIRL",
            "doc": "RUC",
            "n_doc": "7060013861",
            "tel": "985044531",
            "subagente": "ARAS Y ARAS",
            "email": "coordinaciones@ariasayarias.com",
            "direccion": "Pasaje LA LUPUNA MZA. H LOTE. 19 A.H. LA LUPUNA",
            "estado": "Activo"
        },
        {
            "id": 3,
            "razon_social": "CHANG CORPORATION SAC",
            "doc": "RUC",
            "n_doc": "20613815484",
            "tel": "945 175 078",
            "subagente": "ARAS Y ARAS",
            "email": "segurospersonales@ariasayarias.com",
            "direccion": "JR. RUPERTO PEREZ MAYNAS MZA. 2 LOTE. 1B (MEDIA CUADRA DEL BULEVAR DE VARINACOCHA)",
            "estado": "Activo"
        },
    ]
    filters = {
        "orders": ["F. Reg.", "Razón Social", "Doc", "N.Doc", "Tel", "Email", "Subagente", "Dirección", "Estado"]
    }
    return {"rows": rows, "filters": filters, "title": "Clientes"}