from django.contrib import admin
from .models import Institution, Campus, Room, Machine

# Register your models here.


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "cnpj", "data_criacao")
    search_fields = ("nome", "cnpj")


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "instituicao", "latitude", "longitude", "raio_metros")
    list_filter = ("instituicao",)
    search_fields = ("nome",)
    list_select_related = ("instituicao",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("id", "codigo", "nome", "campus")
    list_filter = ("campus",)
    search_fields = ("codigo", "nome")
    list_select_related = ("campus__instituicao",)


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("id", "apelido", "codigo_pareamento", "sala", "ip", "visto_em")
    list_filter = ("sala__campus", "sala")
    search_fields = ("apelido", "codigo_pareamento", "ip")
    list_select_related = ("sala__campus",)
