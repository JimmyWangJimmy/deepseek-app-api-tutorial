"""DeepSeek 全家桶应用 API demo 公共模块。

只依赖 requests；TTS 流式 demo 另需 websockets。
用法：
    export DEEPSEEK_API_KEY=sk-...
    python 01_web_search.py            # 真调用
    python 01_web_search.py --dry-run  # 只打印请求体，不发请求、不花钱
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Iterator

import requests

BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
MODEL = "deepseek-flash"
TIMEOUT = 900


# ---------------------------------------------------------------- 基础工具

def dry_run() -> bool:
    return "--dry-run" in sys.argv[1:]


def api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        if dry_run():
            return "sk-dry-run-placeholder"   # dry-run 只打印请求，不校验 key
        raise SystemExit("缺少 DEEPSEEK_API_KEY，先执行：export DEEPSEEK_API_KEY=sk-...")
    return key


def flag(name: str) -> bool:
    return name in sys.argv[1:]


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def show(obj: Any, limit: int = 3000) -> None:
    text = dumps(obj)
    print(text if len(text) <= limit else text[:limit] + f"\n... (已截断，共 {len(text)} 字符)")


def _headers(bearer: bool, extra: dict[str, str] | None = None) -> dict[str, str]:
    key = api_key()
    h = {"Content-Type": "application/json"}
    h["Authorization" if bearer else "x-api-key"] = f"Bearer {key}" if bearer else key
    if extra:
        h.update(extra)
    return h


# ---------------------------------------------------------------- 协议封装

def messages(payload: dict, *, beta: str | None = None) -> requests.Response:
    """Anthropic 兼容协议：POST /anthropic/v1/messages，鉴权用 x-api-key。"""
    extra = {"anthropic-beta": beta} if beta else None
    return _post("/anthropic/v1/messages", payload, bearer=False, extra=extra)


def chat(payload: dict, *, beta: bool = False) -> requests.Response:
    """OpenAI 兼容协议：POST /chat/completions（续写走 /beta/chat/completions）。"""
    path = "/beta/chat/completions" if beta else "/chat/completions"
    return _post(path, payload, bearer=True)


def responses(payload: dict) -> requests.Response:
    """Responses 协议：POST /responses。"""
    return _post("/responses", payload, bearer=True)


def _post(
    path: str,
    payload: dict | None,
    *,
    bearer: bool,
    extra: dict[str, str] | None = None,
) -> requests.Response:
    url = BASE + path
    headers = _headers(bearer, extra)
    if dry_run():
        safe = {k: ("<redacted>" if k in ("Authorization", "x-api-key") else v) for k, v in headers.items()}
        print(f"[dry-run] POST {url}")
        print(f"[dry-run] headers: {safe}")
        print(dumps(payload))
        raise SystemExit(0)
    chunked = bool((payload or {}).get("stream"))
    resp = requests.post(url, json=payload, headers=headers, stream=chunked, timeout=TIMEOUT)
    if resp.status_code >= 400:
        raise SystemExit(f"HTTP {resp.status_code}\n{resp.text[:2000]}")
    return resp


def post_json(path: str, payload: dict, *, bearer: bool = True) -> dict:
    """给 /v1/tools/search、/v1/tools/fetch 这类独立工具 API 用。"""
    resp = _post(path, payload, bearer=bearer)
    return resp.json()


def post_multipart(path: str, fields: dict[str, str], files: dict[str, Any]) -> requests.Response:
    """给 Files / OCR / ASR 用。fields 的插入顺序就是表单顺序。"""
    url = BASE + path
    headers = {"Authorization": f"Bearer {api_key()}"}
    if dry_run():
        print(f"[dry-run] POST {url}")
        print(f"[dry-run] fields: {fields}")
        print(f"[dry-run] files: {list(files)}")
        raise SystemExit(0)
    resp = requests.post(url, data=fields, files=files, headers=headers, timeout=TIMEOUT)
    if resp.status_code >= 400:
        raise SystemExit(f"HTTP {resp.status_code}\n{resp.text[:2000]}")
    return resp


# ---------------------------------------------------------------- SSE 解析

def sse(resp: requests.Response) -> Iterator[tuple[str, dict]]:
    """解析 text/event-stream：产出 (event_name, data_dict)。

    Messages 协议带 event: 行；Chat Completions 只有 data: 行（含 [DONE]）；
    Responses 协议的 event 行就是事件名。注释行（: keep-alive）直接跳过。
    """
    event = ""
    # SSE 响应通常不带 charset，requests 会按 ISO-8859-1 解码成乱码；这里强制按 UTF-8
    resp.encoding = "utf-8"
    for chunk in resp.iter_lines():                     # bytes，自己解码
        if chunk is None:
            continue
        line = chunk.decode("utf-8", "replace").strip()
        if not line:
            event = ""
            continue
        if line.startswith(":"):
            continue  # keep-alive
        if line.startswith("event:"):
            event = line[len("event:"):].strip()
            continue
        if not line.startswith("data:"):
            continue
        data = line[len("data:"):].strip()
        if data == "[DONE]":
            yield "done", {"type": "done"}
            continue
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        yield event or obj.get("type", ""), obj


# ---------------------------------------------------------------- 流式打印

def stream_messages(payload: dict, *, beta: str | None = None) -> dict:
    """流式跑一次 Messages 请求，边打印块边收集结果。"""
    body = {**payload, "stream": True}
    resp = messages(body, beta=beta)
    texts: list[str] = []
    citations: list[dict] = []
    calls: list[dict] = []
    title = None
    for ev, data in sse(resp):
        t = data.get("type", ev)
        if t == "message_start":
            print(f"[start] usage={json.dumps(data['message'].get('usage'), ensure_ascii=False)}")
        elif t == "content_block_start":
            block = data["content_block"]
            bt = block.get("type")
            if bt == "thinking":
                print("[thinking] ...", end="")
            elif bt == "server_tool_use":
                calls.append(block)
                print(f"\n[tool] {block.get('name')} kind={block.get('kind')} "
                      f"input={json.dumps(block.get('input'), ensure_ascii=False)}")
            elif bt == "web_search_tool_result":
                for item in block.get("content") or []:
                    if item.get("type") == "web_search_result":
                        print(f"  · [{item.get('site_name')}] {item.get('title')}\n    {item.get('url')}")
                    else:
                        print(f"  ! search error: {item}")
            elif bt == "web_fetch_tool_result":
                c = block.get("content") or {}
                if c.get("type") == "web_fetch_result":
                    print(f"  · 抓到 {c.get('url')}  title={c['content'].get('title')!r}")
                else:
                    print(f"  ! fetch error: {c}")
            elif bt == "text":
                print("\n[answer] ", end="")
        elif t == "content_block_delta":
            d = data.get("delta") or {}
            if d.get("type") == "text_delta":
                sys.stdout.write(d.get("text", ""))
                sys.stdout.flush()
                texts.append(d.get("text", ""))
            elif d.get("type") == "thinking_delta" and flag("--show-thinking"):
                sys.stdout.write(d.get("thinking", ""))
            elif d.get("type") == "citations_delta":
                c = d.get("citation") or {}
                citations.append(c)
                print(f"\n  [cite] {c.get('title') or ''} {c.get('url')}")
        elif t == "message_delta":
            delta = data.get("delta") or {}
            title = delta.get("title")
            print(f"\n[end] stop_reason={delta.get('stop_reason')} title={title!r}")
            print("usage:", json.dumps(data.get("usage"), ensure_ascii=False))
        elif t == "error":
            print("\n[error]", json.dumps(data.get("error"), ensure_ascii=False))
    return {"text": "".join(texts), "citations": citations, "calls": calls, "title": title}


def stream_chat(payload: dict, *, beta: bool = False) -> dict:
    """流式跑一次 Chat Completions 请求。"""
    resp = chat({**payload, "stream": True}, beta=beta)
    texts: list[str] = []
    title = None
    final_calls: list[dict] = []
    final_annotations: list[dict] = []
    for ev, data in sse(resp):
        if data.get("type") == "done":
            break
        if data.get("error"):
            print("\n[error]", json.dumps(data["error"], ensure_ascii=False))
            break
        for choice in data.get("choices") or []:
            delta = choice.get("delta") or {}
            if delta.get("reasoning_content") and flag("--show-thinking"):
                sys.stdout.write(delta["reasoning_content"])
            if delta.get("content"):
                sys.stdout.write(delta["content"])
                sys.stdout.flush()
                texts.append(delta["content"])
            if delta.get("title"):
                title = delta["title"]
            evt = choice.get("server_tool_event")
            if evt:
                print(f"\n[tool-event] {evt.get('type')} step={evt.get('step')} "
                      f"call={json.dumps(evt.get('call', {}).get('action'), ensure_ascii=False)}")
            if choice.get("finish_reason"):
                final_calls = delta.get("server_tool_calls") or []
                final_annotations = delta.get("annotations") or []
                print(f"\n[end] finish_reason={choice['finish_reason']} title={title!r}")
        if data.get("usage"):
            print("usage:", json.dumps(data["usage"], ensure_ascii=False))
    return {"text": "".join(texts), "calls": final_calls, "annotations": final_annotations, "title": title}
