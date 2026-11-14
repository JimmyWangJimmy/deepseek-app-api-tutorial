"""10 语音合成（TTS）

整段：POST /v1/tools/tts（JSON）→ 响应体流式返回音频
流式：WebSocket wss://api.deepseek.com/v1/tools/tts → 边生成边发文字，边收音频帧
计费 1.5 元/万字符（限时 5 折，刊例 3 元）；汉字算 2 字符，其他算 1。
跑法：python 10_tts.py [--ws] [--dry-run]
      --ws 需要 pip install "websockets>=14"
"""

import asyncio
import json
import pathlib
import sys

import requests

from common import BASE, api_key, dry_run

TEXT = "你好，我是 DeepSeek。这段语音由语音合成接口生成，可以直接用来朗读回答。"


def whole(text: str = TEXT, voice: str = "stella", fmt: str = "wav", out: str = "speech.wav") -> None:
    payload = {"text": text, "voice_id": voice, "format": fmt, "filter_markdown": True}
    if dry_run():
        print("[dry-run] POST", BASE + "/v1/tools/tts", json.dumps(payload, ensure_ascii=False))
        return
    resp = requests.post(
        BASE + "/v1/tools/tts",
        json=payload,
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"},
        stream=True,
        timeout=600,
    )
    if resp.status_code >= 400:
        raise SystemExit(f"HTTP {resp.status_code}\n{resp.text[:1000]}")
    path = pathlib.Path(out)
    size = 0
    with path.open("wb") as fh:
        for chunk in resp.iter_content(4096):
            fh.write(chunk)
            size += len(chunk)
    print(f"[tts] {size} 字节 → {path.resolve()}")
    print("音色：stella（女声，默认）/ tide（男声）；格式 wav / pcm（24kHz 16bit 单声道）")
    print("单次最多 30 分钟音频、10,000 计费字符、请求体 64 KiB；不支持调速与断点续传")


async def ws(text: str = TEXT, voice: str = "stella", fmt: str = "pcm", out: str = "speech.pcm") -> None:
    url = f"wss://{BASE.split('://', 1)[1]}/v1/tools/tts?voice_id={voice}&format={fmt}"
    headers = {"Authorization": f"Bearer {api_key()}"}
    if dry_run():
        print("[dry-run] WS", url, headers)
        return
    import websockets  # pip install "websockets>=14"
    async with websockets.connect(url, additional_headers=headers) as sock:
        for piece in [text[i:i + 20] for i in range(0, len(text), 20)]:
            await sock.send(json.dumps({"event": "text", "text": piece}))
        await sock.send(json.dumps({"event": "finish_text"}))
        path = pathlib.Path(out)
        frames = 0
        with path.open("wb") as fh:
            async for message in sock:
                if isinstance(message, bytes):
                    fh.write(message)   # 24kHz 16bit signed mono PCM
                    frames += 1
                    continue
                done = json.loads(message)
                if done.get("code") != "success":
                    raise RuntimeError(f"{done.get('code')}: {done.get('message')}")
                break
    print(f"[tts-ws] {frames} 个音频帧 → {path.resolve()}")
    print("限制：60 秒内无文字即断；单次会话最长 30 分钟 / 10,000 计费字符 / 64 KiB")


if __name__ == "__main__":
    if "--ws" in sys.argv[1:]:
        asyncio.run(ws())
    else:
        whole()
