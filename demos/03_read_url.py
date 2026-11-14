"""03 阅读链接

只声明 deepseek_read_url：模型读取最后一条用户消息里的 URL（最多取前 10 个不同链接）。
关思考时才走 read_link；同时开思考和 deepseek_web_search 会走深度思考搜索。
跑法：python 03_read_url.py [URL ...] [--dry-run]
"""

import sys

from common import MODEL, stream_messages

urls = [a for a in sys.argv[1:] if not a.startswith("--")] or [
    "https://api-docs.deepseek.com/zh-cn/news/news261113/",
]

prompt = "请阅读下面的链接，用三句话总结它讲了什么，并说明对开发者最实际的一点：\n" + "\n".join(urls)

payload = {
    "model": MODEL,
    "tools": [{"type": "deepseek_read_url", "name": "deepseek_read_url"}],
    "messages": [{"role": "user", "content": prompt}],
}

result = stream_messages(payload)

print("\n\n==== 读了哪些页 ====")
for call in result["calls"]:
    print(f"- {call.get('input', {}).get('url')}  (kind={call.get('kind')})")
print("引用条数:", len(result["citations"]))
print("\n提示：多轮对话时要把带 signature 的结果块原样回传，网页正文才会拼回上下文。")
