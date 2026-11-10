"""AI 케어메이트의 두뇌: 지침, 응급 규칙, 도구, Claude 호출을 한곳에 모은 모듈"""
import json
from datetime import datetime
import anthropic

MODEL = "claude-haiku-5-5"          # 일상 대화용 모델 (8.7절 설계)
client = anthropic.Anthropic()      # API 키는 환경 변수 ANTHROPIC_API_KEY에서 읽음

# ① 지침: 매 요청에 똑같이 보내므로 프롬프트 캐싱의 대상이 됨
SYSTEM_PROMPT = """너는 혼자 사는 어르신의 안부를 묻는 AI 케어메이트 '다정이'야.

[말투]
- 존댓말로, 한 번에 두세 문장만 말해. 어려운 말과 영어는 쓰지 않아.
- 먼저 어르신의 말에 공감하고, 필요할 때만 한 가지를 물어봐.

[해도 되는 일]
- 안부 대화, 복약 확인, 병원 일정 안내
- 어르신이 약을 먹었다고 하면 record_medication 도구로 기록해
- 몸이 불편하다는 말이 나오면 보호자에게 알릴지 어르신께 먼저 여쭤 보고, 알려 달라고 하시면 notify_guardian 도구를 써
- 도구를 쓴 뒤에는 무엇을 했는지 한 문장으로 꼭 말씀드려

[하지 않는 일]  ← 요구사항 AI-01
- 병명을 짐작하거나 진단하지 않아
- 약의 종류나 양을 바꾸라고 말하지 않아
- 찜질, 파스, 일반 의약품 같은 가벼운 처치도 권하지 않아. 불편이 계속되면 의사 선생님께 여쭤 보시라고만 안내해
- 이런 질문에는 "그건 의사 선생님께 여쭤보시는 게 가장 정확해요"라고 안내해
"""

# ② 도구: 이름·입력 형식을 고정(strict)해 서버가 그대로 실행할 수 있게 함
TOOLS = [
    {
        "name": "record_medication",
        "description": "어르신이 약을 먹었다고 말했을 때 복약 기록을 남긴다.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "slot": {"type": "string", "enum": ["아침", "점심", "저녁"]},
                "taken": {"type": "boolean"},
            },
            "required": ["slot", "taken"],
            "additionalProperties": False,
        },
    },
    {
        "name": "notify_guardian",
        "description": "어르신이 동의했을 때 보호자에게 상황을 알린다.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["참고", "주의"]},
                "summary": {"type": "string", "description": "보호자에게 보낼 한 문장 요약"},
            },
            "required": ["level", "summary"],
            "additionalProperties": False,
        },
    },
]

# ③ 응급 규칙: 언어 모델보다 먼저, 정해진 단어로만 판단 (요구사항 FR-07)
EMERGENCY_WORDS = ["숨이 안", "숨쉬기", "쓰러", "가슴이 조여", "119", "살려"]

def is_emergency(text: str) -> bool:
    return any(w in text for w in EMERGENCY_WORDS)

# 실제 서비스에서는 데이터베이스와 알림 서비스가 이 일을 맡는다
LOG = []
LAST_USAGE = []   # 요청마다의 토큰 사용량(캐시 확인용)

def run_tool(name: str, args: dict) -> str:
    LOG.append({"time": datetime.now().strftime("%H:%M"), "tool": name, **args})
    if name == "record_medication":
        done = [l for l in LOG[:-1] if l["tool"] == name and l["slot"] == args["slot"]]
        if done:                                   # 같은 시간대는 한 번만 기록 (실행 중 발견한 버그 ①)
            LOG.pop()
            return f"{args['slot']} 복약은 이미 기록되어 있음"
        return f"{args['slot']} 복약 기록 완료"
    if name == "notify_guardian":
        return f"보호자에게 '{args['level']}' 알림 전송 완료"
    return "알 수 없는 도구"

def chat(history: list) -> str:
    """대화 기록을 받아 다정이의 답을 돌려준다. 도구 호출이 있으면 실행하고 이어서 묻는다."""
    last = history[-1]["content"]
    if is_emergency(last):
        run_tool("notify_guardian", {"level": "주의", "summary": f"긴급 표현 감지: {last}"})
        return "보호자분께 바로 알렸어요. 숨쉬기가 힘드시면 지금 119에 전화하시거나 아래 빨간 버튼을 눌러 주세요."

    messages = list(history)
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,                          # 생각(thinking) 토큰까지 포함한 한도 (버그 ③)
            output_config={"effort": "low"},          # 안부 대화는 낮은 노력 수준으로 충분
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            cache_control={"type": "ephemeral"},   # 지침·도구 정의를 캐시
            messages=messages,
        )
        LAST_USAGE.append(response.usage)
        if response.stop_reason != "tool_use":
            if response.stop_reason == "max_tokens":   # 한도에 닿아 잘린 답 (버그 ③)
                print("경고: max_tokens에 닿아 답이 잘렸습니다")
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            if not text:                               # 빈 답 대비 (실행 중 발견한 버그 ②)
                text = "제가 잘 알아듣지 못했어요. 한 번만 더 말씀해 주시겠어요?"
            return text

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": run_tool(block.name, block.input),
                })
        messages.append({"role": "user", "content": results})
