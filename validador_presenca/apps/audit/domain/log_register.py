from apps.audit.models import AuditLog

def LogRegister(data_log: dict):

    AuditLog.objects.create(
        autor_id = data_log.get("autor_id", ""),
        origem = data_log.get("origem", ""),
        acao = data_log.get("acao", ""),
        tabela = data_log.get("tabela", ""),
        linha_tabela_id = data_log.get("linha_tabela_id", ""),
    )