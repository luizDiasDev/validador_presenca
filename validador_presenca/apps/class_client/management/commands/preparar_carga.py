import json
import math
import random
from datetime import time
from importlib import import_module
from pathlib import Path

from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Professor, Usuario
from apps.biometrics.domain.services.biometric_service import BiometricService
from apps.checkin.domain.services.chamada_service import ChamadaService
from apps.checkin.models import ChamadaSession
from apps.institution.domain.services.pairing_service import MachinePairingService
from apps.institution.models import Campus, Institution, Machine, Room
from apps.privacy.models import Termo
from apps.teacher_panel.models import Aluno, Aula, Disciplina, Turma
from apps.validator.models import PresencaRecord

PREFIXO = "CARGA"
DOMINIO = "carga.adsum"
MAQUINAS_POR_SALA = 30
CAMPUS = {"lat": -23.5169621, "lon": -46.1826845}
TAMANHO_DO_VETOR = 512
BANCOS_LOCAIS = ("", "localhost", "127.0.0.1")


def _vetor_unitario(sorteio: random.Random, base=None, ruido=0.0) -> list[float]:
    vetor = [sorteio.gauss(0, 1) for _ in range(TAMANHO_DO_VETOR)] if base is None else [
        valor + ruido * sorteio.gauss(0, 1) for valor in base
    ]
    norma = math.sqrt(sum(valor * valor for valor in vetor))
    return [valor / norma for valor in vetor]


def _sessao_logada(usuario) -> str:
    sessao = import_module(settings.SESSION_ENGINE).SessionStore()
    sessao[SESSION_KEY] = str(usuario.pk)
    sessao[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    sessao[HASH_SESSION_KEY] = usuario.get_session_auth_hash()
    sessao.set_expiry(3 * 60 * 60)
    sessao.create()
    usuario.chave_sessao_ativa = sessao.session_key
    usuario.save(update_fields=["chave_sessao_ativa"])
    return sessao.session_key


class Command(BaseCommand):
    help = "Prepara um banco LOCAL para o teste de carga: salas, máquinas pareadas, alunos logados e chamadas abertas."

    def add_arguments(self, parser):
        parser.add_argument("--maquinas", type=int, default=780)
        parser.add_argument("--saida", default="../loadtest/dados_carga.json")
        parser.add_argument("--limpar", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.DATABASES["default"].get("HOST", "") not in BANCOS_LOCAIS:
            raise CommandError("Este comando só roda contra um banco local. Nunca rode em produção.")

        self._limpar()
        if options["limpar"]:
            self.stdout.write(self.style.SUCCESS("Dados de carga apagados."))
            return

        sorteio = random.Random(780)
        instituicao, _ = Institution.objects.get_or_create(cnpj="00000000000191", defaults={"nome": f"{PREFIXO} Universidade"})
        campus = Campus.objects.create(
            instituicao=instituicao, nome=f"{PREFIXO} Campus", latitude=str(CAMPUS["lat"]),
            longitude=str(CAMPUS["lon"]), raio_metros=300,
        )
        Termo.objects.get_or_create(
            instituicao=instituicao, tipo=Termo.TIPO_BIOMETRICO, versao="carga",
            defaults={"titulo": "Termo biométrico", "conteudo": "Carga", "documento_hash": "0" * 64, "ativo": True},
        )
        professor_usuario = Usuario.objects.create_user(email=f"professor@{DOMINIO}", password=None, instituicao=instituicao)
        professor = Professor.objects.create(usuario=professor_usuario, area_atuacao="Carga")

        biometria = BiometricService()
        pareamento = MachinePairingService()
        maquinas, alunos = [], []
        total_salas = math.ceil(options["maquinas"] / MAQUINAS_POR_SALA)

        for numero_sala in range(1, total_salas + 1):
            sala = Room.objects.create(campus=campus, codigo=f"{PREFIXO}-{numero_sala:02d}", nome=f"Laboratório de carga {numero_sala}")
            turma = Turma.objects.create(
                sala=sala, codigo=f"CG{numero_sala:02d}", nome=f"Turma de carga {numero_sala}",
                curso="Carga", semestre_inicio=timezone.localdate(),
            )
            disciplina = Disciplina.objects.create(professor=professor, turma=turma, nome=f"{PREFIXO} {numero_sala:02d}")
            aula = Aula.objects.create(
                disciplina=disciplina, dia_semana=timezone.localdate().weekday(),
                hora_inicio=time(0, 0), hora_fim=time(23, 59), tempos_aula=4,
            )
            ChamadaService().abrir(sala_id=sala.id, professor=professor, aula=aula, duracao_min=120, tempos_cobertos=4)

            restantes = options["maquinas"] - len(maquinas)
            for numero in range(1, min(MAQUINAS_POR_SALA, restantes) + 1):
                maquina = pareamento.criar_maquina(sala=sala, apelido=f"{PREFIXO}-{numero_sala:02d}-{numero:02d}", autor_id=0)
                maquinas.append({"token": pareamento.emitir_token(maquina)})

                indice = len(alunos) + 1
                usuario = Usuario.objects.create_user(email=f"aluno{indice:04d}@{DOMINIO}", password=None, instituicao=instituicao)
                Aluno.objects.create(usuario=usuario, turma=turma, matricula=f"{PREFIXO}{indice:05d}")
                rosto = _vetor_unitario(sorteio)
                biometria.grant_consent(usuario)
                biometria.enroll(
                    usuario, [_vetor_unitario(sorteio, rosto, 0.02) for _ in range(5)],
                    live_score=0.95, live_status="ok", challenge_passed=True,
                )
                alunos.append({"sessionid": _sessao_logada(usuario), "maquina": len(maquinas) - 1, "rosto": rosto})

        saida = Path(options["saida"])
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(json.dumps({"campus": CAMPUS, "maquinas": maquinas, "alunos": alunos}), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(
            f"{total_salas} salas, {len(maquinas)} máquinas e {len(alunos)} alunos prontos. Dados em {saida}."
        ))

    def _limpar(self):
        campi = Campus.objects.filter(nome=f"{PREFIXO} Campus")
        salas = Room.objects.filter(campus__in=campi)
        sessoes = ChamadaSession.objects.filter(sala__in=salas)
        PresencaRecord.objects.filter(sessao__in=sessoes).delete()
        sessoes.delete()
        turmas = Turma.objects.filter(sala__in=salas)
        Aula.objects.filter(disciplina__turma__in=turmas).delete()
        Disciplina.objects.filter(turma__in=turmas).delete()
        Aluno.objects.filter(turma__in=turmas).delete()
        Professor.objects.filter(usuario__email__endswith=f"@{DOMINIO}").delete()
        Usuario.objects.filter(email__endswith=f"@{DOMINIO}").delete()
        turmas.delete()
        Machine.objects.filter(sala__in=salas).delete()
        salas.delete()
        campi.delete()
