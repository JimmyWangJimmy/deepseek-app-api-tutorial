"""07 用户元信息标记（latest_reminder）

格式：<date>,<weekday>,<location>,<platform>,<language>
例：2026-11-10,星期二,新加坡,Web,中文
规则：
- role 用 "latest_reminder"，紧挨在它所属的 user 消息之前
- content 必须是字符串；后面必须紧跟 user 消息，不能夹在 tool_use / tool_result 之间
- Messages 与 Chat Completions 支持，Responses 不支持
- 每轮都带、并随历史回传，能提高上下文缓存命中率
跑法：python 07_latest_reminder.py [--dry-run]
"""

from datetime import datetime, timezone, timedelta

from common import MODEL, messages

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def reminder(now: datetime, location: str = "上海", platform: str = "Web", language: str = "中文") -> str:
    return f"{now:%Y-%m-%d},{WEEKDAYS[now.weekday()]},{location},{platform},{language}"


now = datetime.now(timezone(timedelta(hours=8)))
today = reminder(now)

payload = {
    "model": MODEL,
    "messages": [
        {"role": "latest_reminder", "content": today},
        {"role": "user", "content": "今天是几号？星期几？我需要知道该不该现在出门买明天的早饭。"},
    ],
}

data = messages(payload).json()
for block in data.get("content", []):
    if block.get("type") == "text":
        print("[answer]", block["text"])

print("\n注入的 reminder:", today)
print("要点：不要把日期写进 system prompt，模型对 latest_reminder 的日期更敏感；")
print("      多轮时每轮一条，并随历史一起回传。")
