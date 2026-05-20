# rss-fetcher

以 RSS 为核心的新闻抓取与 SQLite 查询工具，主打政治、政策、政府与地缘议题，也支持 AI 新闻。

用途：只做速查——看目录、看关键文件、看常用命令、看时间参数规则。

## 目录结构

```text
rss-fetcher/
├── README.md
├── SKILL.md
├── pyproject.toml
├── .python-version
├── uv.lock
├── references/
│   └── sources.md
├── scripts/
│   ├── cli/
│   │   ├── main.py
│   │   ├── rss_fetch.py
│   │   ├── news_fetch.py
│   │   ├── news_sync.py
│   │   └── news_query.py
│   ├── data/
│   │   ├── sources.json
│   │   └── news.db
│   └── lib/
│       ├── text_utils.py
│       ├── time_utils.py
│       ├── source_registry.py
│       ├── entry_utils.py
│       └── db.py
```

## 关键文件

- `scripts/data/sources.json`：来源配置真相，长期维护这里
- `scripts/data/news.db`：运行时 SQLite 数据库
- `scripts/cli/main.py`：统一命令入口，推荐配合 `uv run --directory {SKILL_DIR} news ...`
- `scripts/cli/rss_fetch.py`：单 RSS URL 抓取
- `scripts/cli/news_fetch.py`：按 category live fetch
- `scripts/cli/news_sync.py`：同步 sources.json 到 SQLite
- `scripts/cli/news_query.py`：从 SQLite 查询新闻
- `scripts/lib/`：共享逻辑与数据访问层

## 环境

- Python: `>=3.12`
- 依赖: `feedparser>=6.0.12`
- 安装：`uv sync --directory {SKILL_DIR}`
- 运行入口：`project.scripts` + `hatchling`，推荐 `uv run --directory {SKILL_DIR} news ...`

## sources.json 最小结构

```json
{
  "categories": [
    {
      "key": "middle-east",
      "name": "中东",
      "enabled": true,
      "order": 60,
      "sources": [
        {
          "key": "middle-east-al-jazeera",
          "name": "Al Jazeera",
          "url": "https://www.aljazeera.com/xml/rss/all.xml",
          "enabled": true
        }
      ]
    }
  ]
}
```

字段：`key` 稳定标识，`name` 展示名，`url` RSS 地址，`enabled` 开关，`order` 排序。

当前内置分类包含：`top`、`world`、`gov`、`politics`、`us`、`ai`、`middle-east`、`russia-ukraine`、`indonesia`、`japan`、`korea`。

## 常用命令

### 统一入口
```bash
uv run --directory {SKILL_DIR} news rss <rss_url>
uv run --directory {SKILL_DIR} news fetch <category>
uv run --directory {SKILL_DIR} news sync <category>
uv run --directory {SKILL_DIR} news query <category> --since 24h
```

### 单 RSS 抓取
```bash
uv run --directory {SKILL_DIR} news rss <rss_url>
uv run --directory {SKILL_DIR} news rss <rss_url> --limit 5
uv run --directory {SKILL_DIR} news rss <rss_url> --format json
```

### 按 category live fetch
```bash
uv run --directory {SKILL_DIR} news fetch <category>
uv run --directory {SKILL_DIR} news fetch <category> --limit 5
uv run --directory {SKILL_DIR} news fetch <category> --format json
uv run --directory {SKILL_DIR} news fetch --list
uv run --directory {SKILL_DIR} news fetch --all
```

### 同步入库
```bash
uv run --directory {SKILL_DIR} news sync <category>
uv run --directory {SKILL_DIR} news sync --all
```

### SQLite 查询
```bash
uv run --directory {SKILL_DIR} news query <category>
uv run --directory {SKILL_DIR} news query <category> --limit 10
uv run --directory {SKILL_DIR} news query <category> --since '2026-03-09T18:00:00+08:00'
uv run --directory {SKILL_DIR} news query <category> --since 24h
uv run --directory {SKILL_DIR} news query <category> --since '2026-03-09T00:00:00+08:00' --until '2026-03-10T00:00:00+08:00'
uv run --directory {SKILL_DIR} news query --all --since 6h -f json
uv run --directory {SKILL_DIR} news query --list
```

### 直接短命令别名
```bash
uv run --directory {SKILL_DIR} rss-fetch <rss_url>
uv run --directory {SKILL_DIR} news-fetch <category>
uv run --directory {SKILL_DIR} news-sync <category>
uv run --directory {SKILL_DIR} news-query <category>
```

## 参数速查

- `news rss`：`url` / `--limit` / `--format`
- `news fetch`：`category` / `--limit` / `--format` / `--list` / `--all`
- `news sync`：`category` / `--all`
- `news query`：`category` / `--limit` / `--format` / `--since` / `--until` / `--list` / `--all`

## 时间参数规则（news query）

推荐：**ISO 8601 + 时区**

```bash
--since '2026-03-09T18:00:00+08:00'
--until '2026-03-10T00:00:00+08:00'
```

支持格式：
- `2026-03-09T18:00:00+08:00`
- `2026-03-09 18:00`
- `2026-03-09` / `2026/03/09` / `20260309`
- `202603091830` / `20260309183000`
- `24h` / `6h` / `2d` / `90m` / `1w`

区间语义：`[since, until)`
- `published_ts >= since`
- `published_ts < until`

## 推荐工作流

```bash
uv run --directory {SKILL_DIR} news sync middle-east
uv run --directory {SKILL_DIR} news query middle-east --since 24h
```

```bash
uv run --directory {SKILL_DIR} news query middle-east --since 2026-03-09 --until 2026-03-10
```
