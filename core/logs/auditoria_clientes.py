from core.logs.audit import log_client_action
from core import session

def auditar_criacao(cliente_id: int):
    user = (session.get_current_user() or "")
    log_client_action(user, cliente_id, "criou")

def auditar_edicao(cliente_id: int):
    user = (session.get_current_user() or "")
    log_client_action(user, cliente_id, "editou")
