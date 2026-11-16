from django.contrib import admin, messages

from apps.privacy.domain.lgpd_service import (
    AutoAtendimentoError,
    SolicitacaoEncerradaError,
    SolicitacaoNaoAutomatizavelError,
    atender_solicitacao,
    colocar_em_analise,
)
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

    readonly_fields = ["usuario", "tipo", "justificativa", "data_solicitacao", "status", "data_resposta"]

    fieldsets = [
        ("Solicitação (do titular)", {
            "fields": ["usuario", "tipo", "justificativa", "data_solicitacao"],
        }),
        ("Resposta (do DPO)", {
            "description": "Para atender ou recusar, use a tela Solicitações LGPD do painel ou as ações da lista.",
            "fields": ["status", "resposta_dpo", "data_resposta"],
        }),
    ]

    actions = ["marcar_como_em_analise", "marcar_como_atendida"]

    def usuario_email(self, obj):
        return obj.usuario.email
    usuario_email.short_description = "Usuário"

    def marcar_como_em_analise(self, request, queryset):
        atualizadas = 0
        for solicitacao in queryset:
            try:
                colocar_em_analise(solicitacao, request.user.id)
                atualizadas += 1
            except SolicitacaoEncerradaError as exc:
                self.message_user(request, str(exc), level=messages.WARNING)
        self.message_user(request, f"{atualizadas} solicitação(ões) marcada(s) como 'em análise'.")
    marcar_como_em_analise.short_description = "Marcar como 'Em análise'"

    def marcar_como_atendida(self, request, queryset):
        atendidas = 0
        for solicitacao in queryset.select_related("usuario"):
            try:
                atender_solicitacao(solicitacao, request.user.id)
                atendidas += 1
            except (SolicitacaoNaoAutomatizavelError, SolicitacaoEncerradaError, AutoAtendimentoError) as exc:
                self.message_user(request, f"#{solicitacao.id}: {exc}", level=messages.WARNING)
        self.message_user(request, f"{atendidas} solicitação(ões) atendida(s).")
    marcar_como_atendida.short_description = "Atender (revoga, anonimiza ou libera a exportação)"
