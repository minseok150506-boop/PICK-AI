# PICK AI PERFECT

## 이번 버전 핵심
- 사용자가 직접 추가/삭제하는 장기 기억
- SQLite FTS5 기억 검색 + 호환 fallback
- 현재 질문과 관련된 기억만 Ollama에 전달
- 설치된 모델 기반 자동 모델 라우팅
- 계정 전체 데이터 JSON 내보내기
- 일반 사용자 계정 삭제 API
- 관리자 감사 로그 API
- DB 백업 복원 도구
- DB 무결성/외래키 유지보수 검사
- 기존 스트리밍/PWA/음성/웹검색/날씨/뉴스/YouTube/이미지·영상·문서 분석 유지

## 중요한 원칙
사용자 대화를 검증 없이 모델에 자동 재학습하지 않습니다.
대신 사용자가 승인한 장기 기억을 별도 저장하므로 어떤 내용을 기억하는지 확인하고 삭제할 수 있습니다.

## 운영
매일 백업: `BACKUP_DATABASE.sh`
정기 점검: `RUN_MAINTENANCE.sh`
복원: `python restore_db.py data/backups/백업.db --force`

## 보안
- 외부에는 Synology HTTPS만 공개
- MiniPC Ollama 11434 포트포워딩 금지
- SECRET_KEY 변경
- HTTPS 적용 후 PICK_COOKIE_SECURE=1
- 관리자 비밀번호는 `.env`에서 변경 권장
