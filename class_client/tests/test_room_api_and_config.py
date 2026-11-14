from types import SimpleNamespace

import pytest
import requests

from room_app.api import ApiError, RoomApi
from room_app.config import RoomConfig, load_config, save_config


class FakeHttp:
    def __init__(self, status=200, body=None, error=None):
        self.calls = []
        self.status, self.body, self.error = status, body or {}, error

    def _answer(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        return SimpleNamespace(status_code=self.status, json=lambda: self.body)

    def get(self, url, **kwargs):
        return self._answer("get", url, **kwargs)

    def post(self, url, **kwargs):
        return self._answer("post", url, **kwargs)


def test_pairing_keeps_the_token_and_sends_no_authorization():
    http = FakeHttp(body={"token": "abc", "apelido": "PC-01"})
    api = RoomApi("https://adsum.test/", http=http)

    api.pair("1234")

    method, url, kwargs = http.calls[0]
    assert url == "https://adsum.test/api/v1/maquinas/parear/"
    assert kwargs["headers"] == {}
    assert api.machine_token == "abc"


def test_calls_after_pairing_carry_the_machine_token():
    http = FakeHttp(body={"pendente": False})
    api = RoomApi("https://adsum.test", machine_token="abc", http=http)

    api.pending_authorization()

    assert http.calls[0][2]["headers"] == {"Authorization": "Bearer abc"}


def test_wrong_pairing_code_is_explained():
    api = RoomApi("https://adsum.test", http=FakeHttp(status=404))

    with pytest.raises(ApiError, match="não encontrado"):
        api.pair("0000")


def test_revoked_token_asks_for_new_pairing():
    api = RoomApi("https://adsum.test", machine_token="old", http=FakeHttp(status=401))

    with pytest.raises(ApiError, match="pareada"):
        api.current_qr()


def test_network_failure_becomes_a_readable_error():
    api = RoomApi("https://adsum.test", machine_token="abc", http=FakeHttp(error=requests.ConnectionError("down")))

    with pytest.raises(ApiError, match="Sem conexão"):
        api.current_qr()


def test_refused_face_comes_back_as_pending_with_the_reason():
    api = RoomApi("https://adsum.test", machine_token="abc",
                  http=FakeHttp(status=422, body={"status": "PENDING", "mensagem": "Amostras de pessoas diferentes."}))

    answer = api.send_face(7, {"samples": []})

    assert answer == {"status": "PENDING", "mensagem": "Amostras de pessoas diferentes."}


def test_config_is_saved_and_loaded(tmp_path):
    path = tmp_path / "sala.json"
    save_config(RoomConfig(server_url="https://adsum.test", machine_token="abc", machine_name="PC-01"), path)

    config = load_config(path)

    assert config.is_paired
    assert config.machine_name == "PC-01"


def test_missing_config_means_not_paired(tmp_path):
    assert not load_config(tmp_path / "nao-existe.json").is_paired
