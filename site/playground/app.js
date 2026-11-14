/* DeepSeek API Playground — 浏览器直连官方 API 的真调测试台
 * 不依赖任何构建工具或第三方库；密钥只存 localStorage。
 */

const BASE = "https://api.deepseek.com";
const MODEL = "deepseek-flash";
const LS_KEY = "ds-playground-key";

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html != null) n.innerHTML = html;
  return n;
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* ------------------------------------------------------------------ key */

function getKey() { return localStorage.getItem(LS_KEY) || ""; }
function setKeyState() {
  const k = getKey();
  $("#keyState").textContent = k ? `已保存 · ${k.slice(0, 6)}…${k.slice(-4)}` : "未设置密钥";
  $("#keyState").style.color = k ? "var(--green)" : "var(--dimmer)";
}

/* ------------------------------------------------------------------ 网络 */

async function request(path, { body, bearer = false, raw = false, extraHeaders = {} } = {}) {
  const key = getKey();
  if (!key) throw new Error("请先填写并保存 API Key");
  const headers = { ...extraHeaders };
  if (!raw) headers["Content-Type"] = "application/json";
  if (bearer) headers["Authorization"] = `Bearer ${key}`;
  else headers["x-api-key"] = key;

  const res = await fetch(BASE + path, {
    method: "POST",
    headers,
    body: raw ? body : JSON.stringify(body),
  });
  return res;
}

async function sse(res, onEvent) {
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += value;
    let i;
    while ((i = buf.indexOf("\n\n")) !== -1) {
      const chunk = buf.slice(0, i);
      buf = buf.slice(i + 2);
      let event = "";
      const dataLines = [];
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
      }
      const data = dataLines.join("\n");
      if (!data) continue;
      if (data === "[DONE]") { onEvent({ event: "done", data: {} }); continue; }
      try { onEvent({ event, data: JSON.parse(data) }); } catch (_) { /* 忽略非 JSON 行 */ }
    }
  }
}

/* ------------------------------------------------------------------ 轻量 Markdown */

function mdToHtml(src) {
  const codes = [];
  let s = esc(src).replace(/```([\s\S]*?)```/g, (_, c) => {
    codes.push(c.replace(/^\n+|\n+$/g, ""));
    return `\u0000CODE${codes.length - 1}\u0000`;
  });

  // 表格
  s = s.replace(/(?:^\|.*\|[ \t]*\n?)+/gm, (block) => {
    const rows = block.trim().split("\n").map((r) =>
      r.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim()));
    if (rows.length < 2 || !/^:?-{2,}:?$/.test(rows[1][0] || "")) return block;
    const head = rows[0];
    const body = rows.slice(2);
    return `<table class="md-table"><thead><tr>${head.map((c) => `<th>${c}</th>`).join("")}</tr></thead>`
      + `<tbody>${body.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  });

  s = s.replace(/^#{1,6}\s+(.+)$/gm, "<h4>$1</h4>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/^\s*[-*]\s+(.+)$/gm, "<li>$1</li>");
  s = s.replace(/(?:<li>[\s\S]*?<\/li>\n?)+/g, (m) => `<ul>${m.replace(/\n/g, "")}</ul>`);
  s = s.replace(/^>\s?(.+)$/gm, "<blockquote>$1</blockquote>");

  s = s.split(/\n{2,}/).map((p2) => {
    const t = p2.trim();
    if (!t) return "";
    if (/^<(h4|ul|table|pre|blockquote)/.test(t)) return t;
    return `<p>${t.replace(/\n/g, "<br>")}</p>`;
  }).join("");

  return s.replace(/\u0000CODE(\d+)\u0000/g, (_, i) => `<pre class="md-code"><code>${codes[+i]}</code></pre>`);
}

function citeLinks(citations) {
  return (citations || []).map((c, i) => {
    const url = c.url || "";
    const title = (c.title || url).replace(/"/g, "&quot;");
    return `<a class="cite" href="${esc(url)}" target="_blank" rel="noreferrer" title="${title}">${i + 1}</a>`;
  }).join("");
}

/* ------------------------------------------------------------------ 工具 */

function reminderLine() {
  const now = new Date();
  const wd = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"][now.getDay()];
  const p = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())},${wd},上海,Web,中文`;
}

function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

/* ------------------------------------------------------------------ 输出区 */

const state = { request: null, raw: null, tab: "render" };

function showRequest(obj) {
  state.request = obj;
  $("#reqPre")?.remove();
  const pre = el("pre");
  pre.id = "reqPre";
  pre.textContent = JSON.stringify(obj, null, 2);
  reqBox.replaceChildren(pre);
}

function showRaw(obj) {
  const pre = el("pre");
  pre.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  rawBox.replaceChildren(pre);
}

function reset() {
  // 只清渲染与原始响应；请求体保留，方便对照
  renderBox.replaceChildren();
  rawBox.replaceChildren();
}

const out = $("#out");
const renderBox = el("div"); renderBox.id = "renderBox";
const rawBox = el("div"); rawBox.hidden = true; rawBox.id = "rawBox";
const reqBox = el("div"); reqBox.hidden = true; reqBox.id = "reqBox";
out.replaceChildren(renderBox, rawBox, reqBox);

function setTab(name) {
  state.tab = name;
  for (const b of document.querySelectorAll(".tab")) b.classList.toggle("active", b.dataset.tab === name);
  renderBox.hidden = name !== "render";
  rawBox.hidden = name !== "raw";
  reqBox.hidden = name !== "req";
}

/* ------------------------------------------------------------------ 渲染器：Messages 块 */

function renderMessagesBlocks(container, blocks, opts = {}) {
  const wrap = el("div", "turn");
  if (opts.question) {
    const u = el("div", "user");
    u.appendChild(el("div", "bubble", esc(opts.question).replace(/\n/g, "<br>")));
    wrap.appendChild(u);
  }
  for (const b of blocks) {
    const t = b.type;
    if (t === "thinking") {
      const d = el("details", "block thinking");
      d.appendChild(el("summary", "head", `已思考 · ${(b.thinking || "").length} 字符`));
      d.appendChild(el("div", "txt", esc(b.thinking || "")));
      wrap.appendChild(d);
    } else if (t === "server_tool_use") {
      const inp = b.input || {};
      const detail = inp.queries ? inp.queries.join(" / ") : inp.url || inp.pattern || "";
      const box = el("div", "block tool");
      box.appendChild(el("div", "head", `⌕ ${esc(b.name)} · ${esc(inp.action)} · ${esc(b.kind || "")}`));
      if (detail) box.appendChild(el("div", "result", `<span class="fav">›</span><span><span class="u">${esc(detail)}</span></span>`));
      wrap.appendChild(box);
    } else if (t === "web_search_tool_result") {
      const box = el("div", "block tool");
      const items = b.content || [];
      box.appendChild(el("div", "head", `搜索结果 · ${items.length} 条 · ${esc(b.kind || "")}`));
      for (const it of items) {
        if (it.type !== "web_search_result") {
          box.appendChild(el("div", "result", `<span class="fav">!</span><span class="sn">${esc(JSON.stringify(it))}</span>`));
          continue;
        }
        box.appendChild(el("div", "result", `
          <span class="fav">${esc((it.site_name || hostOf(it.url))[0] || "?")}</span>
          <span>
            <span class="t">${esc(it.title || "")}</span>
            <span class="u">${esc(it.url)}</span>
            <span class="sn">${esc((it.snippet || "").slice(0, 160))}</span>
          </span>`));
      }
      wrap.appendChild(box);
    } else if (t === "web_fetch_tool_result") {
      const box = el("div", "block tool fetch");
      const c = b.content || {};
      if (c.type === "web_fetch_result") {
        box.appendChild(el("div", "head", `↓ 打开网页 · ${esc(b.kind || "")}${b.signature ? " · signature ✓" : ""}`));
        box.appendChild(el("div", "result", `
          <span class="fav">${esc((c.content?.title || hostOf(c.url))[0] || "?")}</span>
          <span><span class="t">${esc(c.content?.title || "")}</span><span class="u">${esc(c.url)}</span></span>`));
      } else {
        box.appendChild(el("div", "head", "↓ 抓取失败"));
        box.appendChild(el("div", "result", `<span class="fav">!</span><span class="sn">${esc(JSON.stringify(c))}</span>`));
      }
      wrap.appendChild(box);
    } else if (t === "text") {
      const holder = wrap.querySelector(".answer") || (() => { const d = el("div", "answer"); wrap.appendChild(d); return d; })();
      const div = el("div", "answer-text");
      div.innerHTML = mdToHtml(b.text || "") + citeLinks(b.citations);
      holder.appendChild(div);
    }
  }
  container.appendChild(wrap);
}

/* ------------------------------------------------------------------ 渲染器：Responses / Chat */

function renderResponses(container, data) {
  const wrap = el("div", "turn");
  for (const item of data.output || []) {
    if (item.type === "web_search_call") {
      const box = el("div", "block tool");
      box.appendChild(el("div", "head", `⌕ ${esc(item.kind)} · ${esc(item.action?.type)} · ${esc(item.status)}`));
      const q = item.action?.queries?.join(" / ") || item.action?.url || item.page?.url || "";
      if (q) box.appendChild(el("div", "result", `<span class="fav">›</span><span class="u">${esc(q)}</span>`));
      for (const s of item.action?.sources || []) {
        box.appendChild(el("div", "result", `
          <span class="fav">${esc((s.site_name || hostOf(s.url))[0] || "?")}</span>
          <span><span class="t">${esc(s.title || "")}</span><span class="u">${esc(s.url)}</span></span>`));
      }
      wrap.appendChild(box);
    } else if (item.type === "reasoning") {
      const d = el("details", "block thinking");
      const txt = (item.content || []).map((c) => c.text || "").join("");
      d.appendChild(el("summary", "head", `已推理 · ${txt.length} 字符`));
      d.appendChild(el("div", "txt", esc(txt)));
      wrap.appendChild(d);
    } else if (item.type === "message") {
      const div = el("div", "answer");
      for (const c of item.content || []) {
        if (c.type !== "output_text") continue;
        const p = el("p");
        p.innerHTML = mdToHtml(c.text || "");
        for (const a of c.annotations || []) {
          const c2 = a.url_citation || a;
          const link = el("a", "cite", "↗");
          link.href = c2.url; link.target = "_blank"; link.rel = "noreferrer";
          link.title = c2.url;
          p.appendChild(link);
        }
        div.appendChild(p);
      }
      wrap.appendChild(div);
    }
  }
  if (data.usage) wrap.appendChild(el("div", "usage", `usage · ${esc(JSON.stringify(data.usage))}`));
  if (data.title) wrap.appendChild(el("div", "meta", `title · ${esc(data.title)}`));
  if (data.status && data.status !== "completed") wrap.appendChild(el("div", "meta", `status · ${esc(data.status)}`));
  container.appendChild(wrap);
}

function renderChat(container, data) {
  const msg = data.choices?.[0]?.message || {};
  const wrap = el("div", "turn");
  for (const step of msg.server_tool_calls || []) {
    for (const call of step.calls || []) {
      const box = el("div", "block tool");
      box.appendChild(el("div", "head", `⌕ ${esc(call.type)} · ${esc(call.kind)} · ${esc(call.action?.type)} · ${esc(call.status)}`));
      const q = call.action?.queries?.join(" / ") || call.action?.url || call.page?.url || "";
      if (q) box.appendChild(el("div", "result", `<span class="fav">›</span><span class="u">${esc(q)}</span>`));
      for (const s of call.sources || []) {
        box.appendChild(el("div", "result", `
          <span class="fav">${esc((s.site_name || hostOf(s.url))[0] || "?")}</span>
          <span><span class="t">${esc(s.title || "")}</span><span class="u">${esc(s.url)}</span></span>`));
      }
      if (call.signature) box.appendChild(el("div", "result", `<span class="fav">✓</span><span class="sn">signature ${esc(call.signature.slice(0, 24))}…</span>`));
      wrap.appendChild(box);
    }
  }
  const div = el("div", "answer");
  const p = el("p");
  p.innerHTML = mdToHtml(msg.content || "");
  for (const a of msg.annotations || []) {
    const c = a.url_citation || {};
    const link = el("a", "cite", "↗");
    link.href = c.url; link.target = "_blank"; link.rel = "noreferrer";
    link.title = c.url;
    p.appendChild(link);
  }
  div.appendChild(p);
  wrap.appendChild(div);
  if (data.usage) wrap.appendChild(el("div", "usage", `usage · ${esc(JSON.stringify(data.usage))}`));
  if (msg.title) wrap.appendChild(el("div", "meta", `title · ${esc(msg.title)}`));
  if (data.choices?.[0]?.finish_reason) wrap.appendChild(el("div", "meta", `finish · ${esc(data.choices[0].finish_reason)}`));
  container.appendChild(wrap);
}

/* ------------------------------------------------------------------ 能力定义 */

const caps = [
  {
    id: "chat",
    group: "对话",
    title: "综合对话（三协议）",
    desc: "勾选工具后一次请求里同时开搜索、读链、安全审核、标题、日期标记；可以切换 Messages / Responses / Chat Completions 三种协议。",
    fields: [
      { id: "prompt", type: "textarea", label: "问题", value: "DeepSeek 全家桶 API 里，读链和搜索有什么区别？顺便看下 https://api-docs.deepseek.com/zh-cn/guides/web_tools" },
      { id: "protocol", type: "select", label: "协议", options: [["messages", "Messages（Anthropic 兼容，流式）"], ["responses", "Responses"], ["chat", "Chat Completions"]] },
      { id: "thinking", type: "select", label: "思考", options: [["disabled", "关闭（kind=search）"], ["enabled", "开启（kind=deep_search）"]], value: "disabled" },
      { id: "checks", type: "checks", items: [
        { id: "search", label: "deepseek_web_search", value: true },
        { id: "readurl", label: "deepseek_read_url", value: true },
        { id: "safety", label: "safety_check: high", value: true },
        { id: "title", label: "title", value: true },
        { id: "reminder", label: "latest_reminder", value: true },
      ] },
    ],
    async run(v) {
      const tools = [];
      if (v.search) tools.push({ type: "deepseek_web_search", name: "deepseek_web_search" });
      if (v.readurl) tools.push({ type: "deepseek_read_url", name: "deepseek_read_url" });

      if (v.protocol === "messages") {
        const msgs = [];
        if (v.reminder) msgs.push({ role: "latest_reminder", content: reminderLine() });
        msgs.push({ role: "user", content: v.prompt });

        const body = { model: MODEL, thinking: { type: v.thinking }, messages: msgs };
        if (tools.length) body.tools = tools;
        if (v.safety) body.safety_check = { level: "high" };
        if (v.title) body.title = { enabled: true };
        body.stream = true;
        showRequest(body);
        reset();

        const res = await request("/anthropic/v1/messages", { body });
        if (!res.ok) throw new Error(`HTTP ${res.status}\n${await res.text()}`);

        const wrap = el("div", "turn");
        const u = el("div", "user");
        u.appendChild(el("div", "bubble", esc(v.prompt).replace(/\n/g, "<br>")));
        wrap.appendChild(u);
        renderBox.appendChild(wrap);

        let answerDiv = null, currentP = null;
        const rawEvents = [];
        const cites = [];

        await sse(res, ({ event, data }) => {
          rawEvents.push({ event, data });
          const t = data.type || event;
          if (t === "content_block_start") {
            const b = data.content_block;
            if (b.type === "server_tool_use") {
              const box = el("div", "block tool");
              box.appendChild(el("div", "head", `⌕ ${esc(b.name)} · ${esc(b.input?.action)} · ${esc(b.kind || "")}`));
              const q = b.input?.queries?.join(" / ") || b.input?.url || b.input?.pattern || "";
              if (q) box.appendChild(el("div", "result", `<span class="fav">›</span><span class="u">${esc(q)}</span>`));
              wrap.appendChild(box);
            } else if (b.type === "web_search_tool_result") {
              const box = el("div", "block tool");
              const items = b.content || [];
              box.appendChild(el("div", "head", `搜索结果 · ${items.length} 条 · ${esc(b.kind || "")}`));
              for (const it of items) {
                box.appendChild(el("div", "result", `
                  <span class="fav">${esc((it.site_name || hostOf(it.url || ""))[0] || "?")}</span>
                  <span><span class="t">${esc(it.title || "")}</span><span class="u">${esc(it.url || "")}</span>
                  <span class="sn">${esc((it.snippet || "").slice(0, 150))}</span></span>`));
              }
              wrap.appendChild(box);
            } else if (b.type === "web_fetch_tool_result") {
              const c = b.content || {};
              const box = el("div", "block tool fetch");
              box.appendChild(el("div", "head", `↓ 网页 · ${esc(b.kind || "")}${b.signature ? " · signature ✓" : ""}`));
              if (c.type === "web_fetch_result") {
                box.appendChild(el("div", "result", `<span class="fav">${esc((c.content?.title || hostOf(c.url))[0] || "?")}</span>
                  <span><span class="t">${esc(c.content?.title || "")}</span><span class="u">${esc(c.url)}</span></span>`));
              } else {
                box.appendChild(el("div", "result", `<span class="fav">!</span><span class="sn">${esc(JSON.stringify(c))}</span>`));
              }
              wrap.appendChild(box);
            } else if (b.type === "thinking") {
              const d = el("details", "block thinking");
              d.appendChild(el("summary", "head", "思考中…"));
              const txt = el("div", "txt");
              d.appendChild(txt);
              d._txt = txt;
              wrap.appendChild(d);
            } else if (b.type === "text") {
              if (!answerDiv) { answerDiv = el("div", "answer"); wrap.appendChild(answerDiv); }
              currentP = el("p");
              answerDiv.appendChild(currentP);
            }
          } else if (t === "content_block_delta") {
            const d = data.delta || {};
            if (d.type === "thinking_delta") {
              const box = wrap.querySelector(".thinking:last-of-type");
              if (box && box._txt) box._txt.textContent += d.thinking || "";
            } else if (d.type === "text_delta" && currentP) {
              currentP.appendChild(document.createTextNode(d.text || ""));
            } else if (d.type === "citations_delta") {
              cites.push(d.citation || {});
            }
          } else if (t === "message_delta") {
            if (answerDiv) {
              const full = answerDiv.textContent;
              answerDiv.innerHTML = mdToHtml(full) + citeLinks(cites);
            }
            const u2 = data.usage || {};
            const detail = data.delta?.title ? ` · title=${data.delta.title}` : "";
            wrap.appendChild(el("div", "usage",
              `stop=${esc(data.delta?.stop_reason || "")} · in=${u2.input_tokens ?? "?"} · out=${u2.output_tokens ?? "?"} · search=${u2.server_tool_use?.tool_search ?? 0} · fetch=${u2.server_tool_use?.tool_fetch ?? 0}${esc(detail)}`));
            showRaw(rawEvents.slice(-40));
          } else if (t === "error") {
            wrap.appendChild(el("div", "err", esc(JSON.stringify(data.error))));
          }
        });
        showRaw(rawEvents.slice(-40));
        return;
      }

      // 非流式的另外两种协议
      const body = { model: MODEL };
      if (v.protocol === "responses") {
        body.input = v.prompt;
        body.reasoning = { effort: v.thinking === "enabled" ? "high" : "low" };
        body.tools = tools.map((x) => ({ type: x.type }));
        if (v.safety) body.safety_check = { level: "high" };
        if (v.title) body.title = { enabled: true };
      } else {
        body.messages = [];
        if (v.reminder) body.messages.push({ role: "latest_reminder", content: reminderLine() });
        body.messages.push({ role: "user", content: v.prompt });
        body.thinking = { type: v.thinking };
        body.tools = tools.map((x) => ({ type: x.type }));
        if (v.safety) body.safety_check = { level: "high" };
        if (v.title) body.title = { enabled: true };
      }
      showRequest(body);
      reset();
      const path = v.protocol === "responses" ? "/responses" : "/chat/completions";
      const res = await request(path, { body, bearer: true });
      const data = await res.json();
      if (!res.ok) throw new Error(`HTTP ${res.status}\n${JSON.stringify(data, null, 2)}`);
      renderBox.replaceChildren();
      if (v.protocol === "responses") renderResponses(renderBox, data);
      else renderChat(renderBox, data);
      showRaw(data);
    },
  },

  {
    id: "multiturn",
    group: "对话",
    title: "多轮与 signature",
    desc: "第一轮读你给的链接，第二轮追问并要求引用原文。把 assistant 的 content 原样回传，网页才能留在上下文里。",
    fields: [
      { id: "url", type: "text", label: "第一轮要读的链接", value: "https://api-docs.deepseek.com/zh-cn/news/news261113/" },
      { id: "q1", type: "text", label: "第一轮问题", value: "用一句话总结这个页面。" },
      { id: "q2", type: "text", label: "第二轮问题", value: "原样引用这个页面的第一句话。" },
    ],
    async run(v) {
      const history = [{ role: "user", content: `${v.q1}\n${v.url}` }];
      const body1 = { model: MODEL, thinking: { type: "disabled" }, tools: [{ type: "deepseek_read_url", name: "deepseek_read_url" }], messages: history };
      showRequest(body1);
      reset();
      const res1 = await request("/anthropic/v1/messages", { body: body1 });
      const d1 = await res1.json();
      if (!res1.ok) throw new Error(`HTTP ${res1.status}\n${JSON.stringify(d1, null, 2)}`);
      renderBox.appendChild(el("div", "meta", "— 第一轮 —"));
      renderMessagesBlocks(renderBox, d1.content || []);
      const sig = (d1.content || []).find((b) => b.signature);
      renderBox.appendChild(el("div", "meta", sig ? `signature 已拿到（${sig.signature.length} 字符），下一轮原样回传` : "本轮没有 read_link signature"));

      history.push({ role: "assistant", content: d1.content });
      history.push({ role: "user", content: v.q2 });
      const body2 = { model: MODEL, thinking: { type: "disabled" }, tools: [{ type: "deepseek_read_url", name: "deepseek_read_url" }], messages: history };
      const res2 = await request("/anthropic/v1/messages", { body: body2 });
      const d2 = await res2.json();
      showRaw({ round1: d1, round2: d2, messagesSentRound2: history });
      if (!res2.ok) throw new Error(`HTTP ${res2.status}\n${JSON.stringify(d2, null, 2)}`);
      renderBox.appendChild(el("div", "meta", "— 第二轮（带上一轮 content）—"));
      renderMessagesBlocks(renderBox, d2.content || []);
    },
  },

  {
    id: "search",
    group: "工具 API",
    title: "Search API",
    desc: "DeepSeek 自研搜索引擎。支持 site: / -site: / \"短语\" / lang: / after: / before: 等语法，5 元/千次。",
    fields: [
      { id: "query", type: "text", label: "query", value: "DeepSeek 全家桶应用 API 发布" },
      { id: "count", type: "text", label: "count（1-50）", value: "5" },
      { id: "ori", type: "text", label: "ori_question（可选）", value: "DeepSeek 最近开放了什么" },
      { id: "content", type: "checks", items: [{ id: "need_content", label: "need_content（返回正文，更贵）", value: false }] },
    ],
    async run(v) {
      const body = { query: v.query, count: Number(v.count) || 10, need_content: !!v.need_content };
      if (v.ori) body.ori_question = v.ori;
      showRequest(body);
      reset();
      const res = await request("/v1/tools/search", { body, bearer: true });
      const data = await res.json();
      if (!res.ok) throw new Error(`HTTP ${res.status}\n${JSON.stringify(data, null, 2)}`);
      const wrap = el("div", "turn");
      (data.results || []).forEach((r) => {
        wrap.appendChild(el("div", "result", `
          <span class="fav">${esc((r.site_name || hostOf(r.url))[0] || "?")}</span>
          <span><span class="t">${esc(r.title)}</span><span class="u">${esc(r.url)}</span>
          <span class="sn">${esc(r.snippet || "")}</span>
          <span class="u">rerank ${r.rerank_score?.toFixed?.(2) ?? r.rerank_score} · authority ${r.authority ?? "-"} · ${esc(r.date || "")}</span></span>`));
      });
      if (!data.results?.length) wrap.appendChild(el("div", "empty", "没有结果（可能语法叠加过紧，换个 query 试试）"));
      renderBox.appendChild(wrap);
      showRaw(data);
    },
  },

  {
    id: "fetch",
    group: "工具 API",
    title: "Fetch API",
    desc: "抓单个网页，返回 Markdown。5 元/千次；403 被安全策略拒、404 拿不到内容。",
    fields: [{ id: "url", type: "text", label: "url", value: "https://api-docs.deepseek.com/zh-cn/guides/web_tools" }],
    async run(v) {
      const body = { url: v.url };
      showRequest(body);
      reset();
      const res = await request("/v1/tools/fetch", { body, bearer: true });
      const data = await res.json();
      if (!res.ok) throw new Error(`HTTP ${res.status}\n${JSON.stringify(data, null, 2)}`);
      renderBox.appendChild(el("div", "block", `<div class="head">${esc(data.title || "(无标题)")}</div>
        <pre style="margin:0;border:0;border-radius:0">${esc((data.content || "").slice(0, 4000))}</pre>`));
      showRaw(data);
    },
  },

  {
    id: "file",
    group: "工具 API",
    title: "文件输入",
    desc: "上传文档（PDF/Word/PPT/图片）→ 拿 file_id → 在对话里引用。purpose=rich_layout_recognition 会把文档里的图也交给模型。",
    fields: [
      { id: "file", type: "file", label: "文件", accept: ".pdf,.doc,.docx,.ppt,.pptx,.png,.jpg,.jpeg,.webp,.gif,.bmp,.tif,.tiff,.txt,.md,.csv,.json" },
      { id: "purpose", type: "select", label: "purpose", options: [["rich_layout_recognition", "rich_layout_recognition（含图）"], ["text_recognition", "text_recognition（纯文字）"], ["user_data", "user_data（纯文本/表格，不计费）"]] },
      { id: "q", type: "text", label: "问题", value: "用要点总结这份文档，并列出三个关键数字。" },
    ],
    async run(v) {
      if (!v.file) throw new Error("先选一个文件");
      const fd = new FormData();
      fd.append("purpose", v.purpose);   // 顺序重要：purpose 必须在 file 之前
      fd.append("file", v.file);
      const res = await request("/files", { body: fd, raw: true, bearer: true });
      const up = await res.json();
      showRequest({ upload: { purpose: v.purpose, filename: v.file.name, size: v.file.size }, uploadResponse: up });
      if (!res.ok) throw new Error(`上传失败 HTTP ${res.status}\n${JSON.stringify(up, null, 2)}`);

      const body = {
        model: MODEL,
        messages: [{ role: "user", content: [{ type: "document", source: { type: "file", file_id: up.id } }, { type: "text", text: v.q }] }],
      };
      reset();
      const r2 = await request("/anthropic/v1/messages", { body, extraHeaders: { "anthropic-beta": "files-api-2025-04-14" } });
      const d2 = await r2.json();
      if (!r2.ok) throw new Error(`HTTP ${r2.status}\n${JSON.stringify(d2, null, 2)}`);
      renderMessagesBlocks(renderBox, d2.content || [], { question: v.q });
      showRaw({ upload: up, answer: d2 });
    },
  },

  {
    id: "ocr",
    group: "工具 API",
    title: "OCR",
    desc: "PDF / Word / PPT / 图片按页识别，保留 <|ref|>/<|box|> 与表格结构。1.5 元/千页。",
    fields: [
      { id: "file", type: "file", label: "文件", accept: ".pdf,.doc,.docx,.ppt,.pptx,.png,.jpg,.jpeg,.webp,.gif,.bmp,.tif,.tiff" },
      { id: "purpose", type: "select", label: "purpose", options: [["rich_layout_recognition", "rich_layout_recognition"], ["text_recognition", "text_recognition"]] },
    ],
    async run(v) {
      if (!v.file) throw new Error("先选一个文件");
      const fd = new FormData();
      fd.append("purpose", v.purpose);
      fd.append("file", v.file);
      showRequest({ multipart: { purpose: v.purpose, filename: v.file.name, size: v.file.size } });
      reset();
      const res = await request("/v1/tools/ocr", { body: fd, raw: true, bearer: true });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch { throw new Error(`HTTP ${res.status}\n${text.slice(0, 800)}`); }
      if (!res.ok || data.error) throw new Error(`HTTP ${res.status}\n${JSON.stringify(data.error || data, null, 2)}`);
      const wrap = el("div", "turn");
      wrap.appendChild(el("div", "meta", `page_count=${data.page_count} · usage=${JSON.stringify(data.usage)}`));
      for (const p of data.pages || []) {
        wrap.appendChild(el("div", "block", `<div class="head">page ${p.index} · finish=${esc(p.finish_reason)}</div>
          <pre style="margin:0;border:0;max-height:260px">${esc(p.text)}</pre>`));
      }
      renderBox.appendChild(wrap);
      showRaw(data);
    },
  },

  {
    id: "tts",
    group: "工具 API",
    title: "TTS",
    desc: "整段合成，音频在响应体里流式返回。汉字算 2 个计费字符；1.5 元/万字符（限时 5 折）。",
    fields: [
      { id: "text", type: "textarea", label: "文本", value: "你好，我是 DeepSeek。这段语音由浏览器的语音合成接口实时生成。" },
      { id: "voice", type: "select", label: "音色", options: [["stella", "stella（女声）"], ["tide", "tide（男声）"]] },
      { id: "format", type: "select", label: "格式", options: [["wav", "wav"], ["pcm", "pcm（24kHz 16bit 单声道）"]] },
    ],
    async run(v) {
      const body = { text: v.text, voice_id: v.voice, format: v.format, filter_markdown: true };
      showRequest(body);
      reset();
      const res = await request("/v1/tools/tts", { body, bearer: true });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}\n${t.slice(0, 800)}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const wrap = el("div", "turn");
      wrap.appendChild(el("div", "meta", `${blob.size} 字节 · ${blob.type || v.format}`));
      if (v.format === "wav") {
        const audio = el("audio", "audio");
        audio.controls = true;
        audio.src = url;
        wrap.appendChild(audio);
      }
      const dl = el("a", "btn primary", "下载音频");
      dl.href = url;
      dl.download = `speech.${v.format}`;
      dl.style.display = "inline-block";
      dl.style.marginTop = "10px";
      dl.style.textDecoration = "none";
      wrap.appendChild(dl);
      renderBox.appendChild(wrap);
      showRaw({ size: blob.size, type: blob.type });
    },
  },

  {
    id: "asr",
    group: "工具 API",
    title: "ASR",
    desc: "整段识别，16bit PCM WAV 或 Ogg Opus，≤8 MiB、≤120 秒、双声道只认左声道。0.39 元/小时。",
    fields: [{ id: "file", type: "file", label: "音频", accept: "audio/wav,audio/x-wav,audio/ogg,.wav,.ogg,.opus" }],
    async run(v) {
      if (!v.file) throw new Error("先选一个音频文件");
      const fd = new FormData();
      fd.append("file", v.file);
      showRequest({ multipart: { filename: v.file.name, size: v.file.size } });
      reset();
      const res = await request("/v1/tools/asr", { body: fd, raw: true, bearer: true });
      const data = await res.json();
      if (!res.ok) throw new Error(`HTTP ${res.status}\n${JSON.stringify(data, null, 2)}`);
      renderBox.appendChild(el("div", "block", `<div class="head">转写 · ${esc(data.duration_ms)} ms</div>
        <div style="padding:12px 14px">${esc(data.text)}</div>`));
      showRaw(data);
    },
  },
];

/* ------------------------------------------------------------------ 表单 */

let current = caps[0];

function buildForm(cap) {
  const form = $("#form");
  form.replaceChildren();
  for (const f of cap.fields) {
    if (f.type === "checks") {
      const box = el("div", "checks");
      for (const it of f.items) {
        const label = el("label");
        const input = el("input");
        input.type = "checkbox";
        input.id = `f-${it.id}`;
        input.checked = !!it.value;
        label.append(input, document.createTextNode(" " + it.label));
        box.appendChild(label);
      }
      form.appendChild(box);
    } else if (f.type === "file") {
      const wrap = el("div", "field");
      wrap.appendChild(el("label", null, esc(f.label)));
      const input = el("input");
      input.type = "file";
      input.id = `f-${f.id}`;
      if (f.accept) input.accept = f.accept;
      input.className = "filebox";
      wrap.appendChild(input);
      form.appendChild(wrap);
    } else if (f.type === "select") {
      const wrap = el("div", "field");
      wrap.appendChild(el("label", null, esc(f.label)));
      const sel = el("select");
      sel.id = `f-${f.id}`;
      for (const [val, text] of f.options) {
        const o = el("option", null, esc(text));
        o.value = val;
        if (f.value === val) o.selected = true;
        sel.appendChild(o);
      }
      wrap.appendChild(sel);
      form.appendChild(wrap);
    } else if (f.type === "textarea") {
      const wrap = el("div", "field");
      wrap.appendChild(el("label", null, esc(f.label)));
      const ta = el("textarea", f.mono ? "mono" : "");
      ta.id = `f-${f.id}`;
      ta.value = f.value || "";
      wrap.appendChild(ta);
      form.appendChild(wrap);
    } else {
      const wrap = el("div", "field");
      wrap.appendChild(el("label", null, esc(f.label)));
      const input = el("input");
      input.type = "text";
      input.id = `f-${f.id}`;
      input.value = f.value || "";
      wrap.appendChild(input);
      form.appendChild(wrap);
    }
  }
}

function readValues(cap) {
  const v = {};
  for (const f of cap.fields) {
    if (f.type === "checks") {
      for (const it of f.items) v[it.id] = document.getElementById(`f-${it.id}`)?.checked;
    } else {
      const input = document.getElementById(`f-${f.id}`);
      v[f.id] = f.type === "file" ? input?.files?.[0] : input?.value;
    }
  }
  return v;
}

function selectCap(cap) {
  current = cap;
  for (const b of document.querySelectorAll(".caps button")) b.classList.toggle("active", b.dataset.id === cap.id);
  $("#capTitle").textContent = cap.title;
  $("#capDesc").textContent = cap.desc;
  buildForm(cap);
  $("#status").textContent = "";
  $("#cost").textContent = "";
  reset();
  setTab("render");
}

function buildNav() {
  const nav = $("#caps");
  nav.replaceChildren();
  const groups = [...new Set(caps.map((c) => c.group))];
  for (const g of groups) {
    nav.appendChild(el("div", "group", esc(g)));
    for (const cap of caps.filter((c) => c.group === g)) {
      const b = el("button", null, `<span class="dot"></span>${esc(cap.title)}`);
      b.dataset.id = cap.id;
      b.onclick = () => selectCap(cap);
      nav.appendChild(b);
    }
  }
}

/* ------------------------------------------------------------------ 运行 */

async function run() {
  const btn = $("#run");
  const status = $("#status");
  btn.disabled = true;
  status.textContent = "运行中…";
  const t0 = performance.now();
  try {
    await current.run(readValues(current));
    status.textContent = `${(performance.now() - t0).toFixed(0)} ms · 已完成（真实计费）`;
    status.style.color = "var(--green)";
  } catch (e) {
    status.textContent = `${(performance.now() - t0).toFixed(0)} ms · 失败`;
    status.style.color = "var(--red)";
    const box = el("div", "err", esc(e.message || String(e)));
    renderBox.replaceChildren(box);
    setTab("render");
  } finally {
    btn.disabled = false;
  }
}

/* ------------------------------------------------------------------ 启动 */

$("#saveKey").onclick = () => {
  const v = $("#key").value.trim();
  if (!v) return;
  localStorage.setItem(LS_KEY, v);
  setKeyState();
};
$("#clearKey").onclick = () => {
  localStorage.removeItem(LS_KEY);
  $("#key").value = "";
  setKeyState();
};
$("#key").value = getKey();
$("#key").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#saveKey").click(); });
$("#run").onclick = run;
for (const b of document.querySelectorAll(".tab")) b.onclick = () => setTab(b.dataset.tab);

setKeyState();
buildNav();
selectCap(caps[0]);
