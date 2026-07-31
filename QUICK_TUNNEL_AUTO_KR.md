# Cloudflare Quick Tunnel 주소 자동 갱신

이 기능은 집 PC에서 `cloudflared`가 새 `trycloudflare.com` 주소를 만들 때마다 다음 작업을 자동으로 수행합니다.

1. Ollama 앞에 토큰 인증 게이트웨이 실행
2. Quick Tunnel 주소 감지
3. Render의 `PICK_OLLAMA_HOST`와 `PICK_OLLAMA_TOKEN` 갱신
4. Render 재배포 요청
5. cloudflared가 꺼지면 10초 뒤 자동 재시작

## 최초 1회 설정

### 1. Render API Key 만들기
Render Dashboard → Account Settings → API Keys에서 생성합니다.

### 2. Render Service ID 확인
PICK AI 서비스의 Settings 또는 주소에서 `srv-...` 값을 확인합니다.

### 3. Deploy Hook 만들기/복사
PICK AI 서비스 → Settings → Deploy Hook에서 URL을 복사합니다.

### 4. 설정 스크립트 실행
프로젝트 폴더에서 PowerShell을 열고 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_quick_tunnel.ps1
```

API Key, Service ID, Deploy Hook을 입력하면 `.pick_tunnel.env`가 만들어집니다.
이 파일은 비밀정보이므로 GitHub에 올리면 안 됩니다.

## 매번 실행

`start_quick_tunnel.bat`을 더블클릭합니다.

정상적으로 동작하면 다음 메시지가 표시됩니다.

```text
[감지] 새 Quick Tunnel 주소: https://...trycloudflare.com
[완료] Render 환경변수 갱신 및 재배포 요청 완료
```

Render 재배포가 끝난 뒤 전 세계에서 PICK AI 주소로 접속할 수 있습니다.

## 중요한 제한

- 집 PC와 Ollama가 켜져 있어야 AI 답변이 작동합니다.
- Quick Tunnel은 Cloudflare가 테스트·개발 용도로 제공하는 방식이므로 상용 서비스 수준의 안정성은 보장되지 않습니다.
- Render 무료 서비스는 잠들거나 재배포에 시간이 걸릴 수 있습니다.
- `.pick_tunnel.env`와 Render API Key를 절대 공개하지 마세요.
