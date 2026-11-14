"""02 深度思考搜索（开启思考）

同一个 deepseek_web_search 工具，开了思考就变成"边推理边检索"：
search → open_page → find_in_page 多步循环，最多约 20 次工具调用。
跑法：python 02_deep_thinking_search.py [--dry-run] [--show-thinking]
"""

from common import MODEL, stream_messages

payload = {
    "model": MODEL,
    "thinking": {"type": "enabled"},
    "tools": [{"type": "deepseek_web_search", "name": "deepseek_web_search"}],
    "messages": [
        {
            "role": "user",
            "content": "埃菲尔铁塔和东京塔哪个更高？请查两边的官方网站确认。",
        }
    ],
}

result = stream_messages(payload)

print("\n\n==== 工具链路 ====")
for i, call in enumerate(result["calls"], 1):
    print(f"{i:>2}. {call.get('input', {}).get('action'):<12} kind={call.get('kind'):<12} "
          f"{call.get('input', {}).get('queries') or call.get('input', {}).get('url') or call.get('input', {}).get('pattern')}")
print("引用条数:", len(result["citations"]))
