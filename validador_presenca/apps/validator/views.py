from django.shortcuts import render
from .models import PresencaRecord
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import only_teacher

# Create your views here.

@login_required
@only_teacher
def painel(request):
    status_filter = request.GET.get("status")

    registers = PresencaRecord.objects.all().order_by("-data_criacao")
    if status_filter:
        registers = registers.filter(status=status_filter)

    content = {
        "registers": registers,
        "total": PresencaRecord.objects.count(),
        "approved": PresencaRecord.objects.filter(status="APPROVED").count(),
        "pending": PresencaRecord.objects.filter(status="PENDING").count(),
        "rejected": PresencaRecord.objects.filter(status="REJECTED").count()
    }
    return render(request, 'validator/painel.html', content)
