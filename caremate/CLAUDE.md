# 다정이(AI 케어메이트) 프로젝트

- 혼자 사는 어르신의 안부를 묻는 챗봇. Python 3 + Flask + Claude API(anthropic SDK)
- caremate.py: 지침·응급 규칙·도구·Claude 호출 / app.py: 웹 서버 / templates/: 화면
- 화면 원칙: 어르신 화면 글자 20px 이상, AI가 만든 문장에는 'AI가 만든' 표시
- 응급(SOS) 경로는 Claude를 거치지 않는다. 이 원칙을 바꾸는 수정은 하지 않는다
- 테스트는 tests/ 아래에 두고 `python -m pytest -q`로 실행한다. 실제 API를 부르지 않도록 caremate.client를 가짜로 바꿔 시험한다
