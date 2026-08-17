
"""
PICK Smart Understanding Engine

기능:
- 자동 오타/발음 보정
- 사용자 보정 학습
- 고유명사 보호
- 과한 fuzzy 보정 방지
- 보정 내역 기록
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


DATA_DIR = Path("data")
CORRECTION_PATH = DATA_DIR / "corrections.json"
PROTECTED_PATH = DATA_DIR / "protected_terms.json"
HISTORY_PATH = DATA_DIR / "correction_history.jsonl"


DEFAULT_CORRECTIONS = {
    "헌타닉스": "헌트릭스",
    "헌트닉스": "헌트릭스",
    "헌트릭쓰": "헌트릭스",
    "헌타릭스": "헌트릭스",
    "피피티": "PPT",
    "피티피": "PPT",
    "파워포인트": "PPT",
    "이미지열어줘": "이미지 분석 열어줘",
    "동영상열어줘": "동영상 분석 열어줘",
    "파일열어줘": "파일 분석 열어줘",
    "exe만들기": "EXE 만들기",
    "ex 만들기": "EXE 만들기"
}

DEFAULT_PROTECTED_TERMS = [
    "PICK",
    "PPT",
    "EXE",
    "Excel",
    "헌트릭스",
]


def _read_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class PickTypoEngine:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self.corrections = dict(DEFAULT_CORRECTIONS)
        self.corrections.update(_read_json(CORRECTION_PATH, {}))

        protected = _read_json(PROTECTED_PATH, DEFAULT_PROTECTED_TERMS)
        self.protected_terms = set(protected)

        self.save()

    def save(self):
        _write_json(CORRECTION_PATH, self.corrections)
        _write_json(PROTECTED_PATH, sorted(self.protected_terms))

    def normalize(self, text):
        original = (text or "").strip()
        if not original:
            return original, []

        learned = self._learn_from_text(original)
        if learned:
            wrong, correct = learned
            self._log_change(original, wrong, correct, "learned")
            return original, [{"wrong": wrong, "correct": correct, "type": "learned"}]

        t = original
        changes = []

        # 1. 직접 등록된 보정만 우선 적용
        for wrong, correct in sorted(self.corrections.items(), key=lambda x: len(x[0]), reverse=True):
            if wrong and wrong in t:
                if self._is_protected(wrong) and wrong != correct:
                    continue
                t = t.replace(wrong, correct)
                changes.append({"wrong": wrong, "correct": correct, "type": "direct"})
                self._log_change(original, wrong, correct, "direct")

        # 2. 단어 단위 유사 보정은 매우 보수적으로만 적용
        t2, fuzzy_changes = self._safe_fuzzy_fix(t, original)
        changes.extend(fuzzy_changes)
        return t2, changes

    def _learn_from_text(self, text):
        """
        지원:
        - 헌타닉스 말고 헌트릭스야
        - 헌타닉스가 아니라 헌트릭스야
        - 오타등록 헌타닉스=헌트릭스
        - 헌타닉스 -> 헌트릭스
        - 헌타닉스는 헌트릭스로 이해해
        """
        t = text.strip()

        patterns = [
            r"오타등록\s+(.+?)\s*=\s*(.+)$",
            r"(.+?)\s*말고\s*(.+?)(?:야|입니다|라고|로|$)",
            r"(.+?)\s*가\s*아니라\s*(.+?)(?:야|입니다|라고|로|$)",
            r"(.+?)\s*이\s*아니라\s*(.+?)(?:야|입니다|라고|로|$)",
            r"(.+?)\s*->\s*(.+)$",
            r"(.+?)\s*=>\s*(.+)$",
            r"(.+?)\s*는\s*(.+?)\s*로\s*이해해",
            r"(.+?)\s*은\s*(.+?)\s*로\s*이해해",
        ]

        for p in patterns:
            m = re.search(p, t)
            if not m:
                continue

            wrong = self._clean_term(m.group(1))
            correct = self._clean_term(m.group(2))

            if self._valid_pair(wrong, correct):
                self.corrections[wrong] = correct
                self.protected_terms.add(correct)
                self.save()
                return wrong, correct

        return None

    def _safe_fuzzy_fix(self, text, original):
        tokens = re.split(r"(\s+)", text)
        keys = list(self.corrections.keys())
        fixed = []
        changes = []

        for token in tokens:
            raw = token.strip()
            if not raw or raw.isspace():
                fixed.append(token)
                continue

            # 짧은 단어, 숫자, 영어 섞인 단어는 함부로 보정하지 않음
            if len(raw) < 4 or re.search(r"[A-Za-z0-9]", raw):
                fixed.append(token)
                continue

            if self._is_protected(raw):
                fixed.append(token)
                continue

            best = None
            best_score = 0.0
            for wrong in keys:
                if len(wrong) < 4:
                    continue
                score = SequenceMatcher(None, raw, wrong).ratio()
                if score > best_score:
                    best = wrong
                    best_score = score

            # 아주 비슷할 때만 자동 보정
            if best and best_score >= 0.90:
                correct = self.corrections[best]
                fixed.append(token.replace(raw, correct))
                changes.append({"wrong": raw, "correct": correct, "type": "fuzzy"})
                self._log_change(original, raw, correct, "fuzzy")
            else:
                fixed.append(token)

        return "".join(fixed), changes

    def _valid_pair(self, wrong, correct):
        if not wrong or not correct:
            return False
        if wrong == correct:
            return False
        if len(wrong) > 60 or len(correct) > 60:
            return False
        if len(wrong) < 2 or len(correct) < 2:
            return False
        return True

    def _is_protected(self, term):
        return term in self.protected_terms

    def _clean_term(self, s):
        s = (s or "").strip()
        s = re.sub(r"^[\"'“”‘’]+|[\"'“”‘’]+$", "", s)
        s = s.replace("이건", "").replace("이것은", "").replace("그건", "").strip()
        s = re.sub(r"\s+", " ", s)
        return s

    def _log_change(self, original, wrong, correct, typ):
        HISTORY_PATH.parent.mkdir(exist_ok=True)
        row = {
            "original": original,
            "wrong": wrong,
            "correct": correct,
            "type": typ
        }
        with HISTORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
