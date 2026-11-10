# hello.py
from dotenv import load_dotenv
load_dotenv()
import anthropic

client = anthropic.Anthropic()          # .env의 ANTHROPIC_API_KEY를 자동으로 읽음
response = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=400,
    system="너는 혼자 사는 어르신의 안부를 묻는 다정이야. 존댓말로 두세 문장만 말해.",
    messages=[{"role": "user", "content": "좋은 아침이야"}],
)
print(response.content[0].text)
print(response.usage)
