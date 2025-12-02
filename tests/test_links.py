import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
MAIN_PATH = ROOT_DIR / "main.py"


def load_app():
    spec = importlib.util.spec_from_file_location("main", MAIN_PATH)
    main = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(main)
    return main.app


def test_links_crud_flow(tmp_path, monkeypatch):
    # Настраиваем отдельную БД для теста
    test_db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{test_db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("BASE_URL", "https://short.io")

    app = load_app()

    # ВАЖНО: используем контекстный менеджер,
    # чтобы отработал lifespan (создалась таблица link)
    with TestClient(app) as client:
        # 1. Список пуст
        resp = client.get("/api/links")
        assert resp.status_code == 200
        assert resp.json() == []

        # 2. Создаём ссылку
        payload = {
            "original_url": "https://example.com/long-url",
            "short_name": "exmpl",
        }
        resp = client.post("/api/links", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["original_url"] == payload["original_url"]
        assert data["short_name"] == payload["short_name"]
        assert data["short_url"] == "https://short.io/r/exmpl"
        link_id = data["id"]

        # 3. Получаем по id
        resp = client.get(f"/api/links/{link_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == link_id

        # 4. Обновляем
        update_payload = {
            "original_url": "https://example.com/updated",
            "short_name": "exmpl2",
        }
        resp = client.put(f"/api/links/{link_id}", json=update_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["original_url"] == update_payload["original_url"]
        assert data["short_name"] == update_payload["short_name"]
        assert data["short_url"] == "https://short.io/r/exmpl2"

        # 5. Список теперь не пустой
        resp = client.get("/api/links")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1

        # 6. Удаляем
        resp = client.delete(f"/api/links/{link_id}")
        assert resp.status_code == 204

        # 7. Проверяем 404 после удаления
        resp = client.get(f"/api/links/{link_id}")
        assert resp.status_code == 404
