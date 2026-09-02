# CLI 速查

## 1. 环境

所有命令统一建议使用：

```bash
uv run --directory {baseDir} news ...
```

`{baseDir}` 是 skill 的安装根目录，运行时由调用方自动替换为实际路径。

这样能稳定使用 skill 自己的项目环境与依赖。

---

## 2. 统一入口 `news`

用途：通过一个总入口管理所有子命令。

```bash
uv run --directory {baseDir} news rss <RSS_URL>
uv run --directory {baseDir} news fetch <category>
uv run --directory {baseDir} news sync <category>
uv run --directory {baseDir} news query <category> --since 24h
```

子命令：
- `rss`
- `fetch`
- `sync`
- `query`

---

## 3. `news rss`

用途：抓取单个 RSS URL。

```bash
uv run --directory {baseDir} news rss <RSS_URL>
uv run --directory {baseDir} news rss <RSS_URL> --limit 5
uv run --directory {baseDir} news rss <RSS_URL> --format json
```

参数：
- `url`
- `-l, --limit`
- `-f, --format {text,json}`

---

## 4. `news fetch`

用途：按内置 category 直接 live fetch。

```bash
uv run --directory {baseDir} news fetch <category>
uv run --directory {baseDir} news fetch <category> --limit 5
uv run --directory {baseDir} news fetch <category> --format json
uv run --directory {baseDir} news fetch --list
uv run --directory {baseDir} news fetch --all
```

参数：
- `category`
- `-l, --limit`
- `-f, --format {text,json}`
- `--list`
- `--all`

---

## 5. `news sync`

用途：把 `sources.json` 同步入 SQLite。

```bash
# Sync one category into sqlite
uv run --directory {baseDir} news sync <category>

# Sync all categories
uv run --directory {baseDir} news sync --all
```

参数：
- `category`
- `--all`

---

## 6. `news query`

用途：从 SQLite 查询新闻。

```bash
# Query one category from sqlite
uv run --directory {baseDir} news query <category>

# Query with limit
uv run --directory {baseDir} news query <category> --limit 10

# Query with a time lower bound
uv run --directory {baseDir} news query <category> --since '2026-03-09T18:00:00+08:00'

# Query a relative recent window
uv run --directory {baseDir} news query <category> --since 24h

# Query a closed-open time range [since, until)
uv run --directory {baseDir} news query <category> --since '2026-03-09T00:00:00+08:00' --until '2026-03-10T00:00:00+08:00'

# Query all categories
uv run --directory {baseDir} news query --all

# Query all categories as json
uv run --directory {baseDir} news query --all --since 6h --format json

# List categories
uv run --directory {baseDir} news query --list
```

参数：
- `category`
- `-l, --limit`
- `-f, --format {text,json}`
- `--since`
- `--until`
- `--list`
- `--all`

---

## 7. 直接短命令别名

如果你不想走统一入口，也可以直接运行：

```bash
uv run --directory {baseDir} rss-fetch <RSS_URL>
uv run --directory {baseDir} news-fetch <category>
uv run --directory {baseDir} news-sync <category>
uv run --directory {baseDir} news-query <category>
```

---

## 8. 时间参数

推荐优先使用 ISO 8601 + 时区：

```bash
2026-03-09T18:00:00+08:00
2026-03-10T00:00:00+08:00
```

也支持：

```bash
2026-03-09 18:00
2026-03-09
2026/03/09
20260309
202603091830
20260309183000
24h
6h
2d
90m
1w
```

区间语义固定为：

```text
[since, until)
published_ts >= since
published_ts < until
```
