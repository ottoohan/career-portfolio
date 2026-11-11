#!/usr/bin/env python3
"""PreToolUse(Bash) 훅: 강제 push와 보호 브랜치 직접 push를 막는다.

등록(.claude/settings.json):
  "hooks": {"PreToolUse": [{"matcher": "Bash",
    "hooks": [{"type": "command", "command": "python3 -I .claude/hooks/push_guard.py"}]}]}

원칙: 훅은 "기계적으로 판정 가능 + 어기면 되돌릴 수 없음" 두 조건을 모두 만족할 때만 쓴다.
판정이 애매하면 막는다(fail-closed). 에러를 2>/dev/null 로 삼키지 않는다.
등록 후 반드시 test_push_guard.py 로 실제 입력을 넣어 본다.
"""
import json
import re
import shlex
import subprocess
import sys

PROTECTED = {"main", "master"}  # 회사 규칙에 맞게 바꾼다
# git 전역 옵션 중 값을 하나 받는 것
GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
SHELLS = {"bash", "sh", "zsh", "dash"}


class Deny(Exception):
    pass


def current_branch(repo):
    cmd = ["git"] + (["-C", repo] if repo else []) + ["symbolic-ref", "--short", "-q", "HEAD"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    branch = out.stdout.strip()
    if not branch:  # 브랜치를 알 수 없으면 막는다
        raise Deny("현재 브랜치를 확인할 수 없음")
    return branch


def is_force(arg):
    if arg.startswith("--force") or arg in {"--mirror", "--all", "--delete", "-d"}:
        return True
    # -fu, -uf 같은 묶음 짧은 옵션
    return bool(re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", arg))


def check_git(args):
    repo = None
    i = 0
    while i < len(args) and args[i].startswith("-"):  # git 전역 옵션 건너뛰기
        opt = args[i]
        if opt in GLOBAL_WITH_VALUE:
            if opt == "-C" and i + 1 < len(args):
                repo = args[i + 1]
            i += 2
        else:
            i += 1
    if i >= len(args) or args[i] != "push":
        return
    rest = args[i + 1:]
    for arg in rest:
        if is_force(arg):
            raise Deny(f"강제·일괄 push 금지({arg})")
        if arg.startswith("+"):
            raise Deny("+refspec 강제 push 금지")
    positional = [r for r in rest if not r.startswith("-")]
    refspecs = positional[1:]  # 첫 번째는 원격 이름
    if not refspecs:
        targets = {current_branch(repo)}
    else:
        targets = set()
        for ref in refspecs:
            dst = ref.split(":")[-1].removeprefix("refs/heads/")
            targets.add(current_branch(repo) if dst in {"HEAD", "@"} else dst)
    hit = PROTECTED & targets
    if hit:
        raise Deny(f"{', '.join(sorted(hit))} 직접 push 금지 — PR로 머지할 것")


def check_command(command, depth=0):
    if depth > 3:
        raise Deny("중첩이 너무 깊어 판정 불가")
    for segment in re.split(r"&&|\|\||;|\||\n", command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            if "push" in segment:
                raise Deny("따옴표를 해석할 수 없는 push 명령")
            continue
        for j, tok in enumerate(tokens):
            base = tok.rsplit("/", 1)[-1]
            if base == "git":
                check_git(tokens[j + 1:])
                break
            if base in SHELLS and "-c" in tokens[j + 1:]:  # bash -c "git push ..."
                k = tokens.index("-c", j + 1)
                if k + 1 < len(tokens):
                    check_command(tokens[k + 1], depth + 1)
                break


def main():
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    try:
        check_command(command)
    except Deny as e:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"push 안전 규칙 위반: {e}",
        }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
