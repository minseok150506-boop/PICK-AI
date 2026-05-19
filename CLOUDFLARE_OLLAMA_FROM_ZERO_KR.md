# Cloudflare + Ollama 처음부터 다시 하기

## 목표
PICK(Render) → Cloudflare Tunnel → 내 PC Ollama → Gemma/Qwen 모델

## 1. Ollama 설치
https://ollama.com/download

설치 후 CMD에서:
```bat
ollama run gemma3:12b
```

또는 한국어 대화 추천:
```bat
ollama run qwen3:8b
```

## 2. cloudflared 설치
공식 다운로드:
https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/

Windows용 cloudflared.exe를 설치하거나 PATH에 등록합니다.

## 3. 자동 실행 스크립트 사용
`local_ai_windows` 폴더에서 순서대로 실행합니다.

1. `01_INSTALL_AND_PULL_MODEL.bat`
2. `02_START_OLLAMA_SERVER.bat`
3. 새 CMD에서 `03_START_CLOUDFLARE_TUNNEL.bat`

## 4. trycloudflare 주소 복사
`03_START_CLOUDFLARE_TUNNEL.bat` 실행 후 이런 주소가 나옵니다.

```text
https://xxxxx.trycloudflare.com
```

이 주소 전체를 복사합니다.

## 5. Render Environment 설정
Render → PICK-AI → Environment:

```text
PICK_AI_PROVIDER=ollama
PICK_OLLAMA_MODEL=gemma3:12b
PICK_OLLAMA_HOST=https://xxxxx.trycloudflare.com
```

Qwen을 쓰려면:

```text
PICK_OLLAMA_MODEL=qwen3:8b
```

자동 후보 전환을 원하면:

```text
PICK_OLLAMA_MODEL=auto
```

## 6. Render 재배포
Manual Deploy → Deploy latest commit

## 7. 테스트
관리자로 로그인 후:

```text
/admin/ai-test
```

## 중요
무료 quick tunnel 주소는 바뀔 수 있습니다.
주소가 바뀌면 Render의 PICK_OLLAMA_HOST도 바꿔야 합니다.

Cloudflare 창과 Ollama 창은 꺼지면 안 됩니다.
