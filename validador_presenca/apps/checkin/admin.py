from datetime import timedelta
from django.contrib import admin
from django.utils import timezone
from .models import ChamadaSession

# Register your models here.

@admin.register(ChamadaSession)
class ChamadaSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "aula", "sala", "professor", "sequencia", "abre_em", "fecha_em")
    list_filter = ("sala", "sequencia")
    list_select_related = ("aula__disciplina", "sala", "professor__usuario")
    readonly_fields = ("data_criacao", "data_atualizacao")

    def save_model(self, request, obj, form, change):
        agora = timezone.now()

        if not obj.abre_em:
            obj.abre_em = agora

        if not obj.fecha_em:
            obj.fecha_em = obj.abre_em + timedelta(minutes=10)

        if obj.aula:
            if not obj.sala_id:
                obj.sala = obj.aula.disciplina.turma.sala
            if not obj.professor_id:
                obj.professor = obj.aula.disciplina.professor

        super().save_model(request, obj, form, change)