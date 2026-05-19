# PICK DB 백업/복구 + LLM 업그레이드 버전

추가 기능:
- DB 백업 다운로드: /admin/backup
- DB 복구: /admin/backup
- LLM 설정 확인: /admin/llm
- Ollama 연결 지원: PICK_LLM_MODE=ollama
- 기존 기능 유지: 메시지 수정/삭제, 관리자 전체 삭제, 사용자별 데이터 분리

Ollama 환경변수:
PICK_LLM_MODE=ollama
PICK_OLLAMA_MODEL=qwen2.5:14b
PICK_OLLAMA_HOST=http://서버주소:11434

적용:
1. ZIP 압축 풀기
2. 내부 파일 전체를 GitHub 루트에 업로드
3. Commit changes
4. Render → Manual Deploy → Deploy latest commit
