# PICK 완전 서비스 배포 가이드

## 0. 현재 파일의 의미

이 ZIP은 서비스 배포용 구조입니다.

포함:
- 회원가입 / 로그인 / DB
- SQLite 저장
- Windows 서버 실행용 Waitress
- Render 배포용 설정
- Docker 배포용 설정
- HTTPS / 도메인 연결 가이드

---

# 1. 로컬에서 사이트처럼 실행

## 1-1. 패키지 설치

```powershell
scripts\INSTALL_REQUIREMENTS.bat
```

또는:

```powershell
pip install -r requirements.txt
```

## 1-2. 개발 실행

```powershell
scripts\START_DEV.bat
```

접속:

```text
http://127.0.0.1:5000
```

## 1-3. Windows 서비스형 실행

Gunicorn은 Windows에서 안 됩니다. Windows에서는 Waitress를 쓰세요.

```powershell
scripts\START_WINDOWS_SERVICE.bat
```

접속:

```text
http://127.0.0.1:5000
```

같은 Wi-Fi 안의 다른 기기에서 접속하려면:

```text
http://내PC_IP주소:5000
```

---

# 2. 진짜 인터넷 서비스로 배포하는 가장 쉬운 방법: Render

## 2-1. GitHub에 업로드

1. GitHub 가입
2. 새 저장소 생성
3. 이 폴더 전체 업로드

## 2-2. Render에서 배포

1. Render 접속
2. New → Web Service
3. GitHub 저장소 연결
4. 설정:

```text
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app
```

## 2-3. 환경변수 설정

Render Environment에 추가:

```text
PICK_SECRET_KEY=긴랜덤문자열
PICK_LLM_MODE=local
```

예:

```text
PICK_SECRET_KEY=pick-2026-super-secret-please-change-this
```

## 2-4. 배포 후 접속

Render가 이런 주소를 줍니다:

```text
https://pick-ai-service.onrender.com
```

Render는 HTTPS가 자동 적용됩니다.

---

# 3. 도메인 연결

예: `pick-ai.com`을 연결한다고 가정합니다.

## 3-1. 도메인 구매

가능한 곳:
- 가비아
- 카페24
- Cloudflare Registrar
- Namecheap

## 3-2. Render에서 Custom Domain 추가

Render 서비스 설정에서:

```text
Settings → Custom Domains → Add Custom Domain
```

예:

```text
www.pick-ai.com
```

## 3-3. 도메인 DNS 설정

도메인 DNS에서 Render가 안내하는 값대로 설정합니다.

보통:

```text
CNAME
이름: www
값: Render에서 준 주소
```

루트 도메인도 쓰려면:

```text
A 또는 ALIAS
이름: @
값: Render 안내값
```

## 3-4. HTTPS

Render는 도메인 연결 후 HTTPS 인증서를 자동 발급합니다.

---

# 4. VPS에서 운영하는 방법

Ubuntu VPS 기준입니다.

## 4-1. 서버 준비

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
```

## 4-2. 프로젝트 업로드 후 설치

```bash
cd PICK_SERVICE
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4-3. Gunicorn 실행 테스트

```bash
export PICK_SECRET_KEY="긴랜덤문자열"
export PICK_LLM_MODE=local
gunicorn app:app -b 0.0.0.0:5000
```

## 4-4. Nginx 연결

```nginx
server {
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 4-5. HTTPS 적용

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

---

# 5. Ollama / 최강 LLM 사용 주의

Render 무료 서버에서는 Ollama 같은 큰 모델 실행이 어렵습니다.

강한 LLM을 쓰려면:

## 방법 A
로컬 PC에서만 사용:

```powershell
ollama pull qwen2.5:14b
set PICK_LLM_MODE=auto
set PICK_OLLAMA_MODEL=qwen2.5:14b
scripts\START_WINDOWS_SERVICE.bat
```

## 방법 B
GPU VPS 사용

GPU 서버에 Ollama 설치 후:

```bash
ollama pull qwen2.5:32b
ollama serve
```

PICK 서버 환경변수:

```text
PICK_LLM_MODE=ollama
PICK_OLLAMA_HOST=http://GPU서버IP:11434
PICK_OLLAMA_MODEL=qwen2.5:32b
```

보안상 Ollama 포트를 외부에 그대로 열면 위험합니다. 방화벽 또는 프록시 인증을 붙이세요.

---

# 6. 운영 체크리스트

서비스 공개 전 확인:

- [ ] 회원가입 가능
- [ ] 로그인 가능
- [ ] 로그아웃 가능
- [ ] 한글 아이디/비밀번호 차단
- [ ] 관리자 상태 페이지 접속 가능
- [ ] DB 파일 생성 확인: `data/pick_service.db`
- [ ] Render 환경변수 설정
- [ ] HTTPS 확인
- [ ] 도메인 연결 확인
- [ ] SECRET_KEY 변경
- [ ] 테스트 계정으로 채팅 확인

---

# 7. 가장 추천하는 운영 방식

## 초보/빠른 공개

```text
Render + SQLite + local 모드
```

장점:
- HTTPS 자동
- 배포 쉬움
- 도메인 연결 쉬움

단점:
- 큰 LLM 실행 어려움

## 제대로 된 AI 서비스

```text
VPS 또는 GPU 서버 + Nginx + HTTPS + Ollama
```

장점:
- 진짜 AI 성능 가능
- 자유로운 운영

단점:
- 서버 관리 필요
- 비용 발생
