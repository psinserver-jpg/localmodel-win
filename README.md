# LMW — 로컬 모델을 끝까지 일하게 만드는 CLI

로컬 LLM이 요청을 잊거나 중간에 대충 끝내지 않도록,
**생각 → 계획 → 구현 → 검토·수정 반복 → 완성**을 프로그램이 강제합니다. 파인튜닝 필요 없음.

## 1. 설치 (한 줄)

**Windows** (PowerShell)
```powershell
irm https://raw.githubusercontent.com/psinserver-jpg/localmodel-win/main/install.ps1 | iex
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
1. **로그인** — [psin.ai.kr](https://psin.ai.kr) 링크가 열리면 **Google 로그인** → **[로그인 승인하기]**
2. **모델 설정** — 실행 중인 서버(Ollama, LM Studio, vLLM 등)를 자동으로 찾아 줍니다 → 모델 선택
3. **요청 입력** — 끝!

```
lmw ❯ 카페 홈페이지 만들어줘. 메뉴, 위치, 예약 버튼 포함
 ✔생각 ✔이해검토 ✔계획 ✔계획검토 ▶구현 ·결과검토 ·수정 ·보고
```

## 3. 쓰는 법

| 하고 싶은 것 | 방법 |
|---|---|
| 만들기 / 고치기 | 그냥 입력 |
| 질문 | 끝에 `?` |
| 메뉴 | `Enter` |
| 전체 명령 | `/` (Tab 자동완성) |
| 되돌리기 | `/undo` |
| 모델 바꾸기 | `/model` |
| 밖에서 보기 | [psin.ai.kr](https://psin.ai.kr)에 같은 Google 계정으로 로그인, 또는 다른 PC에서 `lmw watch` |

파일을 바꾸기 전에 항상 물어봅니다 (`y` 승인 · `n` 거절 · `d` 변경 보기 · `a` 모두 승인).

## 준비물

- 로컬 모델 서버 하나: [Ollama](https://ollama.com) (추천), LM Studio, vLLM, llama.cpp, SGLang, LocalAI, KoboldCpp, Jan, GPT4All 등 17종 — 목록은 `lmw servers`
- 모델은 무엇이든 됩니다. 처음이라면 `ollama pull qwen2.5-coder:14b`

---

<details>
<summary>고급 기능</summary>

- `lmw run "요청" -w 폴더` — 대화 없이 한 번에 실행 · `--check "pytest -q"` 테스트 통과까지 강제
- `lmw export` — 채팅 앱(Open WebUI 등)용 시스템 프롬프트 · `lmw commands` — `/lmw` 슬래시 명령 파일
- `lmw ssh user@서버` — 다른 컴퓨터에서 실행 · `lmw tunnel user@서버` — 다른 PC의 GPU 모델 사용
- `skills/` — 웹 디자인·코딩·디버깅 스킬 (SKILL.md 형식, 직접 추가 가능) · `prompts/` — 단계별 프롬프트
</details>

MIT License
