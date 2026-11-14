# DeepSeek Full-Suite App API · Tutorial & Demos

**中文** | [English](README.en.md)

DeepSeek 在 2026/11/13 把自家 App 的能力全部开成了 API：联网搜索、深度思考搜索、文件输入、阅读链接、模型内容安全、会话标题，外加独立的 OCR / ASR / TTS / Search / Fetch。这个仓库把它们逐个拆开，写成**可直接运行的 demo**，并整理成一份讲清「怎么用 + 什么时候会踩坑」的教程。

- 📖 教程正文：[docs/TUTORIAL.md](docs/TUTORIAL.md)
- 🖥 渲染效果演示页：[jimmywangjimmy.github.io/deepseek-app-api-tutorial](https://jimmywangjimmy.github.io/deepseek-app-api-tutorial/)
- 🧪 14 个可运行脚本：[demos/](demos/)
- 官方发布说明：[api-docs.deepseek.com/news/news261113](https://api-docs.deepseek.com/news/news261113/)

![渲染效果预览](https://jimmywangjimmy.github.io/deepseek-app-api-tutorial/preview.png)

> 上图是 `site/index.html` 渲染的一次完整回答：`thinking` 折叠面板 → 搜索卡片（2 个查询词）→ 读链卡片（`signature ✓`）→ 带引用角标的回答 → `usage`。演示页用示例数据静态渲染，不发起真实请求；真实调用见 [demos/](demos/)。

---

## 为什么值得看这份教程

这次发布真正改变的不是「多了几个功能」，而是**工具执行从客户端搬到了服务端**。你不再实现 `search()`，也不再自己把检索结果拼进 prompt——声明工具、服务端跑、你只渲染内容块。随之而来有一批反直觉的行为，官方文档分散在各页，这里集中讲清：

| 坑 | 说明 |
|---|---|
| **采样参数被接管** | 一旦声明 `deepseek_web_search` / `deepseek_read_url`、开 `safety_check: high` 或 `title`，`temperature`、`top_p`、`seed`、`stop` 等全部被服务端忽略 |
| **`max_tokens` 语义变了** | 它限制单步推理的输出，不是整轮总输出 |
| **网页正文不在响应里** | `read_link` 的正文加密在 `signature` 里，多轮必须原样回传，否则网页从上下文里消失 |
| **搜索是否发生不由你决定** | `tool_choice` 不能强制指定联网工具，`"none"` 会把读链一起关掉 |
| **200 也可能是失败** | 生成中途出错时 HTTP 已是 200，错误在响应体里，且失败前的搜索/抓取照常计费 |
| **中文 TTS 按双倍字符计费** | 汉字算 2 个计费字符，英文算 1 个 |

---

## 快速开始

```bash
git clone https://github.com/JimmyWangJimmy/deepseek-app-api-tutorial.git
cd deepseek-app-api-tutorial

python3 -m pip install -r demos/requirements.txt
export DEEPSEEK_API_KEY=sk-...          # https://platform.deepseek.com/

cd demos
python3 01_web_search.py --dry-run      # 不需要 key：只打印请求体，不发请求、不花钱
python3 01_web_search.py                # 真实调用（按次计费）
python3 12_full_chatbot.py              # 交互式完整 Chatbot
```

所有脚本都支持 `--dry-run`（脱敏打印 URL / headers / 请求体）与 `--show-thinking`（打印思考过程）。

---

## Demo 一览

| # | 脚本 | 演示的能力 | 你会看到什么 |
|---|---|---|---|
| 01 | [web_search](demos/01_web_search.py) | 联网搜索（关思考） | `server_tool_use` + `web_search_tool_result` + 引用 |
| 02 | [deep_thinking_search](demos/02_deep_thinking_search.py) | 深度思考搜索（开思考） | `search → open_page → find_in_page` 多步链路 |
| 03 | [read_url](demos/03_read_url.py) | 阅读链接 | `signature` 承载网页正文 |
| 04 | [file_input](demos/04_file_input.py) | 文件上传 + 引用 | `purpose` 顺序、文档解析、`file_id` 引用 |
| 05 | [safety_check](demos/05_safety_check.py) | 模型内容安全 | `refusal` / `safety_tokens` |
| 06 | [title](demos/06_title.py) | 会话标题 | `message_delta.delta.title` |
| 07 | [latest_reminder](demos/07_latest_reminder.py) | 用户元信息标记 | 日期 / 地点 / 语言注入 |
| 08 | [search_fetch](demos/08_search_fetch.py) | 独立 Search / Fetch | 搜索语法、`rerank_score` / `authority` |
| 09 | [ocr](demos/09_ocr.py) | OCR | 逐页文本、`<|box|>` 坐标 |
| 10 | [tts](demos/10_tts.py) | TTS 整段 + WebSocket 流式 | 音频文件、流式帧 |
| 11 | [asr](demos/11_asr.py) | ASR | 转写文本 + 时长 |
| 12 | [full_chatbot](demos/12_full_chatbot.py) | 全链路组合 | 搜索 + 读链 + 审核 + 标题 + TTS |
| 13 | [chat_completions](demos/13_chat_completions.py) | Chat Completions 写法 | `server_tool_calls` / `annotations` |
| 14 | [responses_api](demos/14_responses_api.py) | Responses 写法 | `web_search_call` item / `response.*` 事件 |

三协议差异（工具声明、引用、拒答、续写、`latest_reminder` 支持度）见教程 [§1.5](docs/TUTORIAL.md)。

---

## 教程目录

| 章节 | 内容 |
|---|---|
| §0 | 心智模型：服务端工具 vs 客户端工具，三协议对照 |
| §1 / §1.5 | 环境准备、同一件事在三种协议下的写法 |
| §2–§6 | 联网搜索、深度思考搜索、阅读链接、文件输入、图片搜索 |
| §7–§9 | 内容安全、会话标题、用户元信息标记 |
| §10–§13 | 独立 Search/Fetch、OCR、TTS、ASR |
| §14 | 拼一个完整 Chatbot（block → UI 映射） |
| §15–§17 | 多轮与 `signature`、被忽略的参数、错误与失败处理 |
| §18–§19 | 计费速查、落地检查清单 |

---

## 项目结构

```
.
├── README.md                 # 本文件
├── README.en.md              # English version
├── LICENSE                   # MIT
├── docs/
│   ├── TUTORIAL.md           # 完整教程（19 章）
│   ├── preview.png           # 渲染效果预览
│   └── pricing.png           # 官方定价表
├── demos/                    # 14 个可运行脚本 + common.py
├── examples/                 # --dry-run 的真实输出样例
└── site/index.html           # 静态渲染演示页（GitHub Pages）
```

`examples/` 里是 `--dry-run` 的真实捕获输出，可以直接看到每个请求长什么样，不消耗额度。

---

## 关于渲染演示页

`site/index.html` 是纯静态单文件，不依赖 CDN、不需要 key：把 `demos/` 里 `01 → 02 → 03` 的输出结构（thinking、搜索卡片、读链卡片、带引用正文、usage）用前端渲染出来，用来对齐「内容块 → UI」的映射。加 `#static` 后缀可关闭动画一次性渲染（截图用）。

想换成真实数据：跑 `demos/12_full_chatbot.py`，把返回的 `content` 数组按同样的 block 类型渲染即可。

---

## 计费提醒

这些能力在 token 费用之外**按次/按页/按时长另计**：搜索与抓取 5 元/千次、OCR 1.5 元/千页、ASR 0.39 元/小时、TTS 1.5 元/万字符（均为限时 5 折价）。跑 demo 前先用 `--dry-run` 确认请求，再小批量真实调用。

---

## License

[MIT](LICENSE) © 2026 Jiaming Wang

本仓库是第三方教程，与 DeepSeek 官方无隶属关系；API 行为以[官方文档](https://api-docs.deepseek.com/)为准。
