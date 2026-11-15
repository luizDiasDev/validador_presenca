import requests

PAIRING_PATH = "/api/v1/maquinas/parear/"
QR_PATH = "/api/v1/maquinas/qr/"
AUTHORIZATION_PATH = "/api/v1/maquinas/autorizacao/"
FACE_PATH = "/api/v1/maquinas/rosto/"


class ApiError(RuntimeError):
    pass


class MachineNotPairedError(ApiError):
    pass


class RoomApi:
    def __init__(self, server_url: str, machine_token: str = "", http=None, timeout_seconds: float = 10.0):
        self.server_url = server_url.rstrip("/")
        self.machine_token = machine_token
        self.http = http or requests.Session()
        self.timeout_seconds = timeout_seconds

    def pair(self, pairing_code: str) -> dict:
        response = self._send("post", PAIRING_PATH, json={"codigo_pareamento": pairing_code}, authenticated=False)
        if response.status_code == 404:
            raise ApiError("Código de pareamento não encontrado.")
        if response.status_code in (409, 429):
            raise ApiError(response.json().get("erro", "O servidor recusou o pareamento."))
        data = self._json(response)
        self.machine_token = data["token"]
        return data

    def current_qr(self) -> dict:
        return self._json(self._send("get", QR_PATH))

    def pending_authorization(self) -> dict:
        return self._json(self._send("get", AUTHORIZATION_PATH))

    def send_face(self, presenca_id: int, payload: dict) -> dict:
        response = self._send("post", FACE_PATH, json={"presenca_id": presenca_id, "payload": payload})
        if response.status_code in (409, 422):
            # 409: a liberação expirou; 422: o rosto não pôde ser usado. O servidor explica.
            return response.json() | {"status": response.json().get("status", "PENDING")}
        return self._json(response)

    def _send(self, method: str, path: str, authenticated: bool = True, **kwargs):
        headers = {"Authorization": f"Bearer {self.machine_token}"} if authenticated else {}
        try:
            return getattr(self.http, method)(
                f"{self.server_url}{path}", headers=headers, timeout=self.timeout_seconds, **kwargs
            )
        except requests.RequestException as error:
            raise ApiError(f"Sem conexão com o servidor: {error}") from error

    @staticmethod
    def _json(response) -> dict:
        if response.status_code == 401:
            raise MachineNotPairedError("Máquina não pareada. Faça o pareamento de novo.")
        if response.status_code >= 400:
            raise ApiError(f"Erro {response.status_code} do servidor.")
        return response.json()
