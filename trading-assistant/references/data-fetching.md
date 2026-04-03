# 数据获取方法

## 数据源架构

本系统使用与全球投资情报中心相同的数据源，详见 DATA-SOURCES.md。以下是各维度所需的具体数据点和获取方式。

## 基本面数据

### 美股 — Yahoo Finance API
```
端点: https://query1.finance.yahoo.com/v8/finance/chart/{symbol}
参数: interval=1d&range=1y
返回: 价格/成交量历史

端点: https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}
参数: modules=financialData,defaultKeyStatistics,earningsTrend,incomeStatementHistory
返回: PE/PB/ROE/营收增长/EPS等
```

### 港股 — Yahoo Finance (后缀.HK)
```
示例: 0700.HK (腾讯), 9988.HK (阿里)
同美股API，标的代码加.HK后缀
```

### A股 — 东方财富 Push API
```
行情: https://push2.eastmoney.com/api/qt/stock/get
参数: secid=1.600519 (1=上交所, 0=深交所)
字段: f43(现价),f44(最高),f45(最低),f46(开盘),f47(成交量)

财务数据: https://push2.eastmoney.com/api/qt/slist/get
```

## 技术面数据

所有市场统一通过价格历史计算：
- **均线**: MA5/MA10/MA20/MA60/MA120/MA250 — 从收盘价序列计算
- **MACD**: DEA/DIF/MACD柱 — 标准参数12,26,9
- **RSI**: 14日RSI
- **布林带**: 20日均线 ± 2倍标准差
- **成交量**: 5日均量 vs 当日量比

可选用Alpha Vantage技术指标API直接获取：
```
https://www.alphavantage.co/query?function=RSI&symbol={symbol}&interval=daily&time_period=14&series_type=close&apikey={key}
```

## 消息面数据

### Finnhub 新闻API
```
https://finnhub.io/api/v1/company-news?symbol={symbol}&from={date}&to={date}&token={key}
返回: 标题、摘要、来源、情感标签
```

### 中国市场 — 东方财富/财联社
```
东方财富个股新闻: https://push2.eastmoney.com/api/qt/stock/get (新闻字段)
财联社快讯: 网页抓取 cls.cn
```

## 资金面数据

### 北向资金（沪深港通）
```
东方财富: https://push2.eastmoney.com/api/qt/kamtbs.wss/get
字段: 沪股通/深股通 当日净买入额
```

### 主力资金流向
```
东方财富: https://push2.eastmoney.com/api/qt/stock/fflow/kline/get
参数: secid={市场}.{代码}&klt=101 (日线)
字段: 主力/超大单/大单/中单/小单 净流入
```

### 融资融券
```
东方财富: https://datacenter.eastmoney.com/api/data/v1/get
报表: RPT_MARGIN_TRADE_STATISTICS
```

## 宏观面数据

### FRED (美联储经济数据)
```
https://api.stlouisfed.org/fred/series/observations
关键系列:
- DGS10: 美国10年期国债收益率
- DGS2: 美国2年期国债收益率
- FEDFUNDS: 联邦基金利率
- VIXCLS: VIX恐慌指数
- CPIAUCSL: CPI
- UNRATE: 失业率
- GDP: GDP
- ISM/PMI: 通过Finnhub经济日历获取
```

### 汇率
```
https://open.er-api.com/v6/latest/USD
覆盖: CNY, HKD, JPY, EUR等
```

### 经济日历
```
https://finnhub.io/api/v1/calendar/economic?token={key}
覆盖: 全球重要经济数据发布日期和预期值
```

## 数据缓存策略

| 数据类型 | 刷新频率 | 缓存时间 |
|----------|---------|---------|
| 实时价格 | 每次运行 | 不缓存 |
| 财务数据 | 每周 | 7天 |
| 技术指标 | 每日 | 24小时 |
| 新闻消息 | 每次运行 | 1小时 |
| 资金流向 | 每日 | 24小时 |
| 宏观数据 | 每周 | 7天 |

## 错误处理

采用三级降级策略：
1. 主数据源请求
2. 失败 → 切换备份源
3. 全部失败 → 使用缓存数据 + 标注"数据可能过期"
