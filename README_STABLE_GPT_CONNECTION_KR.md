# PICK 완전 안정 GPT 연결 버전

변경 내용:
- OpenAI GPT 연결 로직 재작성
- 스트리밍 중 오류가 나도 채팅 UI가 멈추지 않게 수정
- GPT 호출 실패 원인을 Render Logs에 `[PICK GPT ERROR]`로 출력
- 관리자 페이지 `/admin/gpt-test` 추가
- static JS/CSS 캐시 방지 버전 파라미터 추가
- 말풍선 크기 축소 유지
- 채팅 이름은 첫 메시지에서만 정해짐

필수 Render 환경변수:
OPENAI_API_KEY=sk-실제키
PICK_OPENAI_MODEL=gpt-4o-mini

확인 방법:
1. 배포 후 minseok / kms0506a! 로그인
2. /admin/gpt-test 접속
3. OPENAI_API_KEY = 인식됨 확인
4. 테스트 결과가 성공인지 확인
