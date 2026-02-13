
class Roles:
    BROKER = 'BROKER'
    EJECUTIVO = 'EJECUTIVO DE CUENTAS'
    OPERADOR = 'OPERADOR'
    SUB_AGENTE = 'SUB AGENTE'

def can_access_maestros(role_name):
    return role_name == Roles.BROKER

def can_delete(role_name):
    # BROKER: Yes
    # EJECUTIVO: Yes ("solo mira y ELIMINA")
    # OPERADOR: No
    # SUB AGENTE: No
    return role_name in [Roles.BROKER, Roles.EJECUTIVO]

def can_edit(role_name):
    # BROKER: Yes
    # EJECUTIVO: No ("solo mira y ELIMINA" implies no edit?) - User said "solo mira". Usually means Read Only.
    # But OPERADOR "adiciona, actualiza".
    # So EJECUTIVO cannot edit.
    # OPERADOR: Yes
    # SUB AGENTE: Yes ("adiciona") - presumably updates too? "Acceso a solo sus cuentas... adiciona, NO ELIMINA". 
    # Usually "adiciona" implies creation. Updates? Let's assume yes for own accounts.
    return role_name in [Roles.BROKER, Roles.OPERADOR, Roles.SUB_AGENTE]

def can_create(role_name):
    return role_name in [Roles.BROKER, Roles.OPERADOR, Roles.SUB_AGENTE]

def get_role_scope(role_name):
    if role_name == Roles.SUB_AGENTE:
        return 'OWN'
    return 'ALL'
