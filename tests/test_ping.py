import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

# Явно загружаем main.py как модуль
ROOT_DIR = Path(__file__).resolve().parent.parent
MAIN_PATH = ROOT_DIR / "main.py"

spec = importlib.util.spec_from_file_location("main", MAIN_PATH)
main = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(main)

app = main.app
client = TestClient(app)


def test_ping():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == "pong"
