from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ocorrido_em",
        "autor_id",
        "origem",
        "acao",
        "tabela",
        "linha_tabela_id",
    )
    list_filter = ("origem", "acao", "tabela")
    search_fields = ("autor_id", "linha_tabela_id", "hash_anterior", "hash_atual")
    date_hierarchy = "ocorrido_em"
    ordering = ("-id",)

    readonly_fields = (
        "autor_id",
        "ocorrido_em",
        "origem",
        "acao",
        "tabela",
        "linha_tabela_id",
        "payload",
        "hash_anterior",
        "hash_atual",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False