"""14 Responses 协议下的全家桶

端点 POST /responses，Bearer 鉴权。差异点：
- 思考用 "reasoning": {"effort": "high"}
- 工具声明 {"type": "deepseek_web_search"}；tool_choice: "required" 按 auto 处理
- 输出是 item 列表：web_search_call（kind/action/sources/page/signature）、reasoning、message
- 引用是 output_text 上的 url_citation 注解（start_index/end_index 按 Unicode 码点计）
- 状态：completed / incomplete(max_output_tokens) / incomplete(content_filter)
- 不支持 previous_response_id、conversation、store，input 结尾不能是 assistant 消息
- 不支持 latest_reminder
跑法：python 14_responses_api.py [--dry-run]
"""

import json
import sys

from common import MODEL, responses, sse

payload = {
    "model": MODEL,
    "reasoning": {"effort": "high"},
    "tools": [
        {"type": "deepseek_web_search"},
        {"type": "deepseek_read_url"},
    ],
    "safety_check": {"level": "high"},
    "title": {"enabled": True},
    "input": "DeepSeek V4.1 有什么新功能？再总结一下 https://api-docs.deepseek.com/zh-cn/news/news261113/ 的重点。",
    "stream": True,
}

resp = responses(payload)

texts: list[str] = []
tool_items: list[dict] = []
for event, data in sse(resp):
    t = data.get("type") or event
    if t == "response.output_item.added":
        item = data.get("item") or {}
        if item.get("type") == "web_search_call":
            tool_items.append(item)
            print(f"\n[tool] kind={item.get('kind')} action={json.dumps(item.get('action'), ensure_ascii=False)[:200]}")
        elif item.get("type") == "message":
            print("\n[answer] ", end="")
    elif t == "response.output_item.done":
        item = data.get("item") or {}
        if item.get("type") == "web_search_call":
            if item.get("status") == "failed":
                print("  ! call failed", item.get("error"))
            else:
                page = item.get("page") or {}
                print(f"  · done {page.get('url') or ''} sig={'有' if item.get('signature') else '无'}")
    elif t == "response.output_text.delta":
        texts.append(data.get("delta", ""))
        sys.stdout.write(data.get("delta", ""))
        sys.stdout.flush()
    elif t == "response.output_text.annotation.added":
        ann = data.get("annotation") or {}
        print(f"\n  [cite] {ann.get('url')}")
    elif t == "response.completed":
        result = data.get("response") or {}
        print(f"\n[end] status={result.get('status')} title={result.get('title')!r}")
        print("usage:", json.dumps(result.get("usage"), ensure_ascii=False))
    elif t == "response.incomplete":
        result = data.get("response") or {}
        print(f"\n[incomplete] {json.dumps(result.get('incomplete_details'), ensure_ascii=False)}")
    elif t == "response.failed":
        result = data.get("response") or {}
        print(f"\n[failed] {json.dumps(result.get('error'), ensure_ascii=False)}")

print("\n\n==== 汇总 ====")
print("工具调用 item:", len(tool_items), [i.get("kind") for i in tool_items])
print("回答字符数:", len("".join(texts)))
print("\n多轮：把上一轮的 output item 原样放回 input，保留 kind 与 signature。")
