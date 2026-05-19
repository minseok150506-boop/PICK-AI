# PICK 채팅 안정화 + OpenAI 전용 버전

수정 내용:
- Ollama 안내 제거, OpenAI GPT 중심으로 정리
- 말풍선 크기 축소
- 채팅 이름이 매 질문마다 바뀌지 않게 수정
- 두 번째 질문부터 답변이 멈추는 문제 방지
- 로그인 문구 '저장된 자동완성 값은 사용하지 않습니다.' 제거

Render 환경변수:
OPENAI_API_KEY=sk-...
PICK_OPENAI_MODEL=gpt-4o-mini

적용:
1. ZIP 압축 풀기
2. 내부 파일 전체를 GitHub 루트에 업로드
3. Commit changes
4. Render → Manual Deploy → Deploy latest commit
