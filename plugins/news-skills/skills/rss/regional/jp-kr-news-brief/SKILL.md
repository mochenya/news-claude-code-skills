---
name: jp-kr-news-brief
description: >-
  Use when the user asks for recent Japan and/or South Korea news or a
  time-windowed JP-KR political-economy brief, including midday, overnight,
  market-hours, and post-close reports, even if RSS is not mentioned. The main
  workflow is mandatory Beijing-time --since/--until filtering followed by the
  Chinese layout contract in references/output-format.md. Triggers include
  日韩新闻、日本新闻、韩国新闻、日韩政经简报、午间日韩、日韩收盘简报. Do not load for
  general web search, non-JP/KR topics, a single fact/article search,
  entertainment/sports, or standalone live-quote requests.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [news, japan, korea, rss, briefing, markets]
    related_skills: [rss-fetcher, news-briefing]
---

# 日本·韩国新闻简报

## 目标与定位

把指定北京时间窗口内的日本、韩国新闻候选集加工成可直接阅读的中文简报。主流程只关注两件事：

1. 用 `--since/--until` 准确取得目标时间窗新闻。
2. 严格按独立排版规范完成筛选、合并和成稿。

底层使用本 Skill 已配置的 RSS 源，正常执行不需要选择或分析具体数据源。只有排查覆盖缺口或维护 feed 时才查看源说明。

## 触发边界

### 使用本 Skill

- “日韩新闻”“日本／韩国最近有什么重要动态”
- 日本、韩国或日韩联合政治经济简报
- 午间、盘中、隔夜、收盘或收盘后的日韩简报
- 日本央行、韩国央行、财政、汇率、贸易、产业链、科技制造、能源或区域安全的窗口新闻汇总

### 不使用本 Skill

- 针对单一人物、事件、网页或事实的定向搜索
- 单独查询指数、个股、汇率或利率的实时数值
- 非日韩地区新闻，以及体育、娱乐、文化和一般社会资讯
- 通用网页搜索

判断边界：**宽口径获取近期日韩新闻时加载；窄口径查一个事实或网页时不加载。**

## 标准执行路径

### 1. 明确时间窗口

将用户要求转换为带 `+08:00` 的 ISO 8601 北京时间：

```text
START=窗口起点（包含）
END=窗口终点（不包含）
语义：[START, END)
```

开始抓取前确认 `START < END`。没有明确时间窗时，依据请求类型采用合理的最近窗口，并在成稿头部写清起止时间。

### 2. 运行唯一常用命令

```bash
SKILL_DIR="/home/lht/.hermes/profiles/global-politics-reporter/skills/news-skills/jp-kr-news-brief"
START="2026-07-16T08:00:00+08:00"
END="2026-07-16T12:00:00+08:00"

uv run --directory "$SKILL_DIR" jpkr fetch --all \
  --since "$START" \
  --until "$END" \
  -f json
```

执行约束：

- `--since`、`--until` 必须同时提供。
- 正式简报不使用 `-l/--limit`，避免先截断 feed 再过滤造成漏报。
- 始终使用 `--all` 和 JSON 输出，不用单源结果代替完整候选集。
- CLI 按 `[START, END)` 过滤；成稿前仍复核每条 `published_bjt`。

### 3. 筛选、合并与补全

对窗口内候选集执行：

1. 剔除跑题、低价值、旧闻回顾和无实质增量内容。
2. 将同一事件的多源报道合并为一条，保留有效来源链接。
3. 标题或摘要不足以支撑事实与影响时，使用 `web_extract` 补全；无法核实则剔除。
4. 按政策、市场和产业影响排序，不按发布时间机械排列。

遇到重复密集、边界新闻或标题型条目时，再读取 `references/filtering-notes.md`；正常窗口无需加载数据源细节。

### 4. 按排版规范成稿

起草前必须完整读取：

`references/output-format.md`

它是唯一成稿标准，包含：

- 中文标题、摘要和来源格式
- 动态板块与重要性排序
- 午间／盘中／收盘市场分析板块
- 潜在海外投资观察
- 零条目窗口模板
- 输出前检查清单

模式选择：

- 一般日韩新闻请求：标准政经简报。
- 用户明确提出午间、盘中、收盘、收盘后或市场分析：增加 `📊 股市与市场表现` 板块，并补充可核验行情数据。

最终响应只输出简报正文，不输出抓取、筛选或排版过程。

## References

| 文件 | 何时读取 |
|---|---|
| `references/output-format.md` | **每次成稿前必读**；唯一排版与输出标准 |
| `references/filtering-notes.md` | 重复密集、相关性存疑、摘要不足时读取 |
| `references/source-discovery.md` | 仅在源失效、覆盖缺口或调整 feed 时读取 |

## 完成检查

- [ ] 已明确北京时间 `[START, END)`
- [ ] 已使用 `--all --since --until -f json`，且未使用 `--limit`
- [ ] 成稿新闻全部位于目标窗口内
- [ ] 重复、跑题和低价值内容已经清除
- [ ] 已完整读取并执行 `references/output-format.md`
- [ ] 午间／收盘模式的行情时点与来源可核验
- [ ] 最终只输出中文简报正文
