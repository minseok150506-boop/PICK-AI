# PICK AI FANTASY

ULTIMATE를 확장한 버전입니다.

## 추가 기능
- 설치형 웹앱(PWA)
- 한국어 음성 입력
- 답변 음성 읽기
- NAS/DB/MiniPC Ollama/모델/디스크 진단
- 사용자 메시지 수정용 서버 API
- 최근 대화 기억 미리보기 API
- 실시간 스트리밍, 채팅 검색, 내보내기, 모델 선택 유지
- 인터넷 자동 검색, 뉴스, 날씨, YouTube, Wikipedia 검색 유지
- 이미지·동영상·PDF·문서 분석 유지
- MiniPC Watchdog 유지

## 구조
인터넷 → HTTPS → Synology NAS → PICK 웹/DB → 내부 LAN → MiniPC Ollama

Ollama 11434 포트를 인터넷에 직접 공개하지 마세요.

## 의도적으로 제외
- 이미지 생성
- 동영상 생성
- Render
- 원본 사용자 대화를 검증 없이 모델 가중치에 자동 재학습

자동 학습은 이후 '검토 가능한 지식 저장소 + 평가 + 승인된 학습 데이터' 구조로 만드는 편이 훨씬 안정적입니다.
