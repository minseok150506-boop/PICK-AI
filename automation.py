
"""
PICK Automation System

기능:
- 자동 상태 점검
- 자동 대화 로그 백업
- 자동 가상 학습
- 자동 성능 개선 실행
- 일정 간격 반복 실행

주의:
- 자동화는 이 스크립트가 켜져 있는 동안만 동작합니다.
- 실제 학습은 시간이 오래 걸릴 수 있으므로 기본값은 가상 학습입니다.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(".")
LOGS = ROOT / "logs"
BACKUPS = ROOT / "backups"
MODELS = ROOT / "models"
REPORTS = ROOT / "automation_reports"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_run(cmd, title):
    print(f"\n[{now()}] {title}")
    print("명령:", " ".join(cmd))

    try:
        subprocess.run(cmd, check=True)
        print(f"[완료] {title}")
        return True, ""
    except Exception as e:
        print(f"[실패] {title}: {e}")
        return False, str(e)


def health_check():
    required = [
        "app.py",
        "pick_engine.py",
        "pick_llm.py",
        "pick_typo.py",
        "pick_polish.py",
    ]

    missing = [p for p in required if not Path(p).exists()]
    if missing:
        return False, f"누락 파일: {missing}"

    for py in Path(".").glob("*.py"):
        try:
            import py_compile
            py_compile.compile(str(py), doraise=True)
        except Exception as e:
            return False, f"{py} 문법 오류: {e}"

    return True, "상태 점검 정상"


def backup_logs():
    BACKUPS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    targets = [
        LOGS / "conversations.jsonl",
        ROOT / "data" / "corrections.json",
        ROOT / "data" / "protected_terms.json",
    ]

    copied = []
    for target in targets:
        if target.exists():
            dst = BACKUPS / f"{stamp}_{target.name}"
            shutil.copyfile(target, dst)
            copied.append(str(dst))

    return copied


def run_virtual_training():
    if Path("virtual_train.py").exists():
        return safe_run(
            [sys.executable, "virtual_train.py", "--steps", "500", "--interval", "100", "--sleep", "0.005", "--out-dir", "models/virtual_auto"],
            "가상 학습 실행"
        )

    return False, "virtual_train.py 없음"


def run_auto_improve(real=False):
    if real and Path("auto_improve.py").exists():
        return safe_run(
            [sys.executable, "auto_improve.py", "--iters", "1000"],
            "실제 자동 성능 개선"
        )

    if Path("performance_boost.py").exists() and real:
        return safe_run(
            [sys.executable, "performance_boost.py", "--add-quality", "--multiplier", "3", "--iters", "1000"],
            "성능 개선 학습"
        )

    return run_virtual_training()


def write_report(items):
    REPORTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS / f"automation_report_{stamp}.json"

    path.write_text(
        json.dumps({
            "time": now(),
            "items": items,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"자동화 리포트 저장: {path}")


def run_once(mode):
    items = []

    ok, msg = health_check()
    items.append({"task": "health_check", "ok": ok, "message": msg})
    print(f"상태 점검: {msg}")

    backups = backup_logs()
    items.append({"task": "backup_logs", "ok": True, "files": backups})
    print(f"백업 파일 수: {len(backups)}")

    if mode == "check":
        write_report(items)
        return

    if mode == "virtual":
        ok, msg = run_virtual_training()
        items.append({"task": "virtual_training", "ok": ok, "message": msg})

    elif mode == "real":
        ok, msg = run_auto_improve(real=True)
        items.append({"task": "real_improve", "ok": ok, "message": msg})

    elif mode == "auto":
        ok, msg = run_auto_improve(real=False)
        items.append({"task": "auto_improve", "ok": ok, "message": msg})

    write_report(items)


def loop(minutes, mode):
    print("PICK 자동화 시스템 시작")
    print(f"모드: {mode}")
    print(f"간격: {minutes}분")
    print("종료하려면 Ctrl+C")
    print("=" * 50)

    while True:
        run_once(mode)
        print(f"\n[{now()}] 다음 실행까지 대기합니다.")
        time.sleep(minutes * 60)


def main():
    parser = argparse.ArgumentParser(description="PICK Automation System")
    parser.add_argument("--mode", choices=["check", "virtual", "real", "auto"], default="auto")
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.once:
        run_once(args.mode)
    else:
        loop(args.minutes, args.mode)


if __name__ == "__main__":
    main()
