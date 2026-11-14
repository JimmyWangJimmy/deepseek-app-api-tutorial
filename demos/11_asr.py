"""11 语音识别（ASR）

POST /v1/tools/asr，multipart 的 file 字段带音频。一次整段识别，不支持流式。
要求：16 位 PCM WAV 或 Ogg Opus；单/双声道（双声道只认左声道）；<= 8 MiB；<= 120 秒。
计费 0.39 元/小时（限时 5 折），按秒计、不足 1 秒按 1 秒。
跑法：python 11_asr.py speech.wav [--dry-run]
"""

import pathlib
import sys

from common import dumps, post_multipart


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("用法：python 11_asr.py <音频文件>")
    path = pathlib.Path(args[0]).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"文件不存在：{path}")

    with path.open("rb") as fh:
        resp = post_multipart("/v1/tools/asr", {}, {"file": (path.name, fh)})
    data = resp.json()
    print("[asr]", dumps(data))
    print("\n转写结果:", data.get("text"))
    print(f"时长: {data.get('duration_ms')} ms")
    print("\n提示：语种自动识别，不需要传参数；超 120 秒要自己切片后逐段调用。")


if __name__ == "__main__":
    main()
