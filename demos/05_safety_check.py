"""05 模型内容安全（safety_check）

"safety_check": {"level": "high"} → 服务端审输入输出，命中风险返回拒答标识。
- Messages: stop_reason="refusal"，stop_details 说明类别
- Responses: status="incomplete", incomplete_details.reason="content_filter"
- Chat Completions: finish_reason="content_filter"，content 为空
拒答发生时：思考与回答文本被清空、已流式下发的文本无法撤回，前端要整段替换成自己的兜底文案。
跑法：python 05_safety_check.py [--dry-run]
"""

from common import MODEL, dumps, messages

payload = {
    "model": MODEL,
    "safety_check": {"level": "high"},
    "title": {"enabled": True},
    "messages": [{"role": "user", "content": "用一句话解释上下文缓存是什么。"}],
}

data = messages(payload).json()

text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
print("[answer]", text)
print("[stop_reason]", data.get("stop_reason"), "| stop_details:", dumps(data.get("stop_details")))
if data.get("stop_reason") == "refusal":
    print("→ 命中拒答：丢掉上面所有内容，展示你自己的拒答文案")

usage = data.get("usage") or {}
print("[usage]", dumps(usage))
print("\n要点：")
print("- 审核 Token 按输出 Token 计费，单独列在 usage.output_tokens_details.safety_tokens")
print("- 输入命中审核时直接 HTTP 400 Content Exists Risk，输入 Token 仍按缓存命中价计费")
print("- level 只能是 low / high；low 等于不传（API 默认检查）")
print("- 对外提供服务必须开 high，并自行完成内容审核、大模型登记、AI 标识")
