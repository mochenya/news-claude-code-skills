# JP-KR News 源选型记录

## 筛选原则

1. **英文优先** — RSS 摘要可直接阅读，减少负载时延
2. **有摘要优于仅标题** — 降低 `web_extract` 补全频率
3. **互补不重复** — 覆盖日本政策/央行/汇率 + 韩国政策/央行/出口/芯片/电池
4. **5 源为上限** — 控制抓取时延，4h 窗口 15-25 条、12h 窗口 30-50 条
5. **稳定交付** — RSS 端点连续可用，无频繁 404/重定向

## 入选源

| Key | 来源 | URL | 命中情况 |
|-----|------|-----|---------|
| `nikkei-asia` | Nikkei Asia | `asia.nikkei.com/rss/feed/nar` | 仅标题；高价值政策与公司头条，需 web_extract 补全 |
| `japan-times-business` | Japan Times Business | `japantimes.co.jp/business/feed/` | 2-5 条/window，日元/央行/东证/日企 |
| `yonhap-en-all` | Yonhap News (English) | `en.yna.co.kr/RSS/news.xml` | 3-8 条/window，政治+经济+突发 |
| `yonhap-en-economy` | Yonhap Economy (English) | `en.yna.co.kr/RSS/economy-finance.xml` | 3-8 条/window，央行/产业/贸易数据 |
| `korea-herald-business` | Korea Herald Business | `koreaherald.com/rss/kh_Business` | 2-5 条/window，韩企/并购/科技产业 |

## 淘汰源

| 来源 | 淘汰原因 |
|------|---------|
| Korea JoongAng Daily | RSS 端点已不可用 |
| KED Global | RSS 返回 HTML 页面而非 XML |
| NHK World EN | RSS XML 格式损坏 |

## 已知限制

- **Nikkei Asia 付费墙**：RSS 仅含标题和链接，无正文摘要。对高价值 Nikkei 标题须通过 `web_extract` 获取详情。
- **Yonhap 双频道交叉**：全站频道与经济频道可能就同一事件从不同角度发稿（如 BOK 利率决议），Agent 需判断合并。
- **行情源可用性（2026-09-18 实测）**：`Google Finance`（`/finance/quote/NI225:INDEXNIKKEI`、`KOSPI:KRX`、`USD-JPY`、`USD-KRW`）与 `CNBC quotes`（`.TOPX`、`.KQ11`）可稳定读到盘中点位与前收；Yahoo Finance（429）、stooq（符号 404）、investing.com（403）、MarketWatch（空页）均不可用。TOPIX/KOSDAQ 取 CNBC quotes，日经/KOSPI/汇率取 Google Finance。指数与前收必须互相对账（如 KOSDAQ 825.78 对前收 822.18、日经对前收 64,136.25），对不上说明抓到了不同时间线，弃用。
- **日本侧补全的可用路径（2026-09-19 实测）**：`marketscreener` 香港站（`hk.marketscreener.com`）镜像 Reuters 稿件并显示 HKT 发布时间，可用于确认日本相关 FX/宏观条目是否落在窗口内；`newsonjapan.com` 聚合 NHK/テレ東 的日文报道（页面顶部为当日条目，但单篇内文会标注真实日期，勿只看首页日期）；`english.kyodonews.net` Digest 编号递增可推断日期，但 403/额度限制频繁。日本侧仍为 0 条时，按上述顺序补全，仍无则在简报中说明覆盖缺口。
- **窗口特征**：08:00 档窗口（前日 22:00 – 当日 08:00 BJT）对应日本 23:00–09:00 JST，日本国内新闻天然稀少，日本侧通常只能得到纽约时段发生的汇率/央行余波类条目；不要为此放宽时间窗口。
- **韩国侧周末/下午窗口补全（2026-09-19 实测）**：`chosun.com/english/national-en/` 列表页可按日期目录（`/2026/09/19/`）取当日子站内条目，单篇 `meta[property="article:published_time"]` 为 UTC，可直接判定是否落在窗口内（KST=BJT−1）；Yonhap 英文站同名元数据为 `+09:00`。窗口内韩国政治/经济稿常只在此类韩媒自有英文版出现（Yonhap RSS 周末偏体育）。
- **周末收盘档（周六/周日）口径**：日韩股市周末休市，简报的「股市与市场表现」必须改写为「最近交易日（周五）收盘」，并显式声明休市；日本侧须查 JPX 官方假日日历（`jpx.co.jp/english/corporate/about-jpx/calendar/`）确认 Silver Week 等连续休市与恢复交易日（2026 年为 9/21–23 休市、9/24 复市），不得用当日「收盘」措辞。
- **日本侧窗口过滤的可用路径（2026-09-21 实测）**：`https://www.japantimes.co.jp/feed/`（全站 RSS）用桌面 UA（`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36`）`curl` 返回 200、约 30 条且每条带 `pubDate`，可直接按北京时间窗口过滤（该来源只覆盖日本+世界稿，世界稿按剔除范围排除）；同一 UA 下 `/business/feed/` 与 `koreaherald.com/rss/kh_Business` 仍为 403，说明拦的是路径级规则，不能靠 UA 绕过。窗口内日本侧只剩 1–2 条时以此补齐，并在元信息行标注 `[Japan Times]`。
- **源时效性核查（2026-09-20 复测）**：`nikkei-asia` 返回的 50 条 entry 全部不含发布日期（RDF/RSS1.0，仅 title+link），会被 `--since/--until` 全部过滤掉；`japan-times-business`、`korea-herald-business` 命中 0 条，`curl` 实测根因为 HTTP 403（bot 拦截，非 XML 结构本身损坏，返回体是拦截页），需按 `blocked-page-recovery` 思路绕过，或改走 `english.kyodonews.net`、`asahi.com/ajw`、`japantimes.co.jp` 网页检索。即窗口候选集实际只剩 Yonhap 两个频道，周末尤甚（Yonhap Economy 频道周末不更新，可能整段窗口为 0 条）。成稿前若日本侧为 0 条，须先用 `web_search` + `web_extract` 补日本侧并逐条核验发布时间落在窗口内（Kyodo/Nikkei Asia 页面均显示 JST，BJT=JST−1），或明确说明覆盖缺口；不要因日本侧为空就删掉时间窗内的韩国/全球宏观条目。
