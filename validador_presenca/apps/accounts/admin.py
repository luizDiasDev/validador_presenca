from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import Administrador, Professor, Usuario


class UsuarioCreationForm(AdminUserCreationForm):
    class Meta:
        model = Usuario
        fields = ("email", "first_name", "last_name", "instituicao")


class UsuarioChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = "__all__"


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = ("email", "first_name", "last_name", "instituicao", "totp_ativo", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "totp_ativo", "instituicao")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    readonly_fields = ("totp_ativo", "last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {"fields": ("first_name", "last_name", "instituicao")}),
        ("Segundo fator", {"fields": ("totp_ativo",)}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "instituicao", "password1", "password2"),
        }),
    )


admin.site.register(Administrador)
admin.site.register(Professor)
