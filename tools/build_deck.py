import json, sys, pathlib
"""슬라이드 원본(deck.json · deck.css · slides/)을 넘겨 보는 HTML 한 장으로 합친다.
사용: python3 build_deck.py <원본 폴더(deck.json이 있는 곳) 또는 그 상위> <출력.html>"""
root = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
proj = root if (root/"deck.json").exists() else root/"project"
idx = json.loads((proj/"deck.json").read_text())
css = (proj/"deck.css").read_text()
slides = [(proj/f"slides/{i}.html").read_text().strip() for i in idx["order"]]
fonts = "&".join(f["href"].split("?",1)[1].replace("&display=swap","") for f in idx["faces"].values())
viewer_css = """
html,body{margin:0;height:100%;background:#0B1117;overflow:hidden}
#stage{position:absolute;left:50%;top:50%;width:1920px;height:1080px;transform-origin:0 0}
#stage>section{position:absolute;inset:0;width:1920px;height:1080px;display:none}
#stage>section.on{display:flex}
section aside{display:none}
section h1,section h2,section h3,section p{margin:0}
x-shape[kind="arrow-right"]{display:block;clip-path:polygon(0 30%,60% 30%,60% 0,100% 50%,60% 100%,60% 70%,0 70%)}
table.tbl{border-collapse:collapse}
table.tbl th,table.tbl td{text-align:left;padding:.45em .6em;border-bottom:2px solid #D7DFDD}
table.tbl th{font-weight:700}
#hud{position:fixed;right:16px;bottom:12px;font:14px/1.4 system-ui,sans-serif;color:#9AA8B4}
#notes{position:fixed;left:0;right:0;bottom:0;max-height:30vh;overflow:auto;background:#182129;color:#E4EAEE;font:18px/1.6 system-ui,sans-serif;padding:16px 24px;display:none;box-sizing:border-box}
#notes.on{display:block}
"""
html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{idx['title']}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{fonts}&display=swap">
<style>{css}
{viewer_css}</style></head><body>
<div id="stage">
{chr(10).join(slides)}
</div>
<div id="hud"></div><div id="notes"></div>
<script>
const s=[...document.querySelectorAll('#stage>section')],st=document.getElementById('stage'),hud=document.getElementById('hud'),nt=document.getElementById('notes');
let i=Math.max(0,Math.min(s.length-1,(parseInt(location.hash.slice(1))||1)-1));
function fit(){{const k=Math.min(innerWidth/1920,innerHeight/1080);st.style.transform=`scale(${{k}}) translate(-50%,-50%)`;st.style.transformOrigin='0 0';st.style.left='50%';st.style.top='50%';}}
function show(){{s.forEach((x,j)=>x.classList.toggle('on',j===i));const a=s[i].querySelector('aside');nt.textContent=a?a.textContent:'';hud.textContent=`${{i+1}} / ${{s.length}} · ←/→ 이동 · N 대본`;history.replaceState(null,'','#'+(i+1));}}
addEventListener('keydown',e=>{{if(['ArrowRight','PageDown',' '].includes(e.key))i=Math.min(s.length-1,i+1);else if(['ArrowLeft','PageUp'].includes(e.key))i=Math.max(0,i-1);else if(e.key==='n'||e.key==='N')nt.classList.toggle('on');else if(e.key==='Home')i=0;else if(e.key==='End')i=s.length-1;else return;show();}});
addEventListener('click',e=>{{if(e.target.closest('#notes'))return;i=e.clientX>innerWidth/2?Math.min(s.length-1,i+1):Math.max(0,i-1);show();}});
addEventListener('hashchange',()=>{{const n=(parseInt(location.hash.slice(1))||1)-1;if(n!==i&&n>=0&&n<s.length){{i=n;show();}}}});addEventListener('resize',fit);fit();show();
</script></body></html>"""
out.write_text(html)
print(out, len(slides), "slides", out.stat().st_size, "bytes")
