from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Usuario
from apps.privacy.domain.lgpd_service import gravar_exportacao


class Command(BaseCommand):
    help = "Exporta em JSON os dados pessoais de um usuário (portabilidade, art. 18 da LGPD)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--pasta", default="lgpd_exports")

    def handle(self, *args, **options):
        usuario = Usuario.objects.filter(email=options["email"]).first()
        if usuario is None:
            raise CommandError(f"Nenhum usuário com o e-mail {options['email']}.")

        arquivo = gravar_exportacao(usuario, options["pasta"])
        self.stdout.write(self.style.SUCCESS(f"Dados exportados em {arquivo}"))
