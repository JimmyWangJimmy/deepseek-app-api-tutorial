"""08 独立 Search / Fetch API（不走对话模型）

Search: POST /v1/tools/search  —— DeepSeek 自研搜索引擎，返回结构化结果
Fetch:  POST /v1/tools/fetch   —— 单页抓取，返回 Markdown 正文
两者都是原始 JSON API、Bearer 鉴权，按成功请求次数计费（5 元/千次），
QPS：Search 100、Fetch 25（账号级，与模型并发无关）。
跑法：python 08_search_fetch.py [--dry-run]
"""

import pathlib

from common import dumps, post_json

# --- Search：支持 site: / -site: / "短语" / -词 / lang: / after: / before: 等语法
# 注意：语法叠加过多会把结果筛空（下面第二个查询就是反例），生产环境建议先跑朴素查询再逐步加条件
QUERIES = [
    "DeepSeek 全家桶应用 API 发布",                                  # 朴素查询
    "DeepSeek 模型 site:github.com OR site:huggingface.co lang:zh",   # 带语法
]

best = []
for query in QUERIES:
    search = post_json(
        "/v1/tools/search",
        {
            "query": query,
            "count": 5,
            "ori_question": "DeepSeek 最近开放了哪些应用能力？",  # 帮搜索引擎理解意图
            "need_content": False,                                  # True 才返回正文，更贵更慢
        },
    )
    results = search.get("results", [])
    print(f"[search] {query!r} → {len(results)} 条")
    for r in results:
        print(f"- rerank={r.get('rerank_score')} authority={r.get('authority')} "
              f"{r.get('title')}  ({r.get('site_name')})")
        print(f"  {r.get('url')}")
        print(f"  summary: {(r.get('summary') or '')[:110]}...")
    best = [r for r in results if (r.get("rerank_score") or 0) >= 1.5]
    if best:
        print(f"  → rerank_score >= 1.5 的优质结果 {len(best)} 条（authority >= 3 为极权威）")
        break
    print("  → 没有优质结果，换一个查询再试\n")

# --- Fetch：抓一页，落成 Markdown
if best:
    page = post_json("/v1/tools/fetch", {"url": best[0]["url"]})
    out = pathlib.Path("fetched.md")
    out.write_text(f"# {page.get('title', '')}\n\n{page.get('content', '')}", encoding="utf-8")
    print(f"\n[fetch] {best[0]['url']}")
    print(f"  title={page.get('title')!r}  markdown {len(page.get('content', ''))} 字符 → {out.resolve()}")

print("\n错误处理：408/429/5xx 可重试；400/401/403/404 不重试；402 先充值。")
print("计费：只有 HTTP 200 且有结果才算一次；count 不影响单价。")
print("\n响应字段速查：", dumps({"rerank_score": "0~3，>=1.5 优质", "authority": "0~4，>=3 极权威", "date": "UTC RFC3339 或 null"}))
