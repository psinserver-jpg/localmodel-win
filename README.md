# LMW — 로컬 모델을 끝까지 일하게 만드는 CLI

로컬 LLM이 요청을 잊거나 중간에 대충 끝내지 않도록,
**생각 → 계획 → 구현 → 검토·수정 반복 → 완성**을 프로그램이 강제합니다. 파인튜닝 필요 없음.

## 1. 설치 (한 줄)

**Windows** — 명령 프롬프트(cmd) 또는 PowerShell 어디서나
```bat
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/psinserver-jpg/localmodel-win/main/install.ps1 | iex"
```
**macOS / Linux**
```bash
curl -fsSL https://raw.githubusercontent.com/psinserver-jpg/localmodel-win/main/install.sh | sh
```

## 2. 실행

새 터미널에서 작업할 폴더로 이동한 뒤:
```
lmw
```
`lmw` 는 **[Ghostty](https://ghostty.org)** 창(LMW 전용 테마)에서 열립니다. Ghostty 가 없으면 Windows 에서는 같은 테마의 Windows Terminal 창으로 열립니다. 지금 창에서 쓰려면 `lmw --here`.

1. **로그인** — [psin.ai.kr](https://psin.ai.kr) 링크가 열리면 **Google 로그인** → **[로그인 승인하기]**
2. **모델 설정** — 실행 중인 서버(Ollama, LM Studio, vLLM 등)를 자동으로 찾아 줍니다 → 모델 선택
3. **요청 입력** — 끝!

```
> /plan 카페 홈페이지 만들어줘. 메뉴, 위치, 예약 버튼 포함

◆ 3/8 계획 — 1차
  ⎿  계획: 구현 3단계
     · 페이지 뼈대와 메뉴  (index.html)
     · 스타일  (style.css)
     · 예약 폼 동작  (app.js)

◆ 5/8 구현 — 단계 1/3: 페이지 뼈대와 메뉴
● Write(index.html)
  ⎿  저장됨
```

## 3. 쓰는 법

그냥 말하듯 입력하면 됩니다. lmw 가 알아서 파일을 **찾고(Grep·Glob) → 읽고(Read) → 고치고(Edit·Write) → 실행해서 확인(Bash)** 하고, 필요하면 **웹 검색(WebSearch)·페이지 읽기(WebFetch)** 도 합니다.

```
> calc.py 의 add 버그 고쳐줘

✻ 생각함 (1.2초)

● Read(calc.py)
  ⎿  4줄 읽음

● Edit(calc.py)
  ⎿  +1 −1
          2 -     return a-b
          2 +     return a+b

● Bash(python calc.py)
  ⎿  exit 0

● 고쳤습니다. add 가 이제 더하기를 합니다.
```

Claude Code 처럼 입력 박스(`/` 입력 시 명령 자동완성), **작업 중에 입력하면 그 내용이 작업에 바로 추가**(순서대로 처리), **Shift+Tab** 으로 권한 모드 전환, 파일 수정 전 **변경 미리보기 + 방향키 선택 메뉴**(예 · 다시 묻지 않기 · 아니요)가 나옵니다.

| 상황 | 동작 |
|---|---|
| "안녕" 같은 짧은 말 | 생각 없이 바로 답변 |
| 질문·간단한 요청 | 생각 없이 바로 답변 (필요하면 파일 읽기) |
| 코드 작성·수정·버그 수정 | 생각하고 진행 |
| `/plan 요청` (또는 `/plan` 입력 후 요청) | **계획 모드**: 분석 → 계획 → 구현 → 검토·수정 반복을 자동으로 끝까지 |

| 명령 | 설명 |
|---|---|
| `/mode` | 권한: **매번 묻기** · **편집 자동 수락** · **전체 허용** (위험한 명령은 항상 물어봄) |
| `/effort` | 생각 수준: 자동 · 빠르게 · 보통 · 깊게 |
| `/new` | 새 세션 |
| `/compact` | 대화 요약해 컨텍스트 비우기 (가득 차기 전에 **자동으로** 함) |
| `/continue` · `/sessions` | 지난 세션 이어서 하기 (대화 내용은 세션이 닫혀도 저장됨) |
| `/undo` · `/model` | 되돌리기 · 모델 바꾸기 |
| `/update` | 최신 버전으로 업데이트 후 자동 재시작 (밖에서는 `lmw update`) |
| `/` · `Shift+Tab` · `Alt+Enter` | 명령 자동완성 · 권한 모드 전환 · 줄바꿈 |

`lmw` 가 켜져 있으면 [psin.ai.kr](https://psin.ai.kr) 에서 **＋ 새 세션** 을 눌러 같은 lmw 안에 세션을 더 열 수 있습니다 (터미널 세션은 그대로).
[psin.ai.kr](https://psin.ai.kr) 에 같은 Google 계정으로 로그인하면 세션별 대화, 생각/작업 펼쳐보기, 권한 승인, 프롬프트 보내기를 폰에서도 할 수 있습니다.

## 준비물

- 로컬 모델 서버 하나: [Ollama](https://ollama.com) (추천), LM Studio, vLLM, llama.cpp, SGLang, LocalAI, KoboldCpp, Jan, GPT4All 등 17종 — 목록은 `lmw servers`
- 모델은 무엇이든 됩니다. 처음이라면 `ollama pull qwen2.5-coder:14b`

---

<details>
<summary>고급 기능</summary>

- `lmw run "요청" -w 폴더` — 대화 없이 8단계로 한 번에 실행 · `--check "pytest -q"` 테스트 통과까지 강제
- 웹 검색: 기본은 DuckDuckGo·Bing (키 필요 없음). 설정에 `"search_url": "http://localhost:8080"`(SearXNG) 또는 환경변수 `BRAVE_API_KEY` 를 넣으면 그쪽을 먼저 사용
- 검색은 [ripgrep](https://github.com/BurntSushi/ripgrep) 이 있으면 자동 사용 · `/engine aider` 로 [Aider](https://github.com/Aider-AI/aider) 엔진 사용 가능 (`pip install aider-chat`)
- `lmw export` — 채팅 앱(Open WebUI 등)용 시스템 프롬프트 · `lmw commands` — `/lmw` 슬래시 명령 파일
- `lmw ssh user@서버` — 다른 컴퓨터에서 실행 · `lmw tunnel user@서버` — 다른 PC의 GPU 모델 사용
- `skills/` — 웹 디자인·코딩·디버깅 스킬 (SKILL.md 형식, 직접 추가 가능) · `prompts/` — 단계별 프롬프트
</details>

MIT License
