# PICK 관리자 코드 방식

문제 해결:
- 첫 번째 가입자 자동 관리자 방식을 제거했습니다.
- 다른 컴퓨터에서 처음 가입해도 관리자가 되지 않습니다.
- 관리자 아이디와 관리자 코드가 모두 맞을 때만 관리자 권한이 생깁니다.

## Render 환경변수 설정

Render → Environment에 아래 추가:

```text
PICK_ADMIN_USERNAME=minseok
PICK_ADMIN_CODE=원하는_관리자_코드
PICK_SECRET_KEY=긴랜덤문자열
```

예:

```text
PICK_ADMIN_USERNAME=minseok
PICK_ADMIN_CODE=pick-owner-2026
```

## 관리자 가입 방법

회원가입 화면에서:

```text
아이디: minseok
비밀번호: 영어+숫자 8자 이상
관리자 코드: pick-owner-2026
```

이렇게 입력한 경우에만 관리자입니다.

## 일반 사용자

관리자 코드 입력칸을 비워두면 일반 유저입니다.

## 중요한 이유

Render 무료 서버에서 SQLite DB가 초기화되면 “첫 번째 가입자 관리자” 방식은 위험합니다.
이 버전은 관리자 코드를 요구하므로 다른 컴퓨터에서 가입해도 관리자가 되지 않습니다.
