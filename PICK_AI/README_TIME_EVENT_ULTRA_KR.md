# PICK AI 시간/이벤트 ULTRA

이번 버전은 이벤트 날짜가 잘못 바뀌는 가능성을 더 줄였습니다.

## 시간 정확성

- Google / Cloudflare / pool.ntp.org / Windows Time NTP 사용
- 여러 서버 응답의 중앙값 사용
- 중앙값에서 크게 벗어난 NTP 응답 자동 제거
- NTP 합의가 2개 이상이면 `high` 신뢰도
- NTP 1개만 성공하면 `medium`
- 모두 실패하면 Synology 시스템 시계 fallback
- NTP로 보정된 UTC를 monotonic clock에 고정해 OS 시계가 갑자기 바뀌어도 이벤트 시간이 튀지 않음

## 서머타임

IANA timezone + Python zoneinfo를 사용하므로
미국/유럽 등 DST(서머타임) 전환을 자동 처리합니다.

## 국가 판정

브라우저 locale 하나만 믿지 않습니다.

예:
브라우저 언어가 한국어여도 실제 시간대가 `America/New_York`라면
미국 시간대를 우선합니다.

정확한 시간대 매핑이 있으면 시간대 기반 국가를 우선하고,
매핑할 수 없을 때만 locale 국가를 보조적으로 사용합니다.

## 이벤트 재검사

이벤트 모드는 서버가 알려준 시간에 자동 재검사합니다.
최대 5분 주기로 확인하고 날짜 전환 직후 새 테마가 적용됩니다.

사용자 PC의 현재 시각은 사용하지 않습니다.

## 진단 API

`/api/time/status?timezone=Asia/Seoul&country=KR`

다음 정보를 확인할 수 있습니다.

- NTP source
- offset_seconds
- confidence
- timezone
- country source
- locale/timezone mismatch
