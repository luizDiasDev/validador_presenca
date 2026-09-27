from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from apps.privacy.forms import SolicitacaoLGPDForm
from apps.privacy.models import SolicitacaoLGPD, Termo

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


@login_required
def solicitar_direito(request):
    if request.method == "POST":
        form = SolicitacaoLGPDForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.usuario = request.user
            solicitacao.save()
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
    })