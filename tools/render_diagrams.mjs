// 4-qa-playbook/img/src/*.mmd 를 PNG로 렌더링한다. GitHub과 Notion이 같은 그림을 쓴다.
// 사용: PLAYWRIGHT_CORE=<playwright-core 경로> node tools/render_diagrams.mjs
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const srcDir = path.join(root, "4-qa-playbook/img/src");
const outDir = path.join(root, "4-qa-playbook/img");
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_CORE || "playwright-core");

const html = `<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;background:#fff;font-family:"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
#d{display:inline-block;padding:24px}</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script></head>
<body><div id="d"></div></body></html>`;

const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 2, viewport: { width: 1400, height: 900 } });
await page.setContent(html, { waitUntil: "load" });
await page.evaluate(() => mermaid.initialize({
  startOnLoad: false, theme: "neutral",
  themeVariables: { fontFamily: '"Apple SD Gothic Neo","Noto Sans KR",sans-serif', fontSize: "16px" },
  flowchart: { htmlLabels: true, curve: "basis", useMaxWidth: false },
  pie: { useMaxWidth: false }, xyChart: { width: 640, height: 380 },
}));
for (const f of fs.readdirSync(srcDir).filter((x) => x.endsWith(".mmd")).sort()) {
  const code = fs.readFileSync(path.join(srcDir, f), "utf8");
  const ok = await page.evaluate(async (c) => {
    try {
      const { svg } = await mermaid.render("g" + Math.random().toString(36).slice(2), c);
      document.getElementById("d").innerHTML = svg;
      return null;
    } catch (e) { return String(e.message || e); }
  }, code);
  if (ok) { console.error("실패", f, ok); process.exitCode = 1; continue; }
  const out = path.join(outDir, f.replace(/\.mmd$/, ".png"));
  await page.locator("#d").screenshot({ path: out });
  console.log("렌더", path.relative(root, out));
}
await browser.close();
