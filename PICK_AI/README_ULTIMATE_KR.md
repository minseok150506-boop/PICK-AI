# PICK AI Synology + MiniPC ULTIMATE

이번 버전에서 추가된 핵심 기능:

- ChatGPT처럼 Ollama 답변 실시간 스트리밍
- 채팅 내용 검색
- 채팅 Markdown 내보내기
- Ollama 모델 선택 / 자동 선택
- 인터넷 검색 자동/항상/끄기 설정
- 사용자별 설정 DB 저장
- 채팅 안에서 이미지·동영상·PDF/문서 바로 첨부 및 분석
- 이미지/동영상 생성 기능은 없음
- 인터넷 검색 결과에 출처 URL 전달
- DuckDuckGo + Wikipedia 혼합 웹 검색
- Google News RSS
- Open-Meteo 전 세계 날씨
- YouTube 검색
- 관리자 DB 즉시 백업 API
- 미니PC Ollama Watchdog
- Windows 부팅 시 Watchdog 자동 시작 등록
- 연결 검사 PowerShell

## 가장 권장하는 미니PC 모델 구성

- RAM 32GB
- `qwen3:8b` : 기본 대화
- `qwen3:4b` : 장애 시 fallback
- `llava:latest` : 이미지 및 동영상 프레임 분석

설치:

```powershell
ollama pull qwen3:8b
ollama pull qwen3:4b
ollama pull llava
```

## 미니PC 24시간 자동 운영

관리자 PowerShell에서:

```powershell
powershell -ExecutionPolicy Bypass -File .\INSTALL_MINIPC_AUTOSTART.ps1
```

이후 Windows가 켜지면 Ollama Watchdog가 자동으로 실행됩니다.

## 중요

미니PC의 TCP 11434를 인터넷에 포트포워딩하지 마세요.
Synology NAS만 집 내부 LAN에서 미니PC Ollama에 연결하게 하는 구조가 안전합니다.
