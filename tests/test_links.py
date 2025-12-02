import importlib.util

from fastapi.testclient import TestClient


def load_app():
    spec = importlib.util.spec_from_file_location("main", "main.py")
    main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main)
    return main.app


def test_links_crud_flow(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db_path}")
    monkeypatch.setenv("BASE_URL", "https://short.io")

    app = load_app()

    with TestClient(app) as client:
        resp = client.get("/api/links")
        assert resp.status_code == 200
        assert resp.json() == []

        resp = client.post(
            "/api/links",
            json={"original_url": "https://google.com", "short_name": "goo"},
        )
        assert resp.status_code == 201
        link = resp.json()
        assert link["id"] == 1

        resp = client.get("/api/links/1")
        assert resp.status_code == 200

        resp = client.put(
            "/api/links/1",
            json={"original_url": "https://ya.ru", "short_name": "ya"},
        )
        assert resp.status_code == 200

        resp = client.delete("/api/links/1")
        assert resp.status_code == 204


def test_links_pagination(tmp_path, monkeypatch):
    test_db_path = tmp_path / "pag.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db_path}")
    monkeypatch.setenv("BASE_URL", "https://short.io")

    app = load_app()

    with TestClient(app) as client:
        for i in range(11):
            r = client.post(
                "/api/links",
                json={
                    "original_url": f"https://example.com/{i}",
                    "short_name": f"seed-{i}",
                },
            )
            assert r.status_code == 201

        r = client.get("/api/links", params={"range": "[0,4]"})
        assert r.status_code == 200
        assert r.headers["Content-Range"] == "links 0-4/11"
        assert len(r.json()) == 5

        r = client.get("/api/links", params={"range": "[5,10]"})
        assert r.status_code == 200
        assert r.headers["Content-Range"] == "links 5-10/11"
        assert len(r.json()) == 6
