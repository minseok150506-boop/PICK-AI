# PICK 관리자 지정 방법

이 버전은 자동 관리자를 만들지 않습니다.

## 기본 규칙

- 첫 번째 가입자도 자동 관리자가 아닙니다.
- 일반 사용자는 `/admin`에 접근할 수 없습니다.
- 관리자 계정은 서버 환경변수 `PICK_ADMIN_USERNAME`으로 지정합니다.

## Render에서 관리자 지정

Render → Environment Variables에 추가:

```text
PICK_ADMIN_USERNAME=minseok
```

그 다음 `minseok` 아이디로 회원가입하면 관리자 권한이 부여됩니다.

이미 회원가입을 먼저 했다면 DB에 이미 일반 유저로 들어갔을 수 있습니다.
그 경우 가장 쉬운 방법은 Render Disk/DB를 초기화하거나, 새 아이디를 `PICK_ADMIN_USERNAME`으로 지정한 뒤 다시 회원가입하는 것입니다.

## 로컬에서 관리자 지정

PowerShell에서 실행 전:

```powershell
set PICK_ADMIN_USERNAME=minseok
python app.py
```

그 다음 `minseok`으로 회원가입하면 관리자입니다.

## 보안 정책

- 관리자는 자기 자신의 관리자 권한을 해제할 수 없습니다.
- 관리자는 자기 자신을 삭제할 수 없습니다.
- 관리자 계정은 유저 삭제 기능으로 삭제되지 않습니다.
