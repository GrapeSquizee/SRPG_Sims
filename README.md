# SRPG AI Sims

텍스트 기반 SRPG 스타일 AI 심즈 프로토타입입니다. 유저가 프롬프트를 입력하면 세계 안의 사물, 장소, 사람, 동물, 오감, 행동이 에이전트처럼 말하고, Multi-Agent Debate에 가까운 방식으로 다음 사건을 결정합니다.

## 현재 MVP

- 텍스트 CLI 게임 루프
- Agent화된 사물/장소/감각/행동의 토론
- ProAgent 스타일의 고정 Action Plan
- SRPG식 Status 창
- 힘, 민첩, 지능, 체력, 운 스탯
- 장비창, 도구, 기억 로그
- 반복 사건을 피하려는 novelty log
- 선택형 Ollama 연결

## 로컬 규칙 모드 실행

```powershell
python main.py
```

## Ollama AI 모드 실행

먼저 Ollama를 설치하고 서버를 켠 뒤, 작은 모델을 내려받습니다.

```powershell
ollama pull qwen2.5:3b
```

그 다음 AI 모드로 실행합니다.

```powershell
python main.py --ai --model qwen2.5:3b
```

다른 작은 모델을 쓰고 싶다면 예를 들어 다음처럼 바꿀 수 있습니다.

```powershell
python main.py --ai --model llama3.2:3b
```

Ollama 서버 주소를 바꾸려면:

```powershell
python main.py --ai --ollama-url http://localhost:11434 --model qwen2.5:3b
```

Ollama가 꺼져 있거나 모델 응답 JSON이 깨지면 게임은 자동으로 로컬 규칙 모드로 폴백합니다. 게임 안에서 `/ai`를 입력하면 현재 모델과 최근 폴백 이유를 볼 수 있습니다.

## 명령어

- `/status`: 현재 상태창 보기
- `/plan`: 현재 Action Plan 보기
- `/ai`: 현재 콘텐츠 모델 정보 보기
- `/help`: 도움말 보기
- `/quit`: 종료

## 다음 확장 아이디어

- 에이전트 정의를 JSON/YAML로 분리해서 콘텐츠만 바꿔도 세계가 달라지게 만들기
- 저장/불러오기
- 장소 그래프와 월드 시뮬레이션
- 에이전트별 장기 기억 및 관계도
- 전투/협상/잠입 같은 SRPG식 판정 모듈
- GUI 상태창과 맵 뷰
