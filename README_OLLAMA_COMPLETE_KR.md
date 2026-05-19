# PICK Ollama 완성 버전

지원:
- Ollama 무료 로컬 AI
- OpenAI API 선택 가능
- Gemma 3 12B 기본값
- 스트리밍
- 대화 기억
- 빈 말풍선 방지
- 자연스러운 오류 메시지

Render 환경변수:
PICK_AI_PROVIDER=ollama
PICK_OLLAMA_MODEL=gemma3:12b
PICK_OLLAMA_HOST=https://외부에서_접속가능한_주소

중요:
Render는 사용자 PC의 localhost:11434에 직접 접속할 수 없습니다.
Cloudflare Tunnel 또는 ngrok으로 Ollama를 외부 주소로 열고 그 주소를 PICK_OLLAMA_HOST에 넣어야 합니다.

PC에서 모델 설치:
ollama run gemma3:12b

관리자 확인:
https://pick-ai.onrender.com/admin/ai-test
