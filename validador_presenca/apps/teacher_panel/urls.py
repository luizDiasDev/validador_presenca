from django.urls import path
from . import views

app_name = "teacher_panel"

urlpatterns = [
    # Listagem principal e CRUD de Turmas, Disciplinas e Aulas
    path("turmas/", views.turmas_view, name="turmas"),
    path("turmas/criar/", views.salvar_turma_view, name="criar_turma"),
    path("turmas/<int:turma_id>/editar/", views.salvar_turma_view, name="editar_turma"),
    path(
        "turmas/<int:turma_id>/excluir/", views.excluir_turma_view, name="excluir_turma"
    ),
    path("disciplinas/criar/", views.salvar_disciplina_view, name="criar_disciplina"),
    path(
        "disciplinas/<int:disciplina_id>/editar/",
        views.salvar_disciplina_view,
        name="editar_disciplina",
    ),
    path(
        "disciplinas/<int:disciplina_id>/excluir/",
        views.excluir_disciplina_view,
        name="excluir_disciplina",
    ),
    path("aulas/criar/", views.salvar_aula_view, name="criar_aula"),
    path("aulas/<int:aula_id>/editar/", views.salvar_aula_view, name="editar_aula"),
    path("aulas/<int:aula_id>/excluir/", views.excluir_aula_view, name="excluir_aula"),
    # Sessoes de chamada
    path("chamadas/", views.chamadas_view, name="chamadas"),
    path("chamadas/abrir/", views.abrir_chamada_view, name="abrir_chamada"),
    path(
        "chamadas/<int:sessao_id>/encerrar/",
        views.encerrar_chamada_view,
        name="encerrar_chamada",
    ),
    # Revisao de presencas pendentes
    path("pendencias/", views.pendencias_view, name="pendencias"),
    path(
        "pendencias/<int:registro_id>/revisar/",
        views.revisar_pendencia_view,
        name="revisar_pendencia",
    ),
]
