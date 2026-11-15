from apps.audit.domain.log_register import LogRegister
from apps.privacy.models import AceiteTermo, Termo

TIPOS_ACEITOS_NO_LOGIN = (Termo.TIPO_POLITICA, Termo.TIPO_TERMO)

SITUACAO_ACEITO = "aceito"
SITUACAO_PENDENTE = "pendente"
SITUACAO_REVOGADO = "revogado"


def _aceites_validos():
    return AceiteTermo.objects.filter(concedido=True, data_revogada__isnull=True)


def termos_pendentes(usuario) -> list[Termo]:
    aceitos = _aceites_validos().filter(usuario=usuario).values("termo_id")
    return list(
        Termo.objects.filter(ativo=True, tipo__in=TIPOS_ACEITOS_NO_LOGIN)
        .exclude(id__in=aceitos)
        .order_by("tipo")
    )


def registrar_aceite(usuario, termos, evidencia: dict) -> None:
    for termo in termos:
        AceiteTermo.objects.create(usuario=usuario, termo=termo, concedido=True, evidencia=evidencia)
    LogRegister().register(
        {
            "autor_id": usuario.id,
            "origem": "privacy",
            "acao": "TERMOS_ACEITOS",
            "tabela": "aceite_termo",
            "linha_tabela_id": usuario.id,
            "payload": {"termos": [f"{termo.tipo} v{termo.versao}" for termo in termos]},
        }
    )


def situacao_dos_termos(usuarios_ids) -> dict:
    termos_vigentes = set(
        Termo.objects.filter(ativo=True, tipo__in=TIPOS_ACEITOS_NO_LOGIN).values_list("id", flat=True)
    )
    aceitos_por_usuario = {}
    for usuario_id, termo_id in _aceites_validos().filter(
        usuario_id__in=usuarios_ids, termo_id__in=termos_vigentes
    ).values_list("usuario_id", "termo_id"):
        aceitos_por_usuario.setdefault(usuario_id, set()).add(termo_id)
    return {
        usuario_id: SITUACAO_ACEITO
        if termos_vigentes and aceitos_por_usuario.get(usuario_id, set()) >= termos_vigentes
        else SITUACAO_PENDENTE
        for usuario_id in usuarios_ids
    }


def situacao_da_biometria(usuarios_ids) -> dict:
    situacao = {usuario_id: SITUACAO_PENDENTE for usuario_id in usuarios_ids}
    consentimentos = AceiteTermo.objects.filter(
        usuario_id__in=usuarios_ids, termo__tipo=Termo.TIPO_BIOMETRICO, concedido=True
    ).order_by("data_concedido")
    for usuario_id, data_revogada, termo_vigente in consentimentos.values_list(
        "usuario_id", "data_revogada", "termo__ativo"
    ):
        if data_revogada:
            situacao[usuario_id] = SITUACAO_REVOGADO
        elif termo_vigente:
            situacao[usuario_id] = SITUACAO_ACEITO
        else:
            situacao[usuario_id] = SITUACAO_PENDENTE
    return situacao
