#!/usr/bin/env python3
"""레포에 올리기 전 회사 식별 정보 검사.

사용: python3 -I tools/check_sanitize.py [경로 ...]   (기본: 레포 전체)
- 일반 패턴(이메일·자격증명·문서 ID 등)은 이 파일에 있다.
- 회사·동료·사내 시스템 이름은 tools/sanitize_terms.local.txt 에만 둔다(gitignore).
  그 목록이 레포에 올라가면 그 자체가 노출이기 때문이다.
  형식: 한 줄에 `BLOCK|라벨|정규식` 또는 `WARN|라벨|정규식`, `#`은 주석.
BLOCK이 1건이라도 있거나 용어 파일이 없으면 종료코드 1.
"""
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
TERMS = TOOLS / "sanitize_terms.local.txt"
SCAN_SUFFIXES = {".md", ".py", ".json", ".txt", ".template", ".sh", ".yml", ".yaml"}

GENERIC = [
    ("BLOCK", "이메일", r"[\w.+-]+@[\w-]+\.[\w.]+"),
    ("BLOCK", "자격증명 흔적", r"(?i)api[_-]?key\s*[=:]\s*\S|token\s*[=:]\s*\S{8,}|password\s*[=:]\s*\S|\b(?:sk|ghp|gho|xox[bp])-?[A-Za-z0-9_]{10,}"),
    ("BLOCK", "문서·페이지 ID(9~10자리)", r"(?<![0-9a-fA-F.])\d{9,10}(?![0-9a-fA-F.])"),
    ("BLOCK", "메신저 채널·사용자 ID", r"\b[CU]0[0-9A-Z]{8,}\b"),
    ("BLOCK", "DB 테이블·매퍼", r"\btb_[a-z_]+|\w+Mapper\.xml"),
    ("WARN", "티켓 키 모양", r"\b[A-Z]{2,6}-\d{2,}\b"),
    ("WARN", "코드 파일명", r"\b\w+\.(?:vue|java|kt|tsx)\b"),
]


# 일부러 공개하는 값(본인 연락처 등). 회사 정보는 절대 넣지 않는다
ALLOW = {"hanjm900817@gmail.com"}


def load_rules():
    rules = list(GENERIC)
    for raw in TERMS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        level, label, pattern = line.split("|", 2)
        rules.append((level.strip(), label.strip(), pattern))
    return rules


def targets_from(args):
    if args:
        return [Path(a).resolve() for a in args]
    return sorted(
        p for p in ROOT.rglob("*")
        if p.is_file() and p.suffix in SCAN_SUFFIXES
        and ".git" not in p.parts and p.parent != TOOLS
    )


def main():
    if not TERMS.exists():
        print(f"BLOCK 용어 파일 없음: {TERMS.relative_to(ROOT)} — 회사·동료 이름 검사를 할 수 없어 중단")
        sys.exit(1)
    rules = load_rules()
    block_count = 0
    for path in targets_from(sys.argv[1:]):
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        hits = []
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for level, label, pattern in rules:
                for m in re.finditer(pattern, line):
                    if m.group(0) in ALLOW:
                        continue
                    hits.append(f"{level:5} {rel}:{lineno} [{label}] '{m.group(0)}' | {line.strip()[:80]}")
                    block_count += level == "BLOCK"
        print("\n".join(hits) if hits else f"OK    {rel}")
    print(f"\nBLOCK {block_count}건")
    sys.exit(1 if block_count else 0)


if __name__ == "__main__":
    main()
