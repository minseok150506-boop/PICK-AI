# PICK 500 에러 핫픽스

수정 내용:
- 메인 페이지 `/` 접속 시 발생할 수 있는 500 에러 수정
- 누락된 `is_user_blocked()` 함수 추가
- 차단된 유저가 관리자 페이지에 접근하지 못하도록 보강
- 대시보드 메뉴 숨김 유지
- GPT 스트리밍/대화 기억 기능 유지

적용:
1. ZIP 압축 풀기
2. 내부 파일 전체를 GitHub 루트에 업로드
3. Commit changes
4. Render → Manual Deploy → Deploy latest commit
