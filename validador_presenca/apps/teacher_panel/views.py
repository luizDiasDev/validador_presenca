from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.decorators import only_admin, only_teacher, only_teacher_or_admin
from apps.accounts.models import Professor
from apps.checkin.domain.services.chamada_service import (
    ChamadaJaAbertaError,
    ChamadaJaEncerradaError,
    ChamadaSemPermissaoError,
    ChamadaService,
)
from apps.checkin.models import ChamadaSession
from apps.institution.models import Room
from apps.teacher_panel.domain.services.dashboard_service import DashboardService
from apps.teacher_panel.domain.services.revisao_service import RevisaoPresencaService
from apps.teacher_panel.forms import (
    AbrirChamadaForm,
    AgendamentoChamadaForm,
    AlunoCadastroForm,
    ProfessorCadastroForm,
    AulaForm,
    DisciplinaForm,
    RevisaoPresencaForm,
    TurmaForm,
)
from apps.teacher_panel.models import Aluno, Aula, Disciplina, Turma
from apps.audit.domain.log_register import registrar_acao
from apps.checkin.domain.services.faltas_service import registrar_faltas_pendentes
from apps.checkin.models import AgendamentoChamada
from apps.biometrics.models import Biometria
from apps.privacy.domain.term_acceptance import situacao_da_biometria, situacao_dos_termos
from apps.validator.models import PresencaRecord
from validador_presenca.pagination import paginar


@login_required
@only_teacher
def turmas_view(request):
    professor = request.user.professor
    aba_ativa = "disciplinas" if request.GET.get("aba") == "disciplinas" else "aulas"

    turmas = Turma.objects.order_by("codigo")
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
        "turmas": turmas,
        "disciplinas": disciplinas,
        "aulas": aulas,
        "dias_semana": Aula.DIAS_SEMANA,
    }
    return render(request, "teacher_panel/turmas.html", context)


@login_required
@only_admin
def gestao_turmas_view(request):
    turmas = (
        Turma.objects.select_related("sala")
        .annotate(
            total_alunos=Count("alunos", distinct=True),
            total_disciplinas=Count("disciplinas", distinct=True),
        )
        .order_by("codigo")
    )
    salas = Room.objects.order_by("codigo")
    return render(request, "teacher_panel/gestao_turmas.html", {"turmas": paginar(request, turmas), "salas": salas})


@login_required
@only_admin
@require_POST
def salvar_turma_view(request, turma_id: int | None = None):
    instancia = get_object_or_404(Turma, pk=turma_id) if turma_id else None
    form = TurmaForm(request.POST, instance=instancia)

    if form.is_valid():
        turma = form.save()
        acao = "atualizada" if turma_id else "cadastrada"
        registrar_acao(request.user, "teacher_panel", "TURMA_ATUALIZADA" if turma_id else "TURMA_CRIADA",
                       "turma", turma.id, {"codigo": turma.codigo, "nome": turma.nome})
        messages.success(request, f"Turma {turma.codigo} {acao} com sucesso.")
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{campo}: {erros[0]}")

    return redirect("teacher_panel:gestao_turmas")


@login_required
@only_admin
@require_POST
def excluir_turma_view(request, turma_id: int):
    turma = get_object_or_404(Turma, pk=turma_id)
    try:
        codigo = turma.codigo
        turma.delete()
        registrar_acao(request.user, "teacher_panel", "TURMA_EXCLUIDA", "turma", turma_id, {"codigo": codigo})
        messages.success(request, f"Turma {codigo} excluída com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir esta turma pois já existem disciplinas ou alunos vinculados a ela.",
        )
    return redirect("teacher_panel:gestao_turmas")


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
        registrar_acao(request.user, "teacher_panel", "DISCIPLINA_ATUALIZADA" if disciplina_id else "DISCIPLINA_CRIADA",
                       "disciplina", disciplina.id, {"nome": disciplina.nome, "turma_id": disciplina.turma_id})
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
        registrar_acao(request.user, "teacher_panel", "DISCIPLINA_EXCLUIDA", "disciplina", disciplina_id, {"nome": nome})
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
        aula = form.save()
        acao = "atualizado" if aula_id else "cadastrado"
        registrar_acao(request.user, "teacher_panel", "AULA_ATUALIZADA" if aula_id else "AULA_CRIADA", "aula", aula.id,
                       {"disciplina_id": aula.disciplina_id, "dia_semana": aula.dia_semana})
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
        registrar_acao(request.user, "teacher_panel", "AULA_EXCLUIDA", "aula", aula_id)
        messages.success(request, "Horário de aula excluído com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir esta aula pois já existem sessões de chamada registradas nela.",
        )
    return redirect("/turmas/?aba=aulas")


@login_required
@only_teacher_or_admin
def alunos_view(request):

    turma_filtro = request.GET.get("turma", "")
    turmas = Turma.objects.select_related("sala").order_by("codigo")

    alunos = Aluno.objects.select_related("usuario", "turma__sala").order_by(
        "turma__codigo", "matricula"
    )
    if turma_filtro.isdigit():
        alunos = alunos.filter(turma_id=int(turma_filtro))

    pagina = paginar(request, alunos)
    usuarios_ids = [aluno.usuario_id for aluno in pagina]
    termos = situacao_dos_termos(usuarios_ids)
    biometria = situacao_da_biometria(usuarios_ids)
    com_rosto = set(Biometria.objects.filter(usuario_id__in=usuarios_ids).values_list("usuario_id", flat=True))
    for aluno in pagina:
        aluno.situacao_termos = termos[aluno.usuario_id]
        aluno.situacao_biometria = biometria[aluno.usuario_id]
        aluno.rosto_cadastrado = aluno.usuario_id in com_rosto

    context = {
        "alunos": pagina,
        "turmas": turmas,
        "turma_filtro": int(turma_filtro) if turma_filtro.isdigit() else None,
        "total_alunos": pagina.paginator.count,
    }
    return render(request, "teacher_panel/alunos.html", context)


@login_required
@only_admin
@require_POST
def salvar_aluno_view(request, aluno_id: int | None = None):
    instancia = (
        get_object_or_404(Aluno.objects.select_related("usuario"), pk=aluno_id)
        if aluno_id
        else None
    )
    form = AlunoCadastroForm(request.POST, aluno_instance=instancia)

    if form.is_valid():
        aluno = form.save(instituicao=getattr(request.user, "instituicao", None))
        registrar_acao(request.user, "teacher_panel", "ALUNO_ATUALIZADO" if aluno_id else "ALUNO_CADASTRADO", "aluno",
                       aluno.id, {"usuario_id": aluno.usuario_id, "matricula": aluno.matricula, "turma_id": aluno.turma_id})
        acao = (
            "atualizado" if aluno_id else f"matriculado na turma {aluno.turma.codigo}"
        )
        messages.success(
            request, f"Aluno {aluno.usuario.get_full_name()} {acao} com sucesso."
        )
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{erros[0]}")

    return redirect("teacher_panel:alunos")


@login_required
@only_admin
@require_POST
def excluir_aluno_view(request, aluno_id: int):
    aluno = get_object_or_404(Aluno.objects.select_related("usuario"), pk=aluno_id)
    try:
        nome = aluno.usuario.get_full_name() or aluno.usuario.email
        usuario = aluno.usuario
        usuario_id = usuario.id
        aluno.delete()
        usuario.delete()
        registrar_acao(request.user, "teacher_panel", "ALUNO_EXCLUIDO", "aluno", aluno_id, {"usuario_id": usuario_id})
        messages.success(request, f"Aluno {nome} excluído com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir este aluno pois já existem registros vinculados a ele.",
        )
    return redirect("teacher_panel:alunos")

@login_required
@only_admin
def professores_view(request):
    pagina = paginar(
        request,
        Professor.objects.select_related("usuario")
        .annotate(total_disciplinas=Count("disciplinas"))
        .order_by("usuario__first_name", "usuario__last_name"),
    )
    termos = situacao_dos_termos([professor.usuario_id for professor in pagina])
    for professor in pagina:
        professor.situacao_termos = termos[professor.usuario_id]

    context = {
        "professores": pagina,
        "total_professores": pagina.paginator.count,
    }
    return render(request, "teacher_panel/professores.html", context)


@login_required
@only_admin
@require_POST
def salvar_professor_view(request, professor_id: int | None = None):
    instancia = (
        get_object_or_404(Professor.objects.select_related("usuario"), pk=professor_id)
        if professor_id
        else None
    )
    form = ProfessorCadastroForm(request.POST, professor_instance=instancia)

    if form.is_valid():
        professor = form.save(instituicao=getattr(request.user, "instituicao", None))
        registrar_acao(request.user, "teacher_panel", "PROFESSOR_ATUALIZADO" if professor_id else "PROFESSOR_CADASTRADO",
                       "professor", professor.id, {"usuario_id": professor.usuario_id})
        acao = "atualizado" if professor_id else "cadastrado"
        messages.success(
            request, f"Professor {professor.usuario.get_full_name()} {acao} com sucesso."
        )
    else:
        for campo, erros in form.errors.items():
            messages.error(request, f"{erros[0]}")

    return redirect("teacher_panel:professores")


@login_required
@only_admin
@require_POST
def excluir_professor_view(request, professor_id: int):
    professor = get_object_or_404(Professor.objects.select_related("usuario"), pk=professor_id)
    try:
        nome = professor.usuario.get_full_name() or professor.usuario.email
        usuario = professor.usuario
        usuario_id = usuario.id
        professor.delete()
        usuario.delete()
        registrar_acao(request.user, "teacher_panel", "PROFESSOR_EXCLUIDO", "professor", professor_id, {"usuario_id": usuario_id})
        messages.success(request, f"Professor {nome} excluído com sucesso.")
    except ProtectedError:
        messages.error(
            request,
            "Não é possível excluir este professor pois ele já possui disciplinas ou chamadas vinculadas.",
        )
    return redirect("teacher_panel:professores")


@login_required
@only_teacher
def chamadas_view(request):
    registrar_faltas_pendentes()
    professor = request.user.professor
    ChamadaService().abrir_agendadas_do_professor(professor)
    agora = timezone.now()
    data_hoje = timezone.localdate()
    dia_semana_hoje = data_hoje.weekday()
    dia_hoje_nome = dict(Aula.DIAS_SEMANA).get(dia_semana_hoje, "")

    form = AbrirChamadaForm(professor=professor)
    agora_local = timezone.localtime(agora)
    aulas_de_hoje = [a for a in form.fields["aula"].queryset if a.dia_semana == dia_semana_hoje]
    aula_em_andamento = next(
        (a for a in aulas_de_hoje if a.hora_inicio <= agora_local.time() < a.hora_fim), None
    )
    aula_sugerida = aula_em_andamento or (aulas_de_hoje[0] if aulas_de_hoje else None)
    agendamentos = AgendamentoChamada.objects.filter(aula__disciplina__professor=professor).select_related(
        "aula__disciplina__turma"
    )

    sessoes = paginar(
        request,
        ChamadaSession.objects.filter(professor=professor)
        .select_related("aula__disciplina__turma", "sala")
        .order_by("-abre_em"),
    )
    sessoes_abertas_ids = {s.id for s in sessoes if s.abre_em <= agora < s.fecha_em}

    context = {
        "form": form,
        "sessoes": sessoes,
        "sessoes_abertas_ids": sessoes_abertas_ids,
        "agendamentos": agendamentos,
        "aula_sugerida_id": aula_sugerida.id if aula_sugerida else None,
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
    limite_por_maquina = form.cleaned_data["limite_por_maquina"]

    sala = aula.disciplina.turma.sala
    service = ChamadaService()

    try:
        sessao = service.abrir(
            sala_id=sala.id,
            professor=professor,
            aula=aula,
            duracao_min=duracao_min,
            tempos_cobertos=tempos_cobertos,
            limite_por_maquina=limite_por_maquina,
        )
        aviso = " (ajustada para fechar no fim da aula)" if form.duracao_ajustada else ""
        messages.success(
            request,
            f"Chamada #{sessao.id} aberta na sala {sala.codigo} por {duracao_min} min{aviso}.",
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
@require_POST
def agendar_chamada_view(request):
    form = AgendamentoChamadaForm(request.POST, professor=request.user.professor)
    if form.is_valid():
        agendamento = form.save()
        registrar_acao(request.user, "checkin", "CHAMADA_AGENDADA", "agendamento_chamada", agendamento.id, {
            "aula_id": agendamento.aula_id, "horario": agendamento.horario.strftime("%H:%M"),
            "duracao_min": agendamento.duracao_min,
        })
        messages.success(
            request,
            f"Chamada agendada para {agendamento.aula.get_dia_semana_display()} às {agendamento.horario:%H:%M}.",
        )
    else:
        for erro in form.non_field_errors():
            messages.error(request, erro)
        for campo, erros in form.errors.items():
            if campo != "__all__":
                messages.error(request, f"{form.fields[campo].label}: {erros[0]}")
    return redirect("teacher_panel:chamadas")


@login_required
@only_teacher
@require_POST
def excluir_agendamento_view(request, agendamento_id: int):
    agendamento = get_object_or_404(
        AgendamentoChamada, pk=agendamento_id, aula__disciplina__professor=request.user.professor
    )
    horario = agendamento.horario.strftime("%H:%M")
    agendamento.delete()
    registrar_acao(request.user, "checkin", "AGENDAMENTO_EXCLUIDO", "agendamento_chamada", agendamento_id,
                   {"horario": horario})
    messages.success(request, f"Agendamento das {horario} removido.")
    return redirect("teacher_panel:chamadas")


@login_required
@only_teacher
def pendencias_view(request):
    professor = request.user.professor
    registros_do_professor = PresencaRecord.objects.filter(sessao__professor=professor)

    pendentes = (
        registros_do_professor.filter(status="PENDING")
        .select_related(
            "usuario",
            "sessao__aula__disciplina__turma",
            "sessao__sala",
            "maquina__sala",
        )
        .order_by("-data_criacao")
    )
    revisados = (
        registros_do_professor.exclude(status="PENDING")
        .filter(revisado_por__isnull=False)
        .select_related(
            "usuario",
            "sessao__aula__disciplina__turma",
            "sessao__sala",
            "maquina__sala",
        )
        .order_by("-data_revisao")[:20]
    )

    context = {
        "pendentes": paginar(request, pendentes),
        "revisados": revisados,
        "total_pendentes": pendentes.count(),
    }
    return render(request, "teacher_panel/pendencias.html", context)


@login_required
@only_teacher
@require_POST
def revisar_pendencia_view(request, registro_id: int):
    get_object_or_404(
        PresencaRecord,
        pk=registro_id,
        status="PENDING",
        sessao__professor=request.user.professor,
    )
    form = RevisaoPresencaForm(request.POST)

    if not form.is_valid():
        for _, erros in form.errors.items():
            messages.error(request, erros[0])
        return redirect("teacher_panel:pendencias")

    try:
        registro = RevisaoPresencaService().revisar(
            registro_id=registro_id,
            autor_id=request.user.id,
            novo_status=form.cleaned_data["status"],
            motivo=form.cleaned_data["motivo"],
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("teacher_panel:pendencias")

    messages.success(
        request, f"Registro #{registro.id} atualizado para {registro.status}."
    )
    return redirect("teacher_panel:pendencias")


@login_required
@only_teacher_or_admin
def dashboard_view(request):
    registrar_faltas_pendentes()

    professor = getattr(request.user, "professor", None)
    turma_param = request.GET.get("turma", "")
    turma_id = int(turma_param) if turma_param.isdigit() else None

    context = DashboardService().gerar_dados(
        professor=professor,
        turma_id=turma_id,
        data_inicio=_data_do_filtro(request.GET.get("de")),
        data_fim=_data_do_filtro(request.GET.get("ate")),
    )
    return render(request, "teacher_panel/dashboard.html", context)


def _data_do_filtro(valor):
    try:
        return date.fromisoformat(valor) if valor else None
    except ValueError:
        return None
