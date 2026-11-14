"""09 OCR：把 PDF / Word / PPT / 图片按页识别成文字

POST /v1/tools/ocr，multipart：file + purpose
- text_recognition：无图 Word/PPT 直接提取文字，其他文件逐页识别
- rich_layout_recognition：所有文件逐页识别，输出带 <|ref|>/<|box|> 标记与坐标
计费 1.5 元/千页，按 page_count 计；识别失败或超时不计费。
跑法：python 09_ocr.py 文件.pdf [--dry-run]
"""

import json
import pathlib
import sys

from common import dumps, post_multipart


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("用法：python 09_ocr.py <文件路径>")
    path = pathlib.Path(args[0]).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"文件不存在：{path}")

    with path.open("rb") as fh:
        resp = post_multipart(
            "/v1/tools/ocr",
            {"purpose": "rich_layout_recognition"},
            {"file": (path.name, fh)},
        )

    # 识别期间服务端持续发换行符保活，整个响应体可以直接按 JSON 解析
    data = json.loads(resp.text)

    if "error" in data:
        print("[error]", dumps(data["error"]))
        return

    print(f"[ocr] id={data['id']} page_count={data['page_count']} usage={dumps(data['usage'])}")
    parts = []
    for page in data["pages"]:
        flag = "（被截断，finish_reason=length）" if page.get("finish_reason") == "length" else ""
        print(f"\n--- page {page['index']}{flag} ---")
        print(page["text"][:400])
        parts.append(f"## page {page['index']}\n\n{page['text']}")

    out = pathlib.Path("ocr.md")
    out.write_text("\n\n".join(parts), encoding="utf-8")
    print(f"\n写入 {out.resolve()}")
    print("\n坐标解读：<|box|>[[x1,y1,x2,y2]]<|/box|>，原点左上角，归一化到 0-1000；")
    print("         实际像素 x = x * 页面宽度 / 1000，可用于自己裁图。")


if __name__ == "__main__":
    main()
