import hashlib
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.privacy.models import Termo


class Command(BaseCommand):
    help = "Publica uma nova versão de um documento e desativa a anterior. No próximo login, todos aceitam de novo."

    def add_arguments(self, parser):
        parser.add_argument("tipo", choices=[tipo for tipo, _ in Termo.TIPO_CHOICES])
        parser.add_argument("versao")
        parser.add_argument("arquivo", help="Arquivo markdown com o conteúdo do documento.")
        parser.add_argument("--titulo")

    @transaction.atomic
    def handle(self, *args, **options):
        caminho = Path(options["arquivo"])
        if not caminho.exists():
            raise CommandError(f"Arquivo {caminho} não encontrado.")

        anterior = Termo.objects.filter(tipo=options["tipo"], ativo=True).first()
        if anterior is None:
            raise CommandError("Não existe versão ativa deste documento para substituir.")
        if Termo.objects.filter(
            instituicao=anterior.instituicao, tipo=options["tipo"], versao=options["versao"]
        ).exists():
            raise CommandError(f"A versão {options['versao']} já foi publicada.")

        conteudo = caminho.read_text(encoding="utf-8").strip()
        Termo.objects.filter(instituicao=anterior.instituicao, tipo=options["tipo"], ativo=True).update(ativo=False)
        novo = Termo.objects.create(
            instituicao=anterior.instituicao,
            tipo=options["tipo"],
            versao=options["versao"],
            titulo=options["titulo"] or anterior.titulo,
            conteudo=conteudo,
            documento_hash=hashlib.sha256(conteudo.encode()).hexdigest(),
            ativo=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f"{novo.get_tipo_display()} v{novo.versao} publicada. A versão {anterior.versao} foi desativada.")
        )
