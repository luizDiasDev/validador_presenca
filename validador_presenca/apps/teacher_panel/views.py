from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import only_teacher
from apps.checkin.domain.services.chamada_service import (
    ChamadaJaAbertaError,
    ChamadaJaEncerradaError,
    ChamadaSemPermissaoError,
    ChamadaService,
)
from apps.checkin.models import ChamadaSession
from apps.institution.models import Room
from apps.teacher_panel.domain.services.revisao_service import RevisaoPresencaService
from apps.teacher_panel.forms import (
    AbrirChamadaForm,
    AulaForm,
    DisciplinaForm,
    RevisaoPresencaForm,
    TurmaForm,
)
from apps.teacher_panel.models import Aula, Disciplina, Turma
from apps.validator.models import PresencaRecord


@login_required
@only_teacher
def turmas_view(request):
    professor = request.user.professor
    aba_ativa = request.GET.get("aba", "aulas")

    salas = Room.objects.select_related("campus").order_by("codigo")
    turmas = (
        Turma.objects.select_related("sala")
        .prefetch_related("alunos")
        .order_by("codigo")
    )
    disciplinas = (
        Disciplina.objects.filter(professor=professor)
        .select_related("turma__sala")
        .order_by("nome")
    )
    aulas = (
        Aula.objects.filter(disciplina__professor=professor)
        .select_related("disciplina__turma__sala")
        .order_by("dia_semana", "hora_inicio")
    )

    context = {
        "aba_ativa": aba_ativa,
        "salas": salas,
        "turmas": turmas,
        "disciplinas": disciplinas,
        "aulas": aulas,
        "dias_semana": Aula.DIAS_SEMANA,
        "turma_form": TurmaForm(),
        "disciplina_form": DisciplinaForm(),
        "aula_form": AulaForm(professor=professor),
    }
    return render(request, "teacher_panel/turmas.html", context)


@login_required
@only_teacher
@require_POST
def salvar_turma_view(request, turma_id: int | None = None):
    instancia = get_object_or_404(Turma, pk=turma_id) if turma_id else None
    form = TurmaForm(request.POST, instance=instancia)

    if form.is_valid():
        turma = form.save()
        acao = "atualizada" if turma_id else "cadastrada"
        messages.success(request, f"Turma {turma.codigo} {acao} com sucesso.")
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{campo}: {erros[0]}")

    return redirect("/turmas/?aba=turmas")


@login_required
@only_teacher
@require_POST
def excluir_turma_view(request, turma_id: int):
    turma = get_object_or_404(Turma, pk=turma_id)
    try:
        codigo = turma.codigo
        turma.delete()
        messages.success(request, f"Turma {codigo} excluída com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir esta turma pois já existem disciplinas ou alunos vinculados a ela.",
        )
    return redirect("/turmas/?aba=turmas")


@login_required
@only_teacher
@require_POST
def salvar_disciplina_view(request, disciplina_id: int | None = None):
    professor = request.user.professor
    instancia = (
        get_object_or_404(Disciplina, pk=disciplina_id, professor=professor)
        if disciplina_id
        else None
    )
    form = DisciplinaForm(request.POST, instance=instancia)

    if form.is_valid():
        disciplina = form.save(commit=False)
        disciplina.professor = professor
        disciplina.save()
        acao = "atualizada" if disciplina_id else "cadastrada"
        messages.success(request, f"Disciplina {disciplina.nome} {acao} com sucesso.")
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{campo}: {erros[0]}")

    return redirect("/turmas/?aba=disciplinas")


@login_required
@only_teacher
@require_POST
def excluir_disciplina_view(request, disciplina_id: int):
    professor = request.user.professor
    disciplina = get_object_or_404(Disciplina, pk=disciplina_id, professor=professor)
    try:
        nome = disciplina.nome
        disciplina.delete()
        messages.success(request, f"Disciplina {nome} excluída com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir esta disciplina pois já existem aulas vinculadas a ela.",
        )
    return redirect("/turmas/?aba=disciplinas")


@login_required
@only_teacher
@require_POST
def salvar_aula_view(request, aula_id: int | None = None):
    professor = request.user.professor
    instancia = (
        get_object_or_404(Aula, pk=aula_id, disciplina__professor=professor)
        if aula_id
        else None
    )
    form = AulaForm(request.POST, instance=instancia, professor=professor)

    if form.is_valid():
        form.save()
        acao = "atualizado" if aula_id else "cadastrado"
        messages.success(request, f"Horário de aula {acao} com sucesso.")
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{erros[0]}")

    return redirect("/turmas/?aba=aulas")


@login_required
@only_teacher
@require_POST
def excluir_aula_view(request, aula_id: int):
    professor = request.user.professor
    aula = get_object_or_404(Aula, pk=aula_id, disciplina__professor=professor)
    try:
        aula.delete()
        messages.success(request, "Horário de aula excluído com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir esta aula pois já existem sessões de chamada registradas nela.",
        )
    return redirect("/turmas/?aba=aulas")


@login_required
@only_teacher
def chamadas_view(request):
    professor = request.user.professor
    agora = timezone.now()
    data_hoje = timezone.localdate()
    dia_semana_hoje = data_hoje.weekday()
    dia_hoje_nome = dict(Aula.DIAS_SEMANA).get(dia_semana_hoje, "")

    form = AbrirChamadaForm(professor=professor, dia_semana=dia_semana_hoje)

    sessoes = (
        ChamadaSession.objects.filter(professor=professor)
        .select_related("aula__disciplina__turma", "sala")
        .order_by("-abre_em")[:20]
    )
    sessoes_abertas_ids = {s.id for s in sessoes if s.abre_em <= agora < s.fecha_em}

    context = {
        "form": form,
        "sessoes": sessoes,
        "sessoes_abertas_ids": sessoes_abertas_ids,
        "data_hoje": data_hoje,
        "dia_hoje_nome": dia_hoje_nome,
    }
    return render(request, "teacher_panel/chamadas.html", context)


@login_required
@only_teacher
@require_POST
def abrir_chamada_view(request):
    professor = request.user.professor
    form = AbrirChamadaForm(request.POST, professor=professor)

    if not form.is_valid():
        for erro in form.non_field_errors():
            messages.error(request, erro)
        for campo, erros in form.errors.items():
            if campo != "__all__":
                messages.error(request, f"{campo}: {erros[0]}")
        return redirect("teacher_panel:chamadas")

    aula = form.cleaned_data["aula"]
    duracao_min = form.cleaned_data["duracao_min"]
    tempos_cobertos = form.cleaned_data["tempos_cobertos"]

    sala = aula.disciplina.turma.sala
    service = ChamadaService()

    try:
        sessao = service.abrir(
            sala_id=sala.id,
            professor=professor,
            aula=aula,
            duracao_min=duracao_min,
            tempos_cobertos=tempos_cobertos,
        )
        messages.success(
            request,
            f"Chamada #{sessao.id} aberta na sala {sala.codigo} por {duracao_min} min.",
        )
    except (ChamadaJaAbertaError, ValueError) as exc:
        messages.error(request, str(exc))

    return redirect("teacher_panel:chamadas")


@login_required
@only_teacher
@require_POST
def encerrar_chamada_view(request, sessao_id: int):
    professor = request.user.professor
    service = ChamadaService()

    try:
        sessao = service.encerrar(sessao_id=sessao_id, professor=professor)
        messages.success(request, f"Chamada #{sessao.id} encerrada com sucesso.")
    except (ChamadaJaEncerradaError, ChamadaSemPermissaoError) as exc:
        messages.error(request, str(exc))

    return redirect("teacher_panel:chamadas")


@login_required
@only_teacher
def pendencias_view(request):
    pendentes = PresencaRecord.objects.filter(status="PENDING").order_by(
        "-data_criacao"
    )
    revisados = (
        PresencaRecord.objects.exclude(status="PENDING")
        .filter(revisado_por__isnull=False)
        .order_by("-data_revisao")[:20]
    )

    context = {
        "pendentes": pendentes,
        "revisados": revisados,
        "total_pendentes": pendentes.count(),
    }
    return render(request, "teacher_panel/pendencias.html", context)


@login_required
@only_teacher
@require_POST
def revisar_pendencia_view(request, registro_id: int):
    get_object_or_404(PresencaRecord, pk=registro_id)
    form = RevisaoPresencaForm(request.POST)

    if not form.is_valid():
        for _, erros in form.errors.items():
            messages.error(request, erros[0])
        return redirect("teacher_panel:pendencias")

    service = RevisaoPresencaService()
    registro = service.revisar(
        registro_id=registro_id,
        autor_id=request.user.id,
        novo_status=form.cleaned_data["status"],
        motivo=form.cleaned_data["motivo"],
    )

    messages.success(
        request, f"Registro #{registro.id} atualizado para {registro.status}."
    )
    return redirect("teacher_panel:pendencias")
