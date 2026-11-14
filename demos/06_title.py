"""06 会话标题（title）

"title": {"enabled": true} → 回答顺带生成一个短标题，不额外请求、不计费。
位置：Messages 流式在 message_delta.delta.title；非流式在顶层 title。
   Responses 在 response.title；Chat Completions 在 delta.title / message.title。
建议只在会话第一条请求上开，拿到标题后关掉；可能缺省（拒答/出错），要兜底。
跑法：python 06_title.py [--dry-run]
"""

from common import MODEL, stream_messages

payload = {
    "model": MODEL,
    "tools": [{"type": "deepseek_web_search", "name": "deepseek_web_search"}],
    "title": {"enabled": True},
    "messages": [{"role": "user", "content": "北京明天会下雨吗？需要带伞吗？"}],
}

result = stream_messages(payload)

title = result["title"]
print("\n\n[title]", repr(title))
if not title:
    print("→ 没拿到标题，兜底：取用户消息前 20 个字符")

print("\n要点：")
print("- 回答结束后最多等标题 5 秒，响应才结束")
print("- 标题不计费；拒答或出错时可能没有")
