from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Usuario
from apps.privacy.domain.lgpd_service import (
    AutoAtendimentoError,
    SolicitacaoEncerradaError,
    SolicitacaoNaoAutomatizavelError,
    atender_solicitacao,
    gravar_exportacao,
)
from apps.privacy.models import SolicitacaoLGPD


class Command(BaseCommand):
    help = "Atende uma solicitação LGPD: revoga a biometria, anonimiza a conta ou exporta os dados."

    def add_arguments(self, parser):
        parser.add_argument("solicitacao_id", type=int)
        parser.add_argument("--dpo", help="E-mail de quem está atendendo, para a auditoria.")
        parser.add_argument("--pasta", default="lgpd_exports")

    def handle(self, *args, **options):
        solicitacao = (
            SolicitacaoLGPD.objects.select_related("usuario")
            .filter(pk=options["solicitacao_id"])
            .first()
        )
        if solicitacao is None:
            raise CommandError(f"Solicitação #{options['solicitacao_id']} não encontrada.")
        if solicitacao.status in (SolicitacaoLGPD.STATUS_ATENDIDA, SolicitacaoLGPD.STATUS_RECUSADA):
            raise CommandError(f"A solicitação #{solicitacao.id} já foi {solicitacao.get_status_display().lower()}.")

        dpo = Usuario.objects.filter(email=options["dpo"]).first() if options["dpo"] else None
        autor_id = dpo.id if dpo else 0

        if solicitacao.tipo == SolicitacaoLGPD.TIPO_EXPORTAR_DADOS:
            arquivo = gravar_exportacao(solicitacao.usuario, options["pasta"])
            self.stdout.write(f"Arquivo para enviar ao titular: {arquivo}")

        try:
            atender_solicitacao(solicitacao, autor_id)
        except (SolicitacaoNaoAutomatizavelError, SolicitacaoEncerradaError, AutoAtendimentoError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(f"Solicitação #{solicitacao.id} ({solicitacao.get_tipo_display()}) atendida.")
        )
