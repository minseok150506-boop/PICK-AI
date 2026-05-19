# PICK Render PostgreSQL 영구 저장 버전

이 버전은 Render PostgreSQL을 연결하면 데이터가 영구 저장됩니다.

저장되는 데이터:
- 회원가입 계정
- 로그인 정보
- 채팅방
- 메시지
- 유저 차단
- IP 차단
- 로그인 시도 로그

## Render에서 PostgreSQL 만드는 방법

1. Render Dashboard
2. New +
3. PostgreSQL 선택
4. 이름 예: pick-db
5. Free Plan 선택 가능
6. 생성

## Web Service에 DB 연결

1. Render에서 PICK Web Service 열기
2. Environment 탭
3. Add Environment Variable
4. Key:
```text
DATABASE_URL
```
5. Value:
PostgreSQL 페이지의 External Database URL 또는 Internal Database URL을 복사해서 넣기

보통 같은 Render 안에서는 Internal Database URL을 권장합니다.

## 기존 환경변수

```text
PICK_SECRET_KEY=긴랜덤문자열
PICK_COOKIE_SECURE=1
```

## 배포

GitHub에 파일 업로드 후:

```text
Manual Deploy → Deploy latest commit
```

## 주의

DATABASE_URL이 없으면 로컬 테스트용 SQLite `data/pick.db`를 사용합니다.
Render에서 데이터를 영구 저장하려면 반드시 DATABASE_URL을 설정해야 합니다.
