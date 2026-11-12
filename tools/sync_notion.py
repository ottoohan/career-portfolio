#!/usr/bin/env python3
"""이 레포를 Notion 페이지 트리로 올리거나, 이미 올린 페이지를 레포 내용으로 갱신한다.

사용: python3 -I tools/sync_notion.py            # 전체 동기화
      python3 -I tools/sync_notion.py --only 2-career-flow/cases/02-measuring-escape-rate.md
      python3 -I tools/sync_notion.py --dry      # 변환만 점검, API 호출 없음
자격증명: ~/.notion/credentials.json {"api_key": "ntn_...", "parent_page_id": "<마스터를 둘 상위 페이지>"}
          상위 페이지의 ··· → 연결에 통합을 추가해야 한다(안 하면 404).

1단계: 매핑(tools/notion_pages.json)에 없는 페이지만 '원본 링크' 콜아웃 하나로 만든다.
2단계: 각 페이지에서 콜아웃·하위 페이지를 뺀 블록을 지우고, 본문을 콜아웃 바로 뒤에 다시 넣는다.
       하위 페이지 블록은 지우지 않는다(지우면 그 페이지가 휴지통으로 간다).
레포 상대 링크는 Notion 페이지 URL로, 코드·템플릿 파일은 GitHub URL로 바꾼다.
"""
import json, os, re, sys, urllib.request, urllib.error, uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE = REPO / "tools" / "notion_pages.json"
GH = "https://github.com/ottoohan/career-portfolio"
API = "https://api.notion.com/v1"
CRED = os.path.expanduser("~/.notion/credentials.json")


def cred(key):
    return json.load(open(CRED))[key].strip()

# (repo 경로, 부모 repo 경로, 제목 덮어쓰기, 아이콘)
TREE = [
    ("README.md", None, "한지만 포트폴리오 — 검증하고, 고치고, 재는 사람", "📌"),
    ("1-ai-workflow-guide/README.md", "README.md", "1. AI 에이전트 업무 환경 이식 가이드", "🧭"),
    ("2-career-flow/README.md", "README.md", "2. 3년 성과 흐름", "📈"),
    ("3-why-me/README.md", "README.md", "3. 왜 이 사람이 필요한가", "🎯"),
    ("PRIVACY.md", "README.md", "회사 정보 취급 원칙", "🔒"),
    ("2-career-flow/경력기술서.md", "2-career-flow/README.md", None, "📄"),
    ("이력서.md", None, "이력서 — 한지만", "📄"),
] + [
    (f"2-career-flow/cases/{p.name}", "2-career-flow/README.md", f"사례 {p.name[:2]}. " + p.read_text().split("\n")[0][2:].strip(), "🔎")
    for p in sorted((REPO / "2-career-flow/cases").glob("*.md"))
] + [
    # 플레이북 첫 페이지는 프로필 아래 'QA 템플릿 모음' 페이지를 그대로 쓴다(notion_pages.json에 미리 매핑)
    ("4-qa-playbook/README.md", None, "QA 플레이북 — 지금 쓰는 템플릿", "🧰"),
] + [
    (f"4-qa-playbook/{p.name}", "4-qa-playbook/README.md", None, "🧩")
    for p in sorted((REPO / "4-qa-playbook").glob("0*.md"))
]


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": "Bearer " + cred("api_key"), "Notion-Version": "2022-06-28", "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API 실패 {e.code} {path}: {e.read().decode()[:500]}")


def upload_image(path):
    """PNG를 Notion에 올리고 image 블록을 돌려준다."""
    fu = call("POST", "/file_uploads", {"filename": path.name, "content_type": "image/png"})
    b = uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            f"Content-Type: image/png\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"{API}/file_uploads/{fu['id']}/send", data=body, method="POST", headers={
        "Authorization": "Bearer " + cred("api_key"), "Notion-Version": "2022-06-28",
        "Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        urllib.request.urlopen(req).read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"이미지 업로드 실패 {e.code} {path.name}: {e.read().decode()[:300]}")
    return blk("image", type="file_upload", file_upload={"id": fu["id"]})


# ---- 인라인 서식 ----
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
FMT = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\*[^*\s][^*]*?\*)")


def fmt(text, link=None):
    out = []
    for part in FMT.split(text):
        if not part:
            continue
        ann = {}
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            content, ann = part[2:-2], {"bold": True}
        elif part.startswith("`") and part.endswith("`"):
            content, ann = part[1:-1], {"code": True}
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            content, ann = part[1:-1], {"italic": True}
        else:
            content = part
        for i in range(0, len(content), 1900):
            t = {"content": content[i:i + 1900]}
            if link:
                t["link"] = {"url": link}
            out.append({"type": "text", "text": t, "annotations": ann})
    return out


def rich(text, resolve):
    out, pos = [], 0
    for m in LINK.finditer(text):
        out += fmt(text[pos:m.start()])
        out += fmt(m.group(1), resolve(m.group(2)))
        pos = m.end()
    out += fmt(text[pos:])
    return out or [{"type": "text", "text": {"content": ""}}]


LANG = {"python": "python", "py": "python", "bash": "bash", "sh": "shell", "json": "json",
        "yaml": "yaml", "markdown": "markdown", "md": "markdown", "text": "plain text"}


def blk(t, **kw):
    return {"object": "block", "type": t, t: kw}


def split_row(line):
    return [x.strip() for x in line.strip().strip("|").split("|")]


def convert(lines, resolve, image=None):
    R = lambda s: rich(s, resolve)
    blocks, i = [], 0
    stack = []  # (indent, block) 목록 중첩용
    while i < len(lines):
        ln = lines[i]; s = ln.strip()
        if not s:
            stack = []; i += 1; continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)\)$", s)
        if m and image:
            blocks.append(image(m.group(2))); stack = []; i += 1; continue
        if s.startswith("```"):
            lang = LANG.get(s[3:].strip().lower(), "plain text")
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            text = "\n".join(buf)
            blocks.append(blk("code", language=lang, rich_text=[
                {"type": "text", "text": {"content": text[n:n + 1900]}} for n in range(0, max(len(text), 1), 1900)]))
            stack = []; continue
        if s == "---":
            blocks.append(blk("divider")); stack = []; i += 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            blocks.append(blk(f"heading_{min(len(m.group(1)), 3)}", rich_text=R(m.group(2))))
            stack = []; i += 1; continue
        if s.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip()); i += 1
            q = R(buf[0])
            for b in buf[1:]:
                q += [{"type": "text", "text": {"content": "\n"}}] + R(b)
            blocks.append(blk("quote", rich_text=q)); stack = []; continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            header = split_row(lines[i]); i += 2
            rows = [header]
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i])); i += 1
            w = len(header)
            table = {"object": "block", "type": "table", "table": {
                "table_width": w, "has_column_header": True, "has_row_header": False,
                "children": [{"object": "block", "type": "table_row",
                              "table_row": {"cells": [R(x) for x in (r + [""] * w)[:w]]}} for r in rows]}}
            if stack and len(ln) - len(ln.lstrip()) > stack[-1][0]:
                p = stack[-1][1]
                p[p["type"]].setdefault("children", []).append(table)
            else:
                blocks.append(table); stack = []
            continue
        m = re.match(r"^(\s*)(?:([-*])|(\d+)\.)\s+(.*)$", ln)
        if m:
            indent, content = len(m.group(1)), m.group(4)
            todo = re.match(r"^\[( |x)\]\s+(.*)$", content)
            if todo:
                item = blk("to_do", rich_text=R(todo.group(2)), checked=todo.group(1) == "x")
            elif m.group(3):
                item = blk("numbered_list_item", rich_text=R(content))
            else:
                item = blk("bulleted_list_item", rich_text=R(content))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            if stack:
                p = stack[-1][1]
                p[p["type"]].setdefault("children", []).append(item)
            else:
                blocks.append(item)
            stack.append((indent, item)); i += 1; continue
        # 목록 항목에 이어진 들여쓴 문단은 그 항목에 붙인다
        if stack and len(ln) - len(ln.lstrip()) > stack[-1][0]:
            p = stack[-1][1]
            if p[p["type"]].get("children"):
                p[p["type"]]["children"].append(blk("paragraph", rich_text=R(s)))
            else:
                p[p["type"]]["rich_text"] += [{"type": "text", "text": {"content": " "}}] + R(s)
            i += 1; continue
        # 문단: 빈 줄 전까지 이어 붙인다(GitHub 렌더와 같게)
        buf = [s]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^\s*(#|>|\||```|---$|[-*]\s|\d+\.\s)", lines[i]):
            buf.append(lines[i].strip()); i += 1
        blocks.append(blk("paragraph", rich_text=R(" ".join(buf)))); stack = []
    return blocks


def dry():
    for path, *_ in TREE:
        lines = (REPO / path).read_text().split("\n")[1:]
        b = convert(lines, lambda h: h, lambda src, base=(REPO / path).parent: (
            blk("image", src=src) if (base / src).is_file() else sys.exit(f"이미지 없음 {path}: {src}")))
        depth = lambda x, d=1: max([d] + [depth(c, d + 1) for c in x[x["type"]].get("children", []) if x["type"] != "table"])
        types = {}
        for x in b: types[x["type"]] = types.get(x["type"], 0) + 1
        print(path, len(b), "maxdepth", max(depth(x) for x in b), types)


def clear(info):
    """콜아웃과 하위 페이지만 남기고 지운다."""
    cur, n = None, 0
    while True:
        r = call("GET", f"/blocks/{info['id']}/children?page_size=100" + (f"&start_cursor={cur}" if cur else ""))
        for b in r["results"]:
            if b["id"] != info["anchor"] and b["type"] != "child_page":
                call("DELETE", f"/blocks/{b['id']}"); n += 1
        if not r["has_more"]:
            return n
        cur = r["next_cursor"]


def main():
    args = sys.argv[1:]
    if "--dry" in args:
        return dry()
    only = args[args.index("--only") + 1] if "--only" in args else None
    pages = json.loads(STATE.read_text()) if STATE.exists() else {}

    # 1단계: 없는 페이지만 생성
    for path, parent, title, icon in TREE:
        if path in pages:
            continue
        src = REPO / path
        title = title or src.read_text().split("\n")[0][2:].strip()
        pid = re.sub(r"[^0-9a-fA-F]", "", cred("parent_page_id")) if parent is None else pages[parent]["id"]
        blob = f"{GH}/blob/main/{path}"
        anchor = blk("callout", icon={"type": "emoji", "emoji": "🔗"}, color="gray_background",
                     rich_text=[{"type": "text", "text": {"content": "GitHub 원본: "}},
                                {"type": "text", "text": {"content": path, "link": {"url": blob}}}])
        r = call("POST", "/pages", {"parent": {"page_id": pid}, "icon": {"type": "emoji", "emoji": icon},
                                    "properties": {"title": {"title": [{"text": {"content": title}}]}},
                                    "children": [anchor]})
        anchor_id = call("GET", f"/blocks/{r['id']}/children")["results"][0]["id"]
        pages[path] = {"id": r["id"], "url": r["url"], "anchor": anchor_id, "title": title}
        STATE.write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n")
        print("생성", title, r["url"])

    # 2단계: 본문 다시 쓰기
    for path, parent, title, icon in TREE:
        if only and path != only:
            continue
        info = pages[path]
        base = (REPO / path).parent

        def resolve(href, base=base):
            if href.startswith("http"):
                return href
            if href.startswith("#"):
                return None  # 같은 페이지 앵커는 링크 없이 텍스트로
            target = (base / href.split("#")[0]).resolve()
            rel = os.path.relpath(target, REPO)
            if rel in pages:
                return pages[rel]["url"]
            kind = "tree" if target.is_dir() else "blob"
            return f"{GH}/{kind}/main/{rel}"

        lines = (REPO / path).read_text().split("\n")
        new_title = title or lines[0][2:].strip()
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
        blocks = convert(lines, resolve, lambda src, base=base: upload_image((base / src).resolve()))
        removed = clear(info)
        if new_title != info["title"]:
            call("PATCH", f"/pages/{info['id']}", {"properties": {"title": {"title": [{"text": {"content": new_title}}]}}})
            info["title"] = new_title
        after = info["anchor"]
        for n in range(0, len(blocks), 100):
            before = {b["id"] for b in call("GET", f"/blocks/{info['id']}/children?page_size=100")["results"]}
            r = call("PATCH", f"/blocks/{info['id']}/children", {"children": blocks[n:n + 100], "after": after})
            # 이번에 새로 들어간 블록의 마지막 뒤에 이어 붙인다
            after = [b["id"] for b in r["results"] if b["id"] not in before][-1]
        STATE.write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n")
        print("갱신", info["title"], f"삭제 {removed} / 작성 {len(blocks)}")


main()
