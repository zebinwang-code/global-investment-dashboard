# 全球投资情报中心 - 数据源架构 v2.0

## 数据源总览：主源 + 备份方案

---

### 一、加密货币数据（免认证，最可靠）

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | CoinGecko | `api.coingecko.com/api/v3` | 无需 | 30/min | 14000+币种，价格/市值/成交量 |
| **备份1** | Binance Public | `api.binance.com/api/v3` | 无需 | 1200/min | 交易对实时行情/K线/深度 |
| **备份2** | CoinCap | `api.coincap.io/v2` | 无需 | 200/30s | 2000+币种，价格/历史 |

**当前状态**: ✅ 已集成 CoinGecko + Binance + CoinCap，自动切换

---

### 二、全球股指数据

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | Yahoo Finance | `query1.finance.yahoo.com/v8` | 无需 | ~2000/hr | 全球股指/个股/ETF/期货 |
| **备份1** | Alpha Vantage | `alphavantage.co/query` | 免费Key | 25/day(demo) | 全球股票/外汇/技术指标 |
| **备份2** | Finnhub | `finnhub.io/api/v1` | 免费Key | 60/min | 全球股票/新闻/经济日历 |
| **备份3** | Twelve Data | `api.twelvedata.com` | 免费Key | 250/day | 25万+金融产品 |

**关键符号映射**:
- S&P500: `^GSPC` / Nasdaq: `^IXIC` / Dow: `^DJI`
- 恒生: `^HSI` / 日经: `^N225` / 上证: `000001.SS`
- 欧洲50: `^STOXX50E` / 富时: `^FTSE` / DAX: `^GDAXI`

---

### 三、外汇数据

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | ExchangeRate API | `open.er-api.com/v6/latest/USD` | 无需 | 1500/月 | 170+货币 |
| **备份1** | ECB Data | `data-api.ecb.europa.eu` | 无需 | 适度 | 欧元交叉盘 |
| **备份2** | Alpha Vantage FX | 同上 | 免费Key | 同上 | 主要货币对 |
| **备份3** | Exchangerate-API | `api.exchangerate-api.com/v4` | 无需 | 无限(免费Key) | 全货币 |

**当前状态**: ✅ 已集成 ExchangeRate API

---

### 四、大宗商品

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | Yahoo Finance | 同上 (`GC=F`, `SI=F`, `CL=F`) | 无需 | 同上 | 黄金/白银/原油/天然气 |
| **备份1** | Metals-API | `metals-api.com/api` | 免费Key | 100/月 | 贵金属 |
| **备份2** | EIA (美能源署) | `api.eia.gov/v2` | 免费Key | 适度 | 能源价格 |

---

### 五、债券/利率数据

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | FRED (美联储) | `api.stlouisfed.org/fred` | 免费Key | 120/min | 美国国债/联邦利率/VIX |
| **备份1** | Yahoo Finance | `^TNX`(10Y), `^FVX`(5Y) | 无需 | 同上 | 美国国债收益率 |
| **备份2** | ECB | 同上 | 无需 | 适度 | 欧洲利率 |

**FRED 关键序列ID**:
- `DGS10` 美国10Y国债 / `DGS2` 美国2Y / `FEDFUNDS` 联邦基金利率
- `VIXCLS` VIX恐慌指数 / `SP500` 标普500 / `UNRATE` 失业率
- `CPIAUCSL` CPI / `GDP` GDP

---

### 六、市场情绪指标

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | Alternative.me FGI | `api.alternative.me/fng` | 无需 | 无限 | 加密市场恐贪指数 |
| **备份1** | CNN Fear & Greed | 网页抓取 | 无需 | - | 美股综合恐贪指数 |
| **数据2** | FRED VIX | 同上 | 免费Key | 同上 | VIX恐慌指数历史 |

**当前状态**: ✅ 已集成 Alternative.me Fear & Greed

---

### 七、中国市场（重点）

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | 东方财富 Push API | `push2.eastmoney.com` | 无需 | 适度 | A股指数/个股/资金流向 |
| **备份1** | 新浪财经 HQ | `hq.sinajs.cn` | 需Referer | 适度 | A股实时行情 |
| **备份2** | 网易财经 | `api.money.126.net` | 无需 | 适度 | A股行情/历史 |
| **备份3** | 腾讯财经 | `qt.gtimg.cn` | 无需 | 适度 | A股/港股行情 |
| **新闻** | 财联社 | 网页抓取 | - | - | 中国财经快讯 |

**东方财富关键端点**:
```
指数行情: /api/qt/ulist.np/get?secids=1.000001,0.399001
资金流向: /api/qt/stock/fflow/kline/get
板块排名: /api/qt/clist/get
```

---

### 八、日本市场

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | Yahoo Finance | `^N225`, `^TOPX` | 无需 | 同上 | 日经/东证 |
| **备份1** | 日本银行 (BOJ) | `boj.or.jp/statistics` | 无需 | 适度 | 利率/货币政策 |
| **新闻** | 日经新闻 | 网页抓取 | - | - | 日本财经 |

---

### 九、欧洲市场

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | Yahoo Finance | `^STOXX50E`, `^FTSE`, `^GDAXI` | 无需 | 同上 | 主要欧洲指数 |
| **数据** | ECB Data Portal | `data-api.ecb.europa.eu` | 无需 | 适度 | 欧元汇率/利率/宏观 |
| **备份** | Euronext | 网页抓取 | - | - | 欧洲交易所数据 |
| **新闻** | FT/Reuters | 网页抓取 | - | - | 欧洲财经 |

---

### 十、经济日历 & 新闻

| 优先级 | 数据源 | 端点 | 认证 | 限速 | 覆盖 |
|--------|--------|------|------|------|------|
| **主源** | Finnhub Calendar | `finnhub.io/api/v1/calendar` | 免费Key | 60/min | 全球经济事件 |
| **备份** | Investing.com | 网页抓取 | - | - | 全球经济日历 |
| **新闻** | Finnhub News | 同上 | 免费Key | 同上 | 股票相关新闻 |
| **新闻** | NewsAPI | `newsapi.org/v2` | 免费Key | 100/day | 全球3.8万+新闻源 |

---

## 备份策略架构

```
请求数据 → 主数据源
            ├── 成功 → 返回 + 缓存(60s)
            └── 失败 → 备份源1
                        ├── 成功 → 返回 + 缓存
                        └── 失败 → 备份源2
                                    ├── 成功 → 返回 + 缓存
                                    └── 失败 → 使用缓存/默认值
```

## API Key 注册指南（全部免费）

1. **Alpha Vantage**: https://www.alphavantage.co/support/#api-key (5req/min)
2. **Finnhub**: https://finnhub.io/register (60req/min)
3. **FRED**: https://fred.stlouisfed.org/docs/api/api_key.html (120req/min)
4. **NewsAPI**: https://newsapi.org/register (100req/day)
5. **Twelve Data**: https://twelvedata.com/pricing (250req/day)

将Key填入仪表盘代码中 `DATA_SOURCES` 配置的 `apiKey` 字段即可启用。
