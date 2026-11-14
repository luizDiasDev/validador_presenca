import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_SERVER = "https://adsum.up.railway.app"
DEFAULT_CONFIG_PATH = Path.home() / ".adsum" / "sala.json"


@dataclass
class RoomConfig:
    server_url: str = DEFAULT_SERVER
    machine_token: str = ""      # recebido no pareamento; é a "senha" desta máquina na API
    machine_name: str = ""
    room_code: str = ""
    camera_index: int = 0
    camera_backend: str = "auto"

    @property
    def is_paired(self) -> bool:
        return bool(self.machine_token)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> RoomConfig:
    if not path.exists():
        return RoomConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    known_fields = RoomConfig.__dataclass_fields__
    return RoomConfig(**{key: value for key, value in data.items() if key in known_fields})


def save_config(config: RoomConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2, ensure_ascii=False), encoding="utf-8")
