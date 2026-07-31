# PICK AI 완성형 자동 실행 버전

## 포함된 기능

- 로그인 후 ChatGPT처럼 새 채팅 시작 화면 표시
- 관리자 계정 자동 생성
  - 아이디: `minseok`
  - 기본 비밀번호: `kms0506a!`
- 일반 사용자는 회원가입 후 로그인 가능
- 아이디만 중복 금지, 비밀번호 중복 허용
- 아이디 또는 비밀번호에 한글 입력 시 한국어 안내
- 새 채팅 생성 및 대화 저장
- 집 PC의 Ollama 연결
- Cloudflare Quick Tunnel 주소 자동 감지
- Render 환경변수 자동 갱신 및 Deploy Hook 호출
- Windows 로그인 시 Ollama와 Quick Tunnel 자동 실행

## 처음 한 번만 설정

1. ZIP 압축을 풉니다.
2. `INSTALL_ALL.bat`를 실행합니다.
3. 아래 값을 입력합니다.
   - Render API Key
   - Render Service ID
   - Render Deploy Hook URL
4. 설정이 끝나면 자동 실행 작업이 설치되고 서버가 바로 시작됩니다.

이미 `.pick_tunnel.env` 설정을 마쳤다면 아래 명령만 실행해도 됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\install_windows_startup.ps1
```

## 바로 실행

`START_NOW.bat`를 실행합니다.

## 자동 실행 해제

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_windows_startup.ps1
```

## 중요

- 집 PC가 켜져 있고 인터넷에 연결되어 있어야 외부에서 PICK AI가 Ollama를 사용할 수 있습니다.
- `.pick_tunnel.env`는 API Key와 토큰을 포함하므로 GitHub에 올리지 마세요.
- Render에서 `PICK_OLLAMA_HOST`와 `PICK_OLLAMA_TOKEN`이 환경 그룹이 아니라 서비스에 직접 설정되어 있어야 자동 갱신됩니다.
- 공개 운영 전에는 관리자 기본 비밀번호를 Render 환경변수 `PICK_ADMIN_PASSWORD`로 변경하는 것이 안전합니다.
