# 部署指南 — AI交易助手 OpenClaw部署

## 快速部署

### 1. 安装Skill

将 `trading-assistant.skill` 文件导入OpenClaw平台，或直接将 `trading-assistant/` 目录复制到技能目录。

### 2. 配置持仓

**方式A — 编辑JSON（推荐）**

编辑 `references/portfolio-config.json`，填入你的持仓信息和API密钥：

```json
{
  "portfolio": {
    "holdings": [
      {"symbol": "AAPL", "name": "苹果", "market": "US", "cost_price": 165.0, "quantity": 100, "target_weight": 0.15, "sector": "科技"}
    ],
    "watchlist": [
      {"symbol": "NVDA", "name": "英伟达", "market": "US", "target_entry": 110.0, "sector": "科技", "reason": "等待回调", "priority": "高"}
    ]
  },
  "api_keys": {
    "finnhub": "你的密钥",
    "fred": "你的密钥",
    "alpha_vantage": "你的密钥",
    "newsapi": "你的密钥"
  }
}
```

**方式B — 使用Excel模板**

打开 `持仓录入模板.xlsx`，在三个Sheet中填入持仓、关注列表和风险参数，保存即可。

**方式C — API接口**

如果你有持仓管理API，运行：
```bash
python scripts/import_portfolio.py --api https://你的API地址/portfolio
```

### 3. 配置API密钥

系统需要以下免费API密钥才能获取完整数据：

| API | 用途 | 获取地址 | 免费额度 |
|-----|------|---------|---------|
| Finnhub | 新闻+经济日历 | https://finnhub.io/register | 60次/分钟 |
| FRED | 宏观经济数据 | https://fred.stlouisfed.org/docs/api/api_key.html | 无限制 |
| Alpha Vantage | 技术指标 | https://www.alphavantage.co/support/#api-key | 25次/天 |
| NewsAPI | 新闻聚合 | https://newsapi.org/register | 100次/天 |

将密钥填入 `references/portfolio-config.json` 的 `api_keys` 部分。

### 4. 设置定时任务

在OpenClaw中创建定时任务：

- **任务ID**: `daily-trading-analysis`
- **Cron**: `0 8 * * 1-5`（工作日早8点）
- **提示词**:
```
读取 trading-assistant/SKILL.md 并按其中的执行流程运行完整分析。先运行 trading_analyzer.py 获取数据并分析，然后运行 generate_report.py 生成HTML报告。如果API调用失败，使用WebSearch作为备选数据源。最后输出精简的文字摘要并提供报告文件。
```

### 5. 验证运行

手动触发一次定时任务，检查：
- `latest_analysis.json` 是否生成且包含完整数据
- HTML报告是否正确渲染
- 五维评分是否合理
- 交易建议是否符合配置的规则

## 目录结构

```
trading-assistant/
├── SKILL.md                          # 技能定义和执行流程
├── DEPLOY.md                         # 本部署指南
├── 持仓录入模板.xlsx                   # Excel手动录入模板
├── scripts/
│   ├── trading_analyzer.py           # 核心分析引擎（五维评分+规则匹配）
│   ├── generate_report.py            # HTML报告生成器
│   └── import_portfolio.py           # 持仓导入工具（Excel/API/JSON）
├── references/
│   ├── portfolio-config.json         # ⭐ 持仓配置（需要编辑）
│   ├── trading-rules.json            # ⭐ 交易规则（可自定义）
│   ├── trading-rules-candidates.json # 6套经典策略备选规则
│   ├── scoring-model.md              # 五维评分模型说明
│   ├── dalio-principles.md           # 达里奥全天候策略
│   ├── buffett-principles.md         # 巴菲特价值投资
│   └── data-fetching.md             # 数据源和API说明
└── (运行时生成)
    ├── latest_analysis.json          # 最新分析结果
    └── trading-report-YYYY-MM-DD.html # 每日HTML报告
```

## 依赖项

- Python 3.8+
- openpyxl（Excel导入，`pip install openpyxl`）
- 网络访问（API数据获取）

## 自定义策略

### 修改交易规则
编辑 `references/trading-rules.json`，每条规则的 `启用` 字段控制开关。

### 切换策略组合
使用 `trading-strategy-selector.html`（在全球投资情报搜集系统根目录）可视化选择和导出规则组合，或直接从 `references/trading-rules-candidates.json` 复制规则到 `trading-rules.json`。

### 添加自定义规则
在 `trading-rules.json` 的 `自定义规则.my_rules` 数组中添加新规则，格式：
```json
{
  "id": "MY2",
  "名称": "规则名称",
  "条件": "条件表达式",
  "启用": true,
  "说明": "规则说明"
}
```

## 常见问题

**Q: API调用失败怎么办？**
系统有三级降级：主源 → 备份源 → 缓存。如果全部失败，Skill会指示Claude使用WebSearch从财经网站获取数据手动评分。

**Q: 如何更新持仓？**
编辑Excel模板并保存，下次分析引擎运行时自动检测导入。或使用API/JSON导入。

**Q: 报告在哪里？**
每次运行后在技能目录生成 `trading-report-YYYY-MM-DD.html`，可在浏览器中打开查看。
