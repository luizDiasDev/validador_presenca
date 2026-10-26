from django.contrib import admin
from .models import Turma, Aluno, Disciplina, Aula

# Register your models here.

@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome", "curso", "sala")
    list_filter = ("curso", "sala__campus")
    search_fields = ("codigo", "nome", "curso")


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("matricula", "usuario", "turma")
    list_filter = ("turma", "turma__curso")
    search_fields = ("matricula", "usuario__email", "usuario__first_name")
    list_select_related = ("usuario", "turma")


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ("nome", "turma", "professor")
    list_filter = ("turma__curso",)
    search_fields = ("nome", "professor__usuario__email")
    list_select_related = ("turma", "professor__usuario")


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ("disciplina", "dia_semana", "hora_inicio", "hora_fim")
    list_filter = ("dia_semana",)
    list_select_related = ("disciplina__turma",)