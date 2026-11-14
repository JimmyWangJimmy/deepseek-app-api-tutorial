"""04 文件输入：先上传解析，再在对话里引用 file_id

- PDF / Word / PPT / 图片：POST /files，purpose 选 text_recognition 或 rich_layout_recognition
  （后者会把文档里的图裁出来一起交给模型，占输入 Token）
- txt / md / csv / json / 代码 / xlsx / epub：purpose=user_data，直接转文本，不计费
- purpose 字段必须放在 file 字段之前（本脚本用有序 dict 保证顺序）
跑法：python 04_file_input.py 你的文件.pdf [--dry-run]
"""

import pathlib
import sys

from common import MODEL, dumps, messages, post_multipart

PARSED = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".webp",
          ".gif", ".bmp", ".tif", ".tiff"}


def upload(path: pathlib.Path) -> str:
    if path.suffix.lower() in PARSED:
        purpose = "rich_layout_recognition"  # 想让模型看到文中的图就选它
    else:
        purpose = "user_data"
    with path.open("rb") as fh:
        resp = post_multipart(
            "/files",
            {"purpose": purpose},                      # 顺序固定：purpose 在 file 前
            {"file": (path.name, fh)},
        )
    data = resp.json()
    print("[upload]", dumps(data))
    return data["id"]


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("用法：python 04_file_input.py <文件路径>")
    path = pathlib.Path(args[0]).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"文件不存在：{path}")

    file_id = upload(path)

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "document", "source": {"type": "file", "file_id": file_id}},
                    {"type": "text", "text": "用要点式总结这份文档，并列出三个关键数字。"},
                ],
            }
        ],
    }
    # Messages 引用文档必须带这个 beta 头
    resp = messages(payload, beta="files-api-2025-04-14")
    data = resp.json()
    for block in data.get("content", []):
        if block.get("type") == "text":
            print("\n[answer]", block["text"])
    print("\nusage:", dumps(data.get("usage")))


if __name__ == "__main__":
    main()
