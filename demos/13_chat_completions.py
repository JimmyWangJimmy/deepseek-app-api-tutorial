"""13 Chat Completions 协议下的全家桶（OpenAI 兼容写法）

同一批能力在 /chat/completions 上用扩展字段表达：
- 请求：tools 声明 {"type": "deepseek_web_search"}（不用 name），safety_check / title 放顶层
- 非流式输出：message.server_tool_calls（分步：每步的思考 + 该步发起的调用）、
  message.annotations（url_citation，start_index/end_index 按 Unicode 码点计）
- 流式输出：choice.server_tool_event（step_reasoning_done / call_started / call_completed），
  完整的 server_tool_calls + annotations 只在最后带 finish_reason 的 chunk 里给一次
- 结束：finish_reason = stop / length / content_filter
跑法：python 13_chat_completions.py [--dry-run] [--show-thinking]
"""

import json

from common import MODEL, stream_chat

payload = {
    "model": MODEL,
    "thinking": {"type": "enabled"},
    "tools": [
        {"type": "deepseek_web_search"},
        {"type": "deepseek_read_url"},
    ],
    "safety_check": {"level": "high"},
    "title": {"enabled": True},
    "messages": [
        {"role": "user", "content": "DeepSeek 全家桶 API 里，搜索和读链有什么区别？顺便看下 "
                                    "https://api-docs.deepseek.com/zh-cn/guides/web_tools 的说法。"}
    ],
}

result = stream_chat(payload)

print("\n\n==== 汇总 ====")
print("title:", result["title"])
for step in result["calls"]:
    print(f"- step {step.get('index')} reasoning={bool(step.get('reasoning_content'))}")
    for call in step.get("calls", []):
        print(f"    {call.get('kind'):<16} {json.dumps(call.get('action'), ensure_ascii=False)} "
              f"status={call.get('status')} signature={'有' if call.get('signature') else '无'}")
print("引用:", [a.get("url_citation", {}).get("url") for a in result["annotations"]])
print("\n注意：多轮时要把 server_tool_calls 连同 signature 原样回传，否则读过的网页不再进上下文。")
