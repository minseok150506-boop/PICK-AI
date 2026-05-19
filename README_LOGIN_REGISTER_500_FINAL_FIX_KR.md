# PICK 로그인/회원가입 500 최종 수정

로그에서 확인된 오류:
- NameError: too_many_login_attempts is not defined
- NameError: strong_password is not defined

수정 내용:
- 누락된 로그인 제한 함수 추가
- 누락된 비밀번호 검증 함수 추가
- login 라우트 재작성
- register 라우트 재작성
- HEAD 요청 안전 처리
- minseok / kms0506a! 관리자 기준 유지
- 일반 유저는 관리자 세션을 받지 않음

적용 방법:
1. ZIP 압축 풀기
2. 내부 파일 전체를 GitHub 루트에 업로드
3. Commit changes
4. Render → Manual Deploy → Deploy latest commit
5. /healthz 확인
6. /login에서 로그인
