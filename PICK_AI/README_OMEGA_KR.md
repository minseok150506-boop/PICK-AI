# PICK AI OMEGA

PERFECT에서 실제 운영 안정성을 더 강화한 버전입니다.

## 새로 추가
- MiniPC 과부하 방지 AI 동시 요청 제한
- AI 대기열
- 연속 오류 Circuit Breaker
- 자동 복구 대기
- 상단 AI 준비/응답중/대기/복구중 상태
- 인터넷 검색 자료 Prompt Injection 방어
- 외부 자료를 정보로만 취급
- 14일 세션 유지
- 관리자 사용자/채팅/메시지/기억/첨부파일 현황
- DB 마이그레이션 버전 관리
- Synology 자동 백업/점검 스케줄 안내

## 기본값
PICK_MAX_CONCURRENT_AI=1
PICK_AI_QUEUE_WAIT_SECONDS=90
PICK_AI_FAILURE_THRESHOLD=4
PICK_AI_COOLDOWN_SECONDS=45

Ryzen 7 5800H + RAM 32GB처럼 MiniPC에서 qwen3:8b를 돌릴 때는 동시 추론 1개부터 시작하는 편이 안정적입니다.

## 보안
- MiniPC Ollama 11434 인터넷 포트포워딩 금지
- 외부에는 Synology HTTPS Reverse Proxy만 공개
- SECRET_KEY 변경
- HTTPS 설정 후 PICK_COOKIE_SECURE=1
