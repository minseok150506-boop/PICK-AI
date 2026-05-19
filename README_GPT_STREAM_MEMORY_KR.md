# PICK GPT 완전 연결 + 스트리밍 + 대화 기억 버전

## 추가 내용
- OpenAI GPT 연결
- 스트리밍 채팅 출력
- DB에 저장된 최근 대화를 GPT 문맥으로 사용
- 응답 속도 개선: 답변이 끝날 때까지 기다리지 않고 바로 출력
- 기존 사용자별 데이터 분리 유지
- 기존 관리자/보안 기능 유지

## Render 환경변수

필수:
```text
OPENAI_API_KEY=sk-...
```

선택:
```text
PICK_OPENAI_MODEL=gpt-4o-mini
```

## Render 배포
1. ZIP 압축 풀기
2. 내부 파일 전체를 GitHub 루트에 업로드
3. Commit changes
4. Render → Environment → OPENAI_API_KEY 추가
5. Render → Manual Deploy → Deploy latest commit

## 비용 주의
OpenAI API는 사용량 기반 과금입니다. Render 환경변수에 키를 넣기 전에 OpenAI 사용량 제한을 설정하는 것을 권장합니다.
