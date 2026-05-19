# PICK 대시보드 제거 + 답변 개선 버전

수정 내용:
- 관리자 사이드바의 대시보드 메뉴 제거
- 관리자 활동 로그 메뉴 제거 유지
- 관리자 메뉴 닫기는 로그아웃 옆에 유지
- 챗봇이 단순 질문에 계속 되묻는 문제 개선
- “해마 이모티콘” 질문에 직접 답변하도록 개선
- Ollama 연결 시에도 더 직접 답변하도록 프롬프트 개선

중요:
기본 local 모드는 진짜 GPT가 아닙니다.
정말 GPT 수준 답변을 원하면 Ollama 또는 OpenAI API 같은 LLM 연결이 필요합니다.

적용 방법:
1. ZIP 압축 풀기
2. 내부 파일 전체를 GitHub 루트에 업로드
3. Commit changes
4. Render → Manual Deploy → Deploy latest commit
