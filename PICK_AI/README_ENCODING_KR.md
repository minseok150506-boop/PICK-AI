# PICK AI 한글/디코딩 수정

파일 인코딩을 다음처럼 통일했습니다.

- Python / HTML / CSS / JavaScript / JSON / YAML / Markdown: UTF-8
- PowerShell (.ps1): UTF-8 BOM
- Windows 배치 파일 (.bat): CP949 + chcp 949
- HTML: <meta charset="UTF-8">
- Flask JSON: JSON_AS_ASCII=False
- Flask text/json 응답: charset=utf-8
- JavaScript 스트리밍: TextDecoder("utf-8")

Windows에서 실행할 때는:
`START_PICK_KOREAN_FIXED.bat`

을 먼저 사용해 주세요.
