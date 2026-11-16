from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.decorators import only_teacher
from validador_presenca.pagination import paginar

from .models import PresencaRecord


@login_required
@only_teacher
def painel(request):
    status_filter = request.GET.get("status")

    teacher_records = PresencaRecord.objects.filter(sessao__professor=request.user.professor)
    registers = teacher_records.order_by("-data_criacao")
    if status_filter:
        registers = registers.filter(status=status_filter)

    content = {
        "registers": paginar(request, registers),
        "total": teacher_records.count(),
        "approved": teacher_records.filter(status="APPROVED").count(),
        "pending": teacher_records.filter(status="PENDING").count(),
        "rejected": teacher_records.filter(status="REJECTED").count(),
    }
    return render(request, "validator/painel.html", content)
