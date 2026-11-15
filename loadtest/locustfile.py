import itertools
import json
import os
import random
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from locust import HttpUser, constant, events, task

DADOS = json.loads(Path(os.environ.get("CARGA_ARQUIVO", Path(__file__).with_name("dados_carga.json"))).read_text())
CAMPUS = DADOS["campus"]
ROSTO_POR_MAQUINA = {aluno["maquina"]: aluno["rosto"] for aluno in DADOS["alunos"]}

INTERVALO_AUTORIZACAO_S = float(os.environ.get("INTERVALO_AUTORIZACAO_S", 3))
JANELA_DE_CHEGADA_S = float(os.environ.get("JANELA_DE_CHEGADA_S", 300))
INTERVALO_STATUS_S = 2
LIMITE_DE_ESPERA_S = 120

qr_por_maquina = {}
proxima_maquina = itertools.count()
proximo_aluno = itertools.count()


class ComputadorDaSala(HttpUser):
    fixed_count = len(DADOS["maquinas"])
    wait_time = constant(INTERVALO_AUTORIZACAO_S)

    def on_start(self):
        self.indice = next(proxima_maquina)
        token = DADOS["maquinas"][self.indice]["token"]
        self.client.headers["Authorization"] = f"Bearer {token}"
        self.proximo_qr = 0.0
        self.chamada_aberta = False

    @task
    def acompanhar_a_chamada(self):
        if time.monotonic() >= self.proximo_qr:
            resposta = self.client.get("/api/v1/maquinas/qr/", name="sala: QR").json()
            self.chamada_aberta = resposta.get("ativa", False)
            if self.chamada_aberta:
                qr_por_maquina[self.indice] = parse_qs(urlparse(resposta["link"]).query)["t"][0]
            self.proximo_qr = time.monotonic() + resposta.get("atualizar_em_s", 15)

        if not self.chamada_aberta:
            return
        pendente = self.client.get("/api/v1/maquinas/autorizacao/", name="sala: autorização").json()
        if pendente.get("pendente"):
            self.client.post(
                "/api/v1/maquinas/rosto/",
                name="sala: enviar rosto",
                json={
                    "presenca_id": pendente["presenca_id"],
                    "payload": {
                        "embedding": ROSTO_POR_MAQUINA[self.indice],
                        "liveness_score": 0.95,
                        "liveness_status": "ok",
                        "challenge_passed": True,
                    },
                },
            )


class AlunoNoCelular(HttpUser):
    fixed_count = len(DADOS["alunos"])
    wait_time = constant(5)

    def on_start(self):
        self.aluno = DADOS["alunos"][next(proximo_aluno)]
        self.concluiu = False
        self.client.cookies.set("sessionid", self.aluno["sessionid"])
        time.sleep(random.uniform(0, JANELA_DE_CHEGADA_S))

    @task
    def fazer_check_in(self):
        if self.concluiu:
            return
        inicio = time.monotonic()
        self.client.get("/checkin/", name="aluno: abrir o check-in")

        limite = time.monotonic() + LIMITE_DE_ESPERA_S
        while self.aluno["maquina"] not in qr_por_maquina and time.monotonic() < limite:
            time.sleep(0.5)
        token = qr_por_maquina.pop(self.aluno["maquina"], "")

        pagina = self.client.post(
            "/checkin/",
            name="aluno: enviar QR e localização",
            data={"token": token, "lat": CAMPUS["lat"], "lon": CAMPUS["lon"]},
            headers={"X-CSRFToken": self.client.cookies.get("csrftoken", "")},
        ).text
        encontrado = re.search(r"/checkin/presenca/(\d+)/status/", pagina)

        status = "REJECTED"
        if encontrado:
            limite = time.monotonic() + LIMITE_DE_ESPERA_S
            while time.monotonic() < limite:
                time.sleep(INTERVALO_STATUS_S)
                resposta = self.client.get(
                    f"/checkin/presenca/{encontrado.group(1)}/status/", name="aluno: acompanhar status"
                ).json()
                status = resposta["status"]
                if not resposta["aguardando_rosto"]:
                    break

        events.request.fire(
            request_type="FLUXO",
            name="check-in completo (celular + rosto)",
            response_time=(time.monotonic() - inicio) * 1000,
            response_length=0,
            exception=None if status == "APPROVED" else Exception(f"terminou como {status}"),
            context={},
        )
        self.concluiu = True
