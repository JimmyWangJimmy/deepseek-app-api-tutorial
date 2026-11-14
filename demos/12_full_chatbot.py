"""12 拼一个完整的 Chatbot：日期标记 + 联网 + 读链 + 安全审核 + 标题 + 可选朗读

这个脚本把前 11 个 demo 串起来，演示官方 App 的最小骨架：
    输入 → latest_reminder → 模型（可能搜索/读页）→ 安全审核 → 渲染块 → （可选）TTS
关键点：多轮时必须把上一轮的 assistant content 原样回传，保留 kind 与 signature，
否则"读过的网页"在下一轮不再进入上下文。

跑法：python 12_full_chatbot.py [问题...] [--tts] [--dry-run]
      不带问题则进入交互模式（输入 exit 退出）
"""

import sys
from datetime import datetime, timedelta, timezone

from common import MODEL, dumps, messages

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


class Chatbot:
    def __init__(self, *, location: str = "上海", language: str = "中文", safety: bool = True) -> None:
        self.tools = [
            {"type": "deepseek_web_search", "name": "deepseek_web_search"},
            {"type": "deepseek_read_url", "name": "deepseek_read_url"},
        ]
        self.location = location
        self.language = language
        self.safety = safety
        self.history: list[dict] = []      # 不含 latest_reminder 的消息历史
        self.title: str | None = None
        self.turns = 0

    # ---------------------------------------------------------------- 内部

    def _reminder(self) -> str:
        now = datetime.now(timezone(timedelta(hours=8)))
        return f"{now:%Y-%m-%d},{WEEKDAYS[now.weekday()]},{self.location},Web,{self.language}"

    @staticmethod
    def _render(blocks: list[dict]) -> str:
        """把 assistant content 渲染成终端可读的样子，对应前端要做的 block 映射。"""
        answer: list[str] = []
        for block in blocks:
            kind = block.get("type")
            if kind == "thinking":
                print("  [thinking]（折叠面板，不展示内容）")
            elif kind == "server_tool_use":
                inp = block.get("input") or {}
                act = inp.get("action")
                detail = inp.get("queries") or inp.get("url") or inp.get("pattern")
                print(f"  [tool] {block.get('kind')}: {act} {detail}")
            elif kind == "web_search_tool_result":
                for item in block.get("content") or []:
                    if item.get("type") == "web_search_result":
                        print(f"    · {item.get('title')} — {item.get('site_name')} {item.get('url')}")
                    else:
                        print(f"    ! search error {item}")
            elif kind == "web_fetch_tool_result":
                c = block.get("content") or {}
                if c.get("type") == "web_fetch_result":
                    print(f"    · 读页 {c.get('url')}  title={c['content'].get('title')!r}")
                else:
                    print(f"    ! fetch error {c}")
            elif kind == "text":
                answer.append(block.get("text", ""))
                for cite in block.get("citations") or []:
                    print(f"    [cite] {cite.get('url')}")
        return "".join(answer)

    # ---------------------------------------------------------------- 对外

    def ask(self, text: str) -> str:
        msgs = [*self.history,
                {"role": "latest_reminder", "content": self._reminder()},
                {"role": "user", "content": text}]

        payload: dict = {"model": MODEL, "tools": self.tools, "messages": msgs}
        if self.safety:
            payload["safety_check"] = {"level": "high"}
        if self.turns == 0:
            payload["title"] = {"enabled": True}   # 只第一轮要标题

        data = messages(payload).json()

        if data.get("stop_reason") == "refusal":
            print("  [拒绝] 命中内容审核，刷新整条回复为兜底文案")
            return "抱歉，这个内容我无法回答。"

        title = data.get("title")
        if title:
            self.title = title

        blocks = data.get("content") or []
        answer = self._render(blocks)

        # 关键：原样回传，保留 kind / signature，网页才能在下一轮拼回上下文
        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": blocks})
        self.turns += 1

        usage = data.get("usage") or {}
        tool_use = usage.get("server_tool_use") or {}
        print(f"  [usage] in={usage.get('input_tokens')} out={usage.get('output_tokens')} "
              f"search={tool_use.get('tool_search')} fetch={tool_use.get('tool_fetch')}")
        return answer


def speak(text: str) -> None:
    """可选：把回答读出来，复用 10_tts.py 的整段合成逻辑。"""
    from common import BASE, api_key
    import pathlib
    import requests

    resp = requests.post(
        BASE + "/v1/tools/tts",
        json={"text": text[:2000], "voice_id": "stella", "format": "wav"},
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"},
        stream=True,
        timeout=600,
    )
    if resp.status_code >= 400:
        print("  [tts] 失败", resp.status_code, resp.text[:200])
        return
    out = pathlib.Path("answer.wav")
    with out.open("wb") as fh:
        for chunk in resp.iter_content(4096):
            fh.write(chunk)
    print(f"  [tts] 已生成 {out.resolve()}")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tts = "--tts" in sys.argv[1:]
    if not args and "--dry-run" in sys.argv[1:]:
        args = ["DeepSeek 全家桶 API 能做什么？"]   # dry-run 时跳过交互，直接演示一次请求
    bot = Chatbot()

    if args:
        question = " ".join(args)
        print(f"\n[user] {question}")
        answer = bot.ask(question)
        print(f"[answer] {answer}")
        if tts:
            speak(answer)
        print(f"\n[title] {bot.title!r}")
        return

    print("交互模式，输入 exit 退出。工具：搜索 + 读链 + 安全审核 + 标题。")
    while True:
        try:
            question = input("\n[user] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        answer = bot.ask(question)
        print(f"[answer] {answer}\n[title] {bot.title!r}")
        if tts:
            speak(answer)


if __name__ == "__main__":
    main()
