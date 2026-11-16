from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.models import Usuario
from apps.audit.domain.event_visibility import ROTULOS_DE_ACAO, eventos_visiveis, rotulo_da_acao
from validador_presenca.pagination import paginar


def _data(valor):
    try:
        return date.fromisoformat(valor) if valor else None
    except ValueError:
        return None


@login_required
def registro_de_atividades(request):
    eventos = eventos_visiveis(request.user).order_by("-ocorrido_em", "-id")

    acao = request.GET.get("acao", "")
    data_inicio = _data(request.GET.get("de"))
    data_fim = _data(request.GET.get("ate"))
    if acao:
        eventos = eventos.filter(acao=acao)
    if data_inicio:
        eventos = eventos.filter(ocorrido_em__date__gte=data_inicio)
    if data_fim:
        eventos = eventos.filter(ocorrido_em__date__lte=data_fim)

    pagina = paginar(request, eventos, por_pagina=30)
    autores = {
        usuario.id: usuario.get_full_name() or usuario.email
        for usuario in Usuario.objects.filter(id__in={evento.autor_id for evento in pagina})
    }
    for evento in pagina:
        evento.rotulo = rotulo_da_acao(evento.acao)
        evento.autor_nome = autores.get(evento.autor_id, "Sistema")

    contexto = {
        "eventos": pagina,
        "acoes": sorted(ROTULOS_DE_ACAO.items(), key=lambda item: item[1]),
        "acao_selecionada": acao,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "escopo": _escopo(request.user),
    }
    return render(request, "audit/registro_de_atividades.html", contexto)


def _escopo(usuario) -> str:
    if hasattr(usuario, "administrador"):
        return "Todos os eventos do sistema."
    if hasattr(usuario, "professor"):
        return "As suas ações e os eventos das chamadas e presenças das suas turmas."
    return "As suas ações e os eventos das suas presenças e solicitações."
