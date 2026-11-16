import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.decorators import only_admin
from apps.audit.domain.log_register import registrar_acao
from apps.privacy.domain.lgpd_service import (
    PRAZO_DIAS,
    AutoAtendimentoError,
    SolicitacaoEncerradaError,
    SolicitacaoNaoAutomatizavelError,
    atender_solicitacao,
    colocar_em_analise,
    dias_em_aberto,
    exportar_dados,
    recusar_solicitacao,
)
from apps.privacy.forms import SolicitacaoLGPDForm
from apps.privacy.models import SolicitacaoLGPD, Termo
from validador_presenca.pagination import paginar

STATUS_ABERTOS = (SolicitacaoLGPD.STATUS_PENDENTE, SolicitacaoLGPD.STATUS_EM_ANALISE)

# Create your views here.

@login_required
def central_privacidade(request):
    return render(request, "privacy/central.html")


def politica_privacidade(request):
    termo = get_object_or_404(Termo, tipo=Termo.TIPO_POLITICA, ativo=True)
    return render(request, "privacy/termo.html", {"termo": termo})


def termo_uso(request):
    termo = get_object_or_404(Termo, tipo=Termo.TIPO_TERMO, ativo=True)
    return render(request, "privacy/termo.html", {"termo": termo})


def termo_biometrico(request):
    termo = get_object_or_404(Termo, tipo=Termo.TIPO_BIOMETRICO, ativo=True)
    return render(request, "privacy/termo.html", {"termo": termo})


@login_required
def solicitar_direito(request):
    if request.method == "POST":
        form = SolicitacaoLGPDForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.usuario = request.user
            solicitacao.save()
            registrar_acao(request.user, "privacy", "SOLICITACAO_LGPD_CRIADA", "solicitacao_lgpd", solicitacao.id,
                           {"tipo": solicitacao.tipo})
            messages.success(
                request,
                f"Solicitação #{solicitacao.pk} registrada. Retorno em até 15 dias.",
            )
            return redirect("privacy:minhas_solicitacoes")
    else:
        form = SolicitacaoLGPDForm()

    prazo = timezone.now() + timedelta(days=15)
    return render(request, "privacy/solicitar.html", {"form": form, "prazo": prazo})


@login_required
def minhas_solicitacoes(request):
    solicitacoes = SolicitacaoLGPD.objects.filter(usuario=request.user)
    return render(request, "privacy/minhas_solicitacoes.html", {
        "solicitacoes": solicitacoes,
        "pode_baixar": _exportacao_liberada(request.user),
    })


def _exportacao_liberada(usuario) -> bool:
    return SolicitacaoLGPD.objects.filter(
        usuario=usuario,
        tipo=SolicitacaoLGPD.TIPO_EXPORTAR_DADOS,
        status=SolicitacaoLGPD.STATUS_ATENDIDA,
    ).exists()


@login_required
def baixar_meus_dados(request):
    if not _exportacao_liberada(request.user):
        raise Http404
    conteudo = json.dumps(exportar_dados(request.user), cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)
    registrar_acao(request.user, "privacy", "DADOS_BAIXADOS", "usuario", request.user.id, {})
    resposta = HttpResponse(conteudo, content_type="application/json; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="meus_dados_adsum.json"'
    return resposta


@login_required
@only_admin
def solicitacoes_admin(request):
    status = request.GET.get("status", "abertas")
    tipo = request.GET.get("tipo", "")
    todas = SolicitacaoLGPD.objects.select_related("usuario")
    solicitacoes = todas
    if status == "abertas":
        solicitacoes = solicitacoes.filter(status__in=STATUS_ABERTOS)
    elif status in dict(SolicitacaoLGPD.STATUS_CHOICES):
        solicitacoes = solicitacoes.filter(status=status)
    if tipo in dict(SolicitacaoLGPD.TIPO_CHOICES):
        solicitacoes = solicitacoes.filter(tipo=tipo)
    solicitacoes = solicitacoes.order_by("data_solicitacao") if status == "abertas" else solicitacoes

    pagina = paginar(request, solicitacoes)
    agora = timezone.now()
    for solicitacao in pagina:
        solicitacao.dias = dias_em_aberto(solicitacao, agora)
        solicitacao.atrasada = solicitacao.status in STATUS_ABERTOS and solicitacao.dias >= PRAZO_DIAS
        solicitacao.propria = solicitacao.usuario_id == request.user.id

    limite = agora - timedelta(days=PRAZO_DIAS)
    totais = todas.aggregate(
        abertas=Count("id", filter=Q(status__in=STATUS_ABERTOS)),
        atrasadas=Count("id", filter=Q(status__in=STATUS_ABERTOS, data_solicitacao__lte=limite)),
        atendidas=Count("id", filter=Q(status=SolicitacaoLGPD.STATUS_ATENDIDA)),
        recusadas=Count("id", filter=Q(status=SolicitacaoLGPD.STATUS_RECUSADA)),
    )
    return render(request, "privacy/solicitacoes_admin.html", {
        "solicitacoes": pagina,
        "totais": totais,
        "status_selecionado": status,
        "tipo_selecionado": tipo,
        "status_opcoes": SolicitacaoLGPD.STATUS_CHOICES,
        "tipo_opcoes": SolicitacaoLGPD.TIPO_CHOICES,
        "prazo_dias": PRAZO_DIAS,
        "tipo_correcao": SolicitacaoLGPD.TIPO_CORRIGIR_DADOS,
        "tipo_exclusao": SolicitacaoLGPD.TIPO_EXCLUIR_CONTA,
    })


@login_required
@only_admin
@require_POST
def decidir_solicitacao(request, solicitacao_id: int):
    solicitacao = get_object_or_404(SolicitacaoLGPD.objects.select_related("usuario"), pk=solicitacao_id)
    decisao = request.POST.get("decisao")
    resposta = request.POST.get("resposta", "")
    try:
        if decisao == "atender":
            atender_solicitacao(solicitacao, request.user.id, resposta)
            messages.success(request, f"Solicitação #{solicitacao.id} atendida.")
        elif decisao == "recusar":
            recusar_solicitacao(solicitacao, request.user.id, resposta)
            messages.success(request, f"Solicitação #{solicitacao.id} recusada. O titular vê a justificativa.")
        elif decisao == "analisar":
            colocar_em_analise(solicitacao, request.user.id)
            messages.success(request, f"Solicitação #{solicitacao.id} em análise.")
        else:
            messages.error(request, "Decisão inválida.")
    except (SolicitacaoNaoAutomatizavelError, SolicitacaoEncerradaError, AutoAtendimentoError, ValueError) as exc:
        messages.error(request, str(exc))
    voltar = request.POST.get("voltar", "")
    if url_has_allowed_host_and_scheme(voltar, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(voltar)
    return redirect("privacy:solicitacoes_admin")