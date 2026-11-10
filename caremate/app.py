"""AI 케어메이트 웹 서버: 화면을 보여 주고, /chat으로 들어온 말을 다정이에게 전한다"""
from dotenv import load_dotenv
load_dotenv()                                   # .env 파일의 API 키를 읽음

from datetime import datetime
from flask import Flask, jsonify, render_template, request
import caremate

app = Flask(__name__)
LAST_CHAT = {"time": None}                       # 마지막 대화 시각(보호자 화면용)

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/chat")
def chat():
    history = request.get_json()["history"]      # [{"role": "user", "content": "..."}, ...]
    LAST_CHAT["time"] = datetime.now().strftime("%H:%M")
    before = len(caremate.LOG)
    reply = caremate.chat(history[-20:])         # 최근 20개 발화만 보냄 (8.7절 비용 원칙)
    return jsonify({"reply": reply, "log": caremate.LOG[before:]})   # 이번에 새로 생긴 기록만

@app.get("/guardian")
def guardian():
    return render_template("guardian.html")

@app.get("/api/log")
def api_log():
    return jsonify(caremate.LOG)

@app.get("/api/last_chat")
def api_last_chat():
    return jsonify(LAST_CHAT)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
