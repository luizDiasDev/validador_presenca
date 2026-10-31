from django.contrib import admin
from .models import ChamadaSession

# Register your models here.

@admin.register(ChamadaSession)
class ChamadaSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "sala", "professor", "sequencia", "abre_em", "fecha_em")
    list_filter = ("sala",)
    list_select_related = ("sala", "professor__usuario")
    readonly_fields = ("abre_em", "fecha_em", "data_criacao", "data_atualizacao")