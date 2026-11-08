from django.urls import path
from . import views

app_name = "institution"

urlpatterns = [
    path("infraestrutura/", views.infraestrutura_view, name="infraestrutura"),
    path("maquinas/criar/", views.salvar_maquina_view, name="criar_maquina"),
    path("maquinas/<int:maquina_id>/editar/",views.salvar_maquina_view,name="editar_maquina",),
    path("maquinas/<int:maquina_id>/excluir/",views.excluir_maquina_view,name="excluir_maquina",),
    path("maquinas/<int:maquina_id>/regenerar/",views.regenerar_codigo_view,name="regenerar_codigo",),
    path("salas/criar/", views.salvar_sala_view, name="criar_sala"),
    path("salas/<int:sala_id>/editar/", views.salvar_sala_view, name="editar_sala"),
    path("salas/<int:sala_id>/excluir/", views.excluir_sala_view, name="excluir_sala"),
    path("campi/criar/", views.salvar_campus_view, name="criar_campus"),
    path("campi/<int:campus_id>/editar/", views.salvar_campus_view, name="editar_campus"),
    path("campi/<int:campus_id>/excluir/",views.excluir_campus_view,name="excluir_campus",),
    path("api/v1/maquinas/parear/", views.parear_maquina_api, name="parear_maquina_api"),
]
