"""01 联网搜索（关闭思考）

开关：tools 里声明 deepseek_web_search，且不开启思考。
模型自己判断要不要搜、搜什么；搜完带引用作答。
跑法：python 01_web_search.py [--dry-run]
"""

from common import MODEL, stream_messages

payload = {
    "model": MODEL,
    # deepseek-flash 默认开启思考（不传 thinking = enabled），要真正的"联网搜索"必须显式关掉
    "thinking": {"type": "disabled"},
    "tools": [{"type": "deepseek_web_search", "name": "deepseek_web_search"}],
    "messages": [{"role": "user", "content": "DeepSeek V4.1 是什么时候发布的？有哪些新能力？"}],
}

result = stream_messages(payload)

print("\n\n==== 汇总 ====")
print("工具调用块:", len(result["calls"]), "→", [c.get("kind") for c in result["calls"]])
print("引用条数:", len(result["citations"]))
for c in result["citations"]:
    print(" -", c.get("url"))
print("回答:", result["text"][:200].replace("\n", " "), "...")
