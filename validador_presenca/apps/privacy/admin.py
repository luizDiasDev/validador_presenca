from django.contrib import admin
from django.utils import timezone
from apps.privacy.models import AceiteTermo, SolicitacaoLGPD, Termo

# Register your models here.

@admin.register(Termo)
class TermoAdmin(admin.ModelAdmin):
    list_display = ["id", "tipo", "versao", "titulo", "ativo", "data_publicacao"]
    list_filter = ["tipo", "ativo"]
    search_fields = ["titulo", "versao"]
    readonly_fields = ["documento_hash", "data_criacao", "data_atualizacao"]


@admin.register(AceiteTermo)
class AceiteTermoAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "termo", "concedido", "data_concedido"]
    list_filter = ["concedido", "termo__tipo"]
    search_fields = ["usuario__email", "termo__titulo"]
    readonly_fields = ["data_concedido", "data_revogada", "data_criacao", "data_atualizacao"]


@admin.register(SolicitacaoLGPD)
class SolicitacaoLGPDAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario_email", "tipo", "status", "data_solicitacao"]
    list_filter = ["status", "tipo"]
    search_fields = ["usuario__email"]

    readonly_fields = ["usuario", "tipo", "justificativa", "data_solicitacao"]

    fieldsets = [
        ("Solicitação (do titular)", {
            "fields": ["usuario", "tipo", "justificativa", "data_solicitacao"],
        }),
        ("Resposta (do DPO)", {
            "fields": ["status", "resposta_dpo", "data_resposta"],
        }),
    ]

    actions = ["marcar_como_em_analise", "marcar_como_atendida"]

    def usuario_email(self, obj):
        return obj.usuario.email
    usuario_email.short_description = "Usuário"

    def marcar_como_em_analise(self, request, queryset):
        atualizadas = queryset.update(status=SolicitacaoLGPD.STATUS_EM_ANALISE)
        self.message_user(request, f"{atualizadas} solicitação(ões) marcada(s) como 'em análise'.")
    marcar_como_em_analise.short_description = "Marcar como 'Em análise'"

    def marcar_como_atendida(self, request, queryset):
        agora = timezone.now()
        atualizadas = queryset.update(
            status=SolicitacaoLGPD.STATUS_ATENDIDA,
            data_resposta=agora,
        )
        self.message_user(request, f"{atualizadas} solicitação(ões) marcada(s) como 'atendida'.")
    marcar_como_atendida.short_description = "Marcar como 'Atendida'"

    def save_model(self, request, obj, form, change):
        if obj.status in [SolicitacaoLGPD.STATUS_ATENDIDA, SolicitacaoLGPD.STATUS_RECUSADA]:
            if not obj.data_resposta:
                obj.data_resposta = timezone.now()
        super().save_model(request, obj, form, change)