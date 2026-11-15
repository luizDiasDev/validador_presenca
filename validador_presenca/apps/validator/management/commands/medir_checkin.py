import math
import statistics
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.validator.models import PresencaRecord


def _percentil(valores_ordenados: list, fracao: float) -> float:
    return valores_ordenados[math.ceil(fracao * len(valores_ordenados)) - 1]


def medir_tempos(dias: int | None = None) -> dict | None:
    registros = PresencaRecord.objects.filter(origem="qr+facial", data_decisao__isnull=False)
    if dias:
        registros = registros.filter(data_criacao__gte=timezone.now() - timedelta(days=dias))

    duracoes = sorted(
        (decidido - criado).total_seconds()
        for criado, decidido in registros.values_list("data_criacao", "data_decisao")
    )
    if not duracoes:
        return None

    return {
        "amostras": len(duracoes),
        "media": statistics.fmean(duracoes),
        "mediana": statistics.median(duracoes),
        "p90": _percentil(duracoes, 0.90),
        "p95": _percentil(duracoes, 0.95),
        "minimo": duracoes[0],
        "maximo": duracoes[-1],
    }


class Command(BaseCommand):
    help = "Mede o tempo entre o envio do QR Code pelo celular e o veredito com o rosto, nos check-ins reais."

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, help="Considera só os últimos N dias.")

    def handle(self, *args, **options):
        tempos = medir_tempos(options["dias"])
        if tempos is None:
            self.stdout.write("Nenhum check-in com verificação facial concluída no período.")
            return

        self.stdout.write(f"Check-ins medidos: {tempos['amostras']}")
        for chave, rotulo in (
            ("media", "Média"),
            ("mediana", "Mediana"),
            ("p90", "90% em até"),
            ("p95", "95% em até"),
            ("minimo", "Mínimo"),
            ("maximo", "Máximo"),
        ):
            self.stdout.write(f"{rotulo}: {tempos[chave]:.1f} s")
