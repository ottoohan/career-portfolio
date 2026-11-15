#!/usr/bin/env python3
"""대표 숫자가 문서마다 같은지 검사한다. 정본은 2-career-flow/경력기술서.md의 '핵심 숫자' 표.

같은 숫자가 README·이력서·경력기술서·사례·발표 자료에 반복되므로, 한 곳만 고치면 나머지가 옛 값으로 남는다.
(2026-11 만족도 9.4 → 9.33 교정 때 7개 파일을 고쳐야 했다.)

사용: python3 -I tools/check_numbers.py   # 불일치가 있으면 종료 코드 1
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = {".md", ".html"}
SKIP_DIRS = {".git", "node_modules"}

# 정본 값. 바꿀 때는 여기와 경력기술서 표를 같이 고친다.
CANON = {
    "만족도 시작": "8.23",
    "만족도 최종": "9.33",
    "결함 유출률": "3.40",
    "유출률 분자": "7",
    "유출률 분모": "206",
    "직접 커밋": "328",
    "결제 TC": "290",
    "검증 티켓": "1,136",
    "운영 실수 전": "13.9",
    "운영 실수 후": "9.7",
    "요청 감소": "35.6",
    "운영지원 메시지": "345",
}

# (설명, 정규식, 정본 키 목록 — 그룹 순서대로)
RULES = [
    ("만족도 변화", re.compile(r"만족도[^\n|]{0,40}?(\d\.\d+)\s*\*{0,2}\s*(?:→|->)\s*\*{0,2}(\d\.\d+)"), ["만족도 시작", "만족도 최종"]),
    ("유출률", re.compile(r"유출률[^\n|]{0,20}?\*{0,2}(\d\.\d\d)%"), ["결함 유출률"]),
    ("유출률 식", re.compile(r"핫픽스\s*(\d+)\s*건?\s*÷[^\n]{0,30}?배포\s*(\d+)"), ["유출률 분자", "유출률 분모"]),
    ("유출률 식(문장)", re.compile(r"운영 배포\s*(\d+)번 중\s*(\d+)번"), ["유출률 분모", "유출률 분자"]),
    # 레포별 내역(백오피스 프론트 161 등)은 대표 숫자가 아니라서 '직접·프로덕션 커밋'만 본다
    ("커밋 수", re.compile(r"(?:직접|프로덕션)[^\n|]{0,12}?커밋\s*\*{0,2}(\d{3})\s*\*{0,2}\s*건"), ["직접 커밋"]),
    ("운영 실수 비율", re.compile(r"(\d{1,2}\.\d)%\s*\*{0,2}\s*→\s*\*{0,2}(\d{1,2}\.\d)%"), ["운영 실수 전", "운영 실수 후"]),
    ("요청 감소율", re.compile(r"요청[^\n|]{0,40}?−(\d{2}\.\d)%"), ["요청 감소"]),
    ("운영지원 메시지", re.compile(r"(?:운영지원 메시지|운영 부서에 직접 공유)[^\n|]{0,8}?\*{0,2}\(?(\d{3})건"), ["운영지원 메시지"]),
    ("검증 티켓", re.compile(r"검증[^\n|]{0,6}?\*{0,2}(\d,\d{3})\s*\*{0,2}\s*건"), ["검증 티켓"]),
]

# 한 번 틀렸다가 고친 값. 다시 나타나면 무조건 실패.
STALE = [
    (re.compile(r"7\.29"), "만족도 옛 기준값 7.29(원자료 미확인)"),
    (re.compile(r"8\.82"), "만족도 옛 중간값 8.82(원자료 미확인)"),
    (re.compile(r"만족도[^\n]{0,60}?9\.4(?!\d)"), "만족도 옛 최종값 9.4(원본 9.33)"),
    (re.compile(r"약\s*50명"), "만족도 응답자 '약 50명'(원본 최종 회차 15명)"),
    (re.compile(r"역대 최고 갱신"), "'회차마다 역대 최고'(6월·9월 하락)"),
]


def files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in SCAN and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            yield p


def main():
    bad = 0
    for p in files():
        rel = p.relative_to(ROOT)
        for n, line in enumerate(p.read_text(errors="ignore").split("\n"), 1):
            for pat, why in STALE:
                if pat.search(line):
                    print(f"STALE {rel}:{n} {why} | {line.strip()[:120]}")
                    bad += 1
            for name, pat, keys in RULES:
                for m in pat.finditer(line):
                    got = m.groups()
                    want = tuple(CANON[k] for k in keys)
                    if got != want:
                        print(f"DIFF  {rel}:{n} {name} {'/'.join(got)} ≠ 정본 {'/'.join(want)} | {line.strip()[:120]}")
                        bad += 1
    print(f"불일치 {bad}건")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
