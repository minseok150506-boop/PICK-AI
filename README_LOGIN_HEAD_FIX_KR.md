# PICK 로그인 HEAD 요청 500 오류 수정

수정 내용:
- `/login` 라우트에 HEAD 요청 허용
- HEAD 요청이 오면 빈 200 응답 반환
- `/` 루트도 HEAD 요청 안전 처리
- 500 오류 화면 추가

적용 방법:
1. ZIP 압축 풀기
2. 내부 파일 전체를 GitHub 루트에 업로드
3. Commit changes
4. Render → Manual Deploy → Deploy latest commit
5. 브라우저 캐시 새로고침
