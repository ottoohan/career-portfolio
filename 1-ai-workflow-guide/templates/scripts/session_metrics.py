#!/usr/bin/env python3
"""Claude Code 세션 로그로 AI 사용 기준선을 잰다.

사용: python3 -I session_metrics.py <로그 폴더> <시작일 YYYY-MM-DD> [종료일] [--exclude <세션ID 앞자리>] [--show-corrections]
  로그 폴더 예: ~/.claude/projects/-Users-me-company-source/
  기간은 세션 파일의 마지막 수정 시각 기준이다(시작일 이상, 종료일 다음날 0시 미만).
출력은 집계 수치만 낸다. 프롬프트 원문은 --show-corrections 를 줄 때만 앞 60자.

지표 (개선 전후로 같은 스크립트·같은 옵션으로 비교한다)
- 교정: 두 번째 이후 사용자 발화의 앞 80자에 교정 표현이 있는 건수. 키워드 방식이라 오탐이 섞인다.
  비율보다 추세를 보고, 교정 문구는 --show-corrections 로 직접 읽어 분류한다.
- 권한 거부: 사용자가 거부한 도구 실행 수
- 세션당 스킬 호출: Skill 도구 + 슬래시 명령 호출 수 ÷ 세션 수
- 장시간 세션: 첫 기록~마지막 기록 300분 이상
- 많이 쓴 도구 상위 10 (전용 도구가 필요한 반복 작업 후보)
"""
import collections
import datetime as dt
import json
import re
import statistics
import sys
from pathlib import Path

# 한국어 교정 표현. 팀 말투에 맞게 고친다.
CORRECTION = re.compile(r"(아니|왜 |틀렸|다시 해|잘못|그게 아니|확인 안|멈춰|하지 마|하지마|말고)")
DENIED = ("doesn't want to proceed", "rejected")


def parse_session(path: Path):
    s = dict(user=0, corrections=[], denied=0, skill_calls=0, start=None, end=None)
    tools = collections.Counter()
    for raw in path.open(errors="ignore"):
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if ts := row.get("timestamp"):
            t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            s["start"] = s["start"] or t
            s["end"] = t
        msg = row.get("message") or {}
        content = msg.get("content")
        if row.get("type") == "assistant":
            for c in content or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    name = c["name"]
                    tools["mcp:" + name.split("__")[1] if name.startswith("mcp__") else name] += 1
                    s["skill_calls"] += name == "Skill"
        if row.get("type") != "user" or row.get("isMeta") or row.get("isSidechain"):
            continue
        text = content if isinstance(content, str) else None
        for c in content if isinstance(content, list) else []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_result" and any(d in json.dumps(c.get("content"), ensure_ascii=False) for d in DENIED):
                s["denied"] += 1
            if c.get("type") == "text":
                text = c["text"]
        if not text or "[Request interrupted" in text:
            continue
        if text.startswith("<") and any(k in text for k in ("command-name", "local-command", "system-reminder", "task-notification")):
            s["skill_calls"] += bool(re.search(r"<command-name>", text))
            continue
        s["user"] += 1
        if s["user"] > 1 and CORRECTION.search(text[:80]):
            s["corrections"].append(text[:60].replace("\n", " "))
    return s, tools


def main():
    args = [a for a in sys.argv[1:]]
    show = "--show-corrections" in args
    exclude = args[args.index("--exclude") + 1] if "--exclude" in args else None
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--exclude")]
    folder = Path(pos[0]).expanduser()
    since = dt.datetime.fromisoformat(pos[1]).timestamp()
    until = (dt.datetime.fromisoformat(pos[2]) + dt.timedelta(days=1)).timestamp() if len(pos) > 2 else float("inf")
    files = [f for f in folder.glob("*.jsonl")
             if since <= f.stat().st_mtime < until and not (exclude and f.name.startswith(exclude))]
    sessions, tools = [], collections.Counter()
    for f in files:
        s, t = parse_session(f)
        if s["start"]:
            sessions.append(s)
            tools += t
    if not sessions:
        sys.exit("세션 로그가 없다")
    n = len(sessions)
    turns = sum(s["user"] for s in sessions)
    corrections = [c for s in sessions for c in s["corrections"]]
    minutes = [(s["end"] - s["start"]).total_seconds() / 60 for s in sessions]
    long_n = sum(m > 300 for m in minutes)
    print(f"세션 {n} / 사용자 발화 {turns}")
    print(f"교정 {len(corrections)}건 ({len(corrections) / max(turns, 1):.1%})")
    print(f"권한 거부 {sum(s['denied'] for s in sessions)}건 (세션당 {sum(s['denied'] for s in sessions) / n:.2f})")
    print(f"스킬 호출 {sum(s['skill_calls'] for s in sessions)}회 (세션당 {sum(s['skill_calls'] for s in sessions) / n:.2f})")
    print(f"300분 초과 세션 {long_n}개 ({long_n / n:.0%}), 세션 길이 중앙값 {statistics.median(minutes):.0f}분")
    print("많이 쓴 도구:", ", ".join(f"{k} {v}" for k, v in tools.most_common(10)))
    if show:
        print("\n교정 발화 앞부분:")
        for c in corrections[:40]:
            print(" -", c)


if __name__ == "__main__":
    main()
