import sys
sys.path.insert(0, ".")
import pytest
import caremate
import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(caremate, "LOG", [])
    monkeypatch.setattr(caremate, "client", object())   # 실제 API는 부르지 않음
    monkeypatch.setitem(app_module.LAST_CHAT, "time", None)
    return app_module.app.test_client()


def test_guardian_page(client):
    r = client.get("/guardian")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "오늘 복약" in html and "보낸 알림" in html and "마지막 대화 시각" in html


def test_api_log_returns_log(client):
    caremate.run_tool("record_medication", {"slot": "아침", "taken": True})
    caremate.run_tool("notify_guardian", {"level": "참고", "summary": "잘 지내세요"})
    data = client.get("/api/log").get_json()
    assert [l["tool"] for l in data] == ["record_medication", "notify_guardian"]
    assert data[0]["slot"] == "아침"


def test_api_log_empty(client):
    assert client.get("/api/log").get_json() == []


def test_last_chat_updates_via_emergency_path(client):
    assert client.get("/api/last_chat").get_json()["time"] is None
    r = client.post("/chat", json={"history": [{"role": "user", "content": "숨이 안 쉬어져요"}]})
    assert r.status_code == 200                       # 응급 경로: Claude 호출 없음
    assert client.get("/api/last_chat").get_json()["time"]
    logs = client.get("/api/log").get_json()
    assert logs[-1]["tool"] == "notify_guardian"
