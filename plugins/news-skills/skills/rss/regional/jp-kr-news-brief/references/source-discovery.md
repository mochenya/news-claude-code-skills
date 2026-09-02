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
