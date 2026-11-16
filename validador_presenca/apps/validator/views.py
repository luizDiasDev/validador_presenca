from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from apps.accounts.decorators import only_teacher
from apps.checkin.domain.services.faltas_service import registrar_faltas_pendentes
from validador_presenca.pagination import paginar

from .models import PresencaRecord

STATUS_VALIDOS = ("APPROVED", "PENDING", "REJECTED")


def _data(valor):
    try:
        return date.fromisoformat(valor) if valor else None
    except ValueError:
        return None


@login_required
@only_teacher
def painel(request):
    registrar_faltas_pendentes()
    status_filter = request.GET.get("status", "")
    busca = request.GET.get("busca", "").strip()
    data_inicio = _data(request.GET.get("de"))
    data_fim = _data(request.GET.get("ate"))

    teacher_records = PresencaRecord.objects.filter(sessao__professor=request.user.professor)
    registers = teacher_records.select_related("usuario__aluno", "sessao__aula__disciplina").order_by("-data_criacao")
    if status_filter in STATUS_VALIDOS:
        registers = registers.filter(status=status_filter)
    if busca:
        registers = registers.filter(
            Q(usuario__first_name__icontains=busca)
            | Q(usuario__last_name__icontains=busca)
            | Q(usuario__email__icontains=busca)
            | Q(usuario__aluno__matricula__icontains=busca)
        )
    if data_inicio:
        registers = registers.filter(data_criacao__date__gte=data_inicio)
    if data_fim:
        registers = registers.filter(data_criacao__date__lte=data_fim)

    content = {
        "registers": paginar(request, registers),
        "total": teacher_records.count(),
        "approved": teacher_records.filter(status="APPROVED").count(),
        "pending": teacher_records.filter(status="PENDING").count(),
        "rejected": teacher_records.filter(status="REJECTED").count(),
        "status_filter": status_filter,
        "busca": busca,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "filtrando": bool(status_filter or busca or data_inicio or data_fim),
    }
    return render(request, "validator/painel.html", content)
