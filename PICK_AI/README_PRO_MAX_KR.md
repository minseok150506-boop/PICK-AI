# PICK AI Synology + MiniPC PRO MAX

이 버전은 Synology를 공개 웹/DB/파일 서버로, 미니PC를 Ollama 연산 서버로 사용합니다.

## PRO MAX에서 추가된 부분

- 질문이 최신 정보인지 자동 판단
- 최신/가격/뉴스/날씨/YouTube 질문은 인터넷 자동 조회
- Open-Meteo 기반 전 세계 날씨 (키 불필요)
- Google News RSS 기반 뉴스 검색
- DuckDuckGo 공개 웹 검색
- YouTube 관련 검색
- 인터넷 검색 결과를 Ollama에 근거 자료로 전달
- 최신 검색에 실패하면 아는 척하지 않도록 프롬프트 보강
- CSRF 보호
- 로그인 요청 제한
- 채팅 요청 제한
- 보안 HTTP 헤더
- Synology Reverse Proxy 환경 지원
- SQLite 온라인 백업
- 최근 14개 DB 백업 자동 보관
- Ollama 다중 fallback 모델 유지
- 이미지/동영상/PDF 분석 유지
- 이미지/동영상 생성은 없음
- Render 없음

## 데이터베이스 백업

Synology Task Scheduler에서 매일 실행하도록 다음 파일을 등록할 수 있습니다.

`BACKUP_DATABASE.sh`

백업은 `data/backups/`에 생성되고 최신 14개를 유지합니다.

## 인터넷 검색 주의

외부 검색 사이트의 HTML/RSS 형식이 변경되면 일부 검색이 실패할 수 있습니다.
검색이 실패해도 Ollama 일반 대화는 계속 동작하도록 설계했습니다.

## 공개 서비스 보안

1. 외부에는 Synology HTTPS만 공개
2. 미니PC Ollama 11434 포트는 포트포워딩 금지
3. `SECRET_KEY` 변경
4. 실제 공개 후 `PICK_COOKIE_SECURE=1`
5. 관리자 비밀번호는 가능하면 `.env`에서 변경
