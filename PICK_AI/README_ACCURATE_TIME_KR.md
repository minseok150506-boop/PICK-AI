# PICK AI 시간 오차 방지

이 버전은 이벤트 날짜 판정에 브라우저/PC의 현재 시각을 사용하지 않습니다.

## 시간 판정 구조

1. Synology PICK 서버가 NTP 서버에서 UTC 시각 차이를 확인합니다.
2. 여러 NTP 응답이 있으면 중앙값(offset median)을 사용합니다.
3. 사용자의 브라우저에서는 `Asia/Seoul`, `America/New_York` 같은 IANA 시간대 이름만 받습니다.
4. NTP 기준 UTC → 해당 국가/사용자의 시간대로 변환합니다.
5. 그 현지 날짜를 기준으로 이벤트를 켭니다.

따라서 사용자의 Windows 시간이 몇 분 또는 몇 시간 틀려도 이벤트 시작 시각에는 영향을 주지 않습니다.

## 기본 NTP 서버

- time.google.com
- time.cloudflare.com
- pool.ntp.org

10분마다 다시 확인합니다.

## NTP 접속 실패

UDP 123이 차단된 네트워크에서는 Synology 시스템 UTC 시계를 사용합니다.

이 경우 DSM에서도 NTP 동기화를 켜두는 것을 강력히 권장합니다.

DSM:
제어판 → 지역 옵션 → 시간 → NTP 서버와 동기화

## 이벤트 예시

광복절:
- 대한민국 전용
- 반드시 `Asia/Seoul`에서 8월 15일이 되었을 때 적용

크리스마스:
- 국제 이벤트
- 서울 사용자는 서울의 12월 25일
- 뉴욕 사용자는 뉴욕의 12월 25일
- 런던 사용자는 런던의 12월 25일

## 진단

로그인 후 다음 API가 있습니다.

`/api/time/status`

반환값에서:
- `source: ntp` → NTP 기준
- `accurate: true` → NTP 응답을 사용 중
- `offset_seconds` → 서버 시계와 NTP의 차이

설정의 시스템 진단에서도 `시간 NTP 동기화` 여부를 확인할 수 있습니다.
