import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.accounts.decorators import only_admin
from apps.institution.domain.services.pairing_service import (
    CodigoPareamentoInvalidoError,
    MachinePairingService,
)
from apps.institution.forms import CampusForm, MachineForm, RoomForm
from apps.institution.models import Campus, Institution, Machine, Room


def _obter_instituicao_atual(user):
    # Retorna a instituicao atrelada ao usuario ou a primeira cadastrada no servidor
    return (
        getattr(user, "instituicao", None)
        or Institution.objects.order_by("nome").first()
    )


@login_required
@only_admin
def infraestrutura_view(request):
    # Controla a aba ativa na navegacao (maquinas, salas ou campi)
    aba_ativa = request.GET.get("aba", "maquinas")
    instituicao_atual = _obter_instituicao_atual(request.user)

    campi = Campus.objects.select_related("instituicao").order_by("nome")
    salas = Room.objects.select_related("campus__instituicao").order_by("codigo")
    maquinas = Machine.objects.select_related("sala__campus").order_by(
        "sala__codigo", "apelido"
    )

    context = {
        "aba_ativa": aba_ativa,
        "instituicao_atual": instituicao_atual,
        "campi": campi,
        "salas": salas,
        "maquinas": maquinas,
        "campus_form": CampusForm(),
        "room_form": RoomForm(),
        "machine_form": MachineForm(),
    }
    return render(request, "institution/infraestrutura.html", context)


@login_required
@only_admin
@require_POST
def salvar_campus_view(request, campus_id: int | None = None):
    # Salva ou atualiza os dados do campus
    instancia = get_object_or_404(Campus, pk=campus_id) if campus_id else None
    form = CampusForm(request.POST, instance=instancia)

    if form.is_valid():
        campus = form.save(commit=False)
        # Ao cadastrar novo campus, vincula automaticamente a instituicao do servidor
        if not campus_id:
            campus.instituicao = _obter_instituicao_atual(request.user)
        campus.save()
        acao = "atualizado" if campus_id else "cadastrado"
        messages.success(request, f"Campus {campus.nome} {acao} com sucesso.")
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{campo}: {erros[0]}")

    return redirect("/infraestrutura/?aba=campi")


@login_required
@only_admin
@require_POST
def excluir_campus_view(request, campus_id: int):
    # Exclui o campus se nao houver salas vinculadas a ele
    campus = get_object_or_404(Campus, pk=campus_id)
    try:
        nome = campus.nome
        campus.delete()
        messages.success(request, f"Campus {nome} excluído com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir este campus pois já existem salas vinculadas a ele.",
        )
    return redirect("/infraestrutura/?aba=campi")


@login_required
@only_admin
@require_POST
def salvar_sala_view(request, sala_id: int | None = None):
    # Salva ou atualiza a sala fisica
    instancia = get_object_or_404(Room, pk=sala_id) if sala_id else None
    form = RoomForm(request.POST, instance=instancia)

    if form.is_valid():
        sala = form.save()
        acao = "atualizada" if sala_id else "cadastrada"
        messages.success(request, f"Sala {sala.codigo} {acao} com sucesso.")
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{campo}: {erros[0]}")

    return redirect("/infraestrutura/?aba=salas")


@login_required
@only_admin
@require_POST
def excluir_sala_view(request, sala_id: int):
    # Exclui a sala se nao houver maquinas ou turmas vinculadas a ela
    sala = get_object_or_404(Room, pk=sala_id)
    try:
        codigo = sala.codigo
        sala.delete()
        messages.success(request, f"Sala {codigo} excluída com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir esta sala pois já existem máquinas, turmas ou sessões vinculadas a ela.",
        )
    return redirect("/infraestrutura/?aba=salas")


@login_required
@only_admin
@require_POST
def salvar_maquina_view(request, maquina_id: int | None = None):
    # Salva maquina existente ou cria nova gerando codigo de 4 digitos via service
    instancia = get_object_or_404(Machine, pk=maquina_id) if maquina_id else None
    form = MachineForm(request.POST, instance=instancia)

    if form.is_valid():
        if maquina_id:
            maquina = form.save()
            messages.success(
                request, f"Máquina {maquina.apelido} atualizada com sucesso."
            )
        else:
            svc = MachinePairingService()
            maquina = svc.criar_maquina(
                sala=form.cleaned_data["sala"],
                apelido=form.cleaned_data["apelido"],
                autor_id=request.user.id,
            )
            messages.success(
                request,
                f"Máquina {maquina.apelido} criada com código {maquina.codigo_pareamento}.",
            )
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{campo}: {erros[0]}")

    return redirect("/infraestrutura/?aba=maquinas")


@login_required
@only_admin
@require_POST
def excluir_maquina_view(request, maquina_id: int):
    # Exclui a maquina de bancada
    maquina = get_object_or_404(Machine, pk=maquina_id)
    try:
        apelido = maquina.apelido
        maquina.delete()
        messages.success(request, f"Máquina {apelido} excluída com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir esta máquina pois existem registros vinculados a ela.",
        )
    return redirect("/infraestrutura/?aba=maquinas")


@login_required
@only_admin
@require_POST
def regenerar_codigo_view(request, maquina_id: int):
    # Gera um novo codigo de 4 digitos para a maquina informada
    get_object_or_404(Machine, pk=maquina_id)
    svc = MachinePairingService()
    maquina = svc.regenerar_codigo(maquina_id=maquina_id, autor_id=request.user.id)
    messages.success(
        request,
        f"Novo código gerado para {maquina.apelido}: {maquina.codigo_pareamento}.",
    )
    return redirect("/infraestrutura/?aba=maquinas")


@csrf_exempt
@require_POST
def parear_maquina_api(request):
    # Endpoint consumido pelo executavel PySide6 para parear pelo codigo de 4 digitos
    try:
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    codigo = body.get("codigo_pareamento") or request.POST.get("codigo_pareamento", "")
    ip_cliente = request.META.get("REMOTE_ADDR")

    svc = MachinePairingService()
    try:
        maquina = svc.parear_cliente(codigo_pareamento=codigo, ip=ip_cliente)
    except CodigoPareamentoInvalidoError as exc:
        return JsonResponse({"pareado": False, "erro": str(exc)}, status=404)

    return JsonResponse(
        {
            "pareado": True,
            "maquina_id": maquina.id,
            "apelido": maquina.apelido,
            "sala_id": maquina.sala_id,
            "sala_codigo": maquina.sala.codigo,
            "campus_id": maquina.sala.campus_id,
        }
    )
