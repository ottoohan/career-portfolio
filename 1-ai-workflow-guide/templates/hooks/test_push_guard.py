#!/usr/bin/env python3
"""push_guard.py 파이프 테스트. 임시 git 레포를 만들어 실제 브랜치 상태에서 판정한다.

사용: python3 -I test_push_guard.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "push_guard.py"

# (현재 브랜치, 명령, 기대: True=차단)
CASES = [
    ("feature/x", "git push origin feature/x", False),
    ("feature/x", "git push -u origin feature/x", False),
    ("feature/x", "git push", False),
    ("feature/x", "git push origin HEAD", False),
    ("feature/x", "git status && git log --oneline", False),
    ("feature/x", "echo 'git push origin main'", False),
    ("feature/x", "git push origin main", True),
    ("feature/x", "git push origin HEAD:main", True),
    ("feature/x", "git push origin feature/x:refs/heads/main", True),
    ("feature/x", "git push -f origin dev", True),
    ("feature/x", "git push --force-with-lease origin dev", True),
    ("feature/x", "git push -fu origin dev", True),
    ("feature/x", "git push -uf origin dev", True),
    ("feature/x", "git push origin +dev", True),
    ("feature/x", "git push --all origin", True),
    ("feature/x", "git push --mirror origin", True),
    ("feature/x", "git push origin --delete dev", True),
    ("feature/x", "git -C . push origin master", True),
    ("feature/x", "git -c core.askPass=x push origin main", True),
    ("feature/x", "git --no-pager push origin main", True),
    ("feature/x", "cd repo && git push origin main", True),
    ("feature/x", "/usr/bin/git push origin main", True),
    ("feature/x", 'bash -c "git push -f origin dev"', True),
    ("feature/x", "sh -c 'cd x; git push origin main'", True),
    ("feature/x", 'eval "git push -f origin dev"', True),
    ("feature/x", "eval git push origin main", True),
    ("feature/x", "echo $(git push -f origin dev)", True),
    ("feature/x", "echo `git push origin main`", True),
    ("feature/x", "cat <(git push -f origin dev)", True),
    ("feature/x", "g=git; $g push -f origin dev", True),
    ("feature/x", "${GIT:-git} push origin main", True),
    ("feature/x", "git $(echo push) -f origin dev", True),
    ("feature/x", "echo $(git status)", False),
    ("feature/x", 'eval "git push origin feature/x"', False),
    ("main", "git push", True),
    ("main", "git push -u origin", True),
    ("main", "git push origin HEAD", True),
    ("main", "git push origin @", True),
]


def run(cwd, command):
    payload = json.dumps({"tool_input": {"command": command}})
    out = subprocess.run([sys.executable, "-I", str(HOOK)], input=payload, capture_output=True, text=True, cwd=cwd)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    return bool(out.stdout.strip())


def main():
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        git = lambda *a: subprocess.run(["git", "-C", tmp, *a], check=True, capture_output=True)
        git("init", "-q", "-b", "main")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
        git("branch", "feature/x")
        for branch, command, expect in CASES:
            git("checkout", "-q", branch)
            got = run(tmp, command)
            ok = got == expect
            failed += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {'차단' if got else '통과'}  [{branch}] {command}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} 통과")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
