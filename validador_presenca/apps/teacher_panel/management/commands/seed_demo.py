import random
import secrets
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Professor, Usuario
from apps.checkin.models import ChamadaSession
from apps.institution.models import Room
from apps.teacher_panel.models import Aluno, Aula, Disciplina, Turma
from apps.validator.models import PresencaRecord

TURMA_DEMO = "DEMO-01"
DOMINIO_DEMO = "demo.adsum"
NOMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabriela", "Heitor", "Isabela", "João",
    "Karina", "Lucas", "Marina", "Nicolas", "Olívia", "Pedro", "Rafaela", "Samuel", "Tatiane", "Vitor",
    "Yasmin", "Wagner", "Bianca", "Caio", "Débora", "Eduardo", "Fernanda", "Gustavo", "Helena", "Igor",
]
SOBRENOMES = ["Silva", "Souza", "Oliveira", "Santos", "Lima", "Pereira", "Costa", "Almeida", "Ribeiro", "Carvalho"]


def _decimal(valor: float) -> Decimal:
    return Decimal(str(round(valor, 3)))


def _registro(sorteio: random.Random, sessao, usuario, assiduidade: float, revisor_id: int):
    sorte = sorteio.random()
    if sorte > assiduidade:
        return None

    facial = sorteio.uniform(0.82, 0.98)
    vida = sorteio.uniform(0.85, 0.99)
    campos = {"status": "APPROVED", "aprovado": True, "geo_valida": True, "motivo": ""}

    faixa = sorteio.random()
    if faixa < 0.06:
        facial = sorteio.uniform(0.45, 0.65)
        campos = {"status": "PENDING", "aprovado": False, "geo_valida": True,
                  "motivo": "Pontuação intermediária: o professor precisa confirmar"}
    elif faixa < 0.10:
        facial, vida = 0.0, 0.0
        campos = {"status": "REJECTED", "aprovado": False, "geo_valida": False,
                  "motivo": f"Coordenada a {sorteio.randint(900, 4000)} m do campus (raio permitido: 300 m)"}

    registro = PresencaRecord(
        sessao=sessao, usuario=usuario, qr_token_hash=secrets.token_hex(32),
        score_facial=_decimal(facial), score_vida=_decimal(vida),
        score_final=_decimal(0.7 * facial + 0.3 * vida), origem="qr+facial", **campos,
    )
    if campos["status"] == "PENDING" and sessao.fecha_em < timezone.now() - timedelta(days=7):
        registro.status = "APPROVED"
        registro.aprovado = True
        registro.revisado_por = revisor_id
        registro.data_revisao = sessao.fecha_em + timedelta(days=1)
        registro.motivo = "Revisão manual: aluno conferido em sala"
    return registro


class Command(BaseCommand):
    help = "Cria uma turma de demonstração (DEMO-01) com alunos e chamadas passadas para o dashboard."

    def add_arguments(self, parser):
        parser.add_argument("--professor", help="E-mail do professor que recebe a disciplina de demonstração.")
        parser.add_argument("--alunos", type=int, default=24)
        parser.add_argument("--semanas", type=int, default=10)
        parser.add_argument("--limpar", action="store_true", help="Apaga todos os dados de demonstração.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["limpar"]:
            self._limpar()
            return

        if Turma.objects.filter(codigo=TURMA_DEMO).exists():
            raise CommandError("Os dados de demonstração já existem. Rode com --limpar antes de recriar.")
        professor = Professor.objects.filter(usuario__email=options["professor"]).select_related("usuario").first()
        if professor is None:
            raise CommandError("Informe com --professor o e-mail de um professor cadastrado.")
        sala = Room.objects.order_by("id").first()
        if sala is None:
            raise CommandError("Cadastre ao menos uma sala antes de gerar a demonstração.")

        sorteio = random.Random(2026)
        hoje = timezone.localdate()
        turma = Turma.objects.create(
            sala=sala, codigo=TURMA_DEMO, nome="Turma de demonstração", curso="Engenharia de Software",
            semestre_inicio=hoje - timedelta(weeks=options["semanas"] + 1),
        )
        disciplina = Disciplina.objects.create(professor=professor, turma=turma, nome="Demonstração de Frequência")
        aula = Aula.objects.create(
            disciplina=disciplina, dia_semana=hoje.weekday(), hora_inicio=time(19, 10), hora_fim=time(22, 0), tempos_aula=4,
        )

        alunos = []
        for numero in range(1, options["alunos"] + 1):
            nome = NOMES[(numero - 1) % len(NOMES)]
            sobrenome = SOBRENOMES[(numero - 1) % len(SOBRENOMES)]
            usuario = Usuario.objects.create_user(
                email=f"demo.aluno{numero:02d}@{DOMINIO_DEMO}", password=None,
                first_name=nome, last_name=sobrenome, instituicao=professor.usuario.instituicao,
            )
            Aluno.objects.create(usuario=usuario, turma=turma, matricula=f"DEMO{numero:04d}")
            assiduidade = 0.55 if numero % 8 == 0 else 0.72 if numero % 5 == 0 else 0.95
            alunos.append((usuario, assiduidade))

        registros = []
        datas = []
        for semana in range(options["semanas"], 0, -1):
            dia = hoje - timedelta(weeks=semana)
            abertura = timezone.make_aware(datetime.combine(dia, time(19, 15)))
            sessao = ChamadaSession.objects.create(
                aula=aula, sala=sala, professor=professor, tempos_cobertos=4,
                abre_em=abertura, fecha_em=abertura + timedelta(minutes=10),
            )
            for usuario, assiduidade in alunos:
                registro = _registro(sorteio, sessao, usuario, assiduidade, professor.usuario_id)
                if registro:
                    registros.append(registro)
                    datas.append(abertura + timedelta(seconds=sorteio.randint(20, 540)))

        PresencaRecord.objects.bulk_create(registros)
        for registro, data in zip(registros, datas, strict=True):
            registro.data_criacao = data
        PresencaRecord.objects.bulk_update(registros, ["data_criacao"])

        self.stdout.write(self.style.SUCCESS(
            f"Turma {TURMA_DEMO} criada com {len(alunos)} alunos, {options['semanas']} chamadas e {len(registros)} check-ins."
        ))

    def _limpar(self):
        turma = Turma.objects.filter(codigo=TURMA_DEMO).first()
        if turma is None:
            self.stdout.write("Não há dados de demonstração para apagar.")
            return
        sessoes = ChamadaSession.objects.filter(aula__disciplina__turma=turma)
        PresencaRecord.objects.filter(sessao__in=sessoes).delete()
        sessoes.delete()
        Aula.objects.filter(disciplina__turma=turma).delete()
        Disciplina.objects.filter(turma=turma).delete()
        usuarios_ids = list(
            Usuario.objects.filter(aluno__turma=turma, email__endswith=f"@{DOMINIO_DEMO}").values_list("id", flat=True)
        )
        Aluno.objects.filter(turma=turma).delete()
        Usuario.objects.filter(id__in=usuarios_ids).delete()
        turma.delete()
        self.stdout.write(self.style.SUCCESS("Dados de demonstração apagados."))
