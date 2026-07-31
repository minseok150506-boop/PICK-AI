
from pathlib import Path
import py_compile
import sys

required = [
    "app.py",
    "pick_llm.py",
    "pick_typo.py",
    "pick_polish.py",
]

missing = [p for p in required if not Path(p).exists()]
if missing:
    print("누락 파일:", missing)
    sys.exit(1)

for p in Path(".").glob("*.py"):
    try:
        py_compile.compile(str(p), doraise=True)
        print("OK:", p)
    except Exception as e:
        print("ERROR:", p, e)
        sys.exit(1)

print("PICK 상태 점검 완료")
