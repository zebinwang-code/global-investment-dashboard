#!/usr/bin/env python3
"""
AI交易助手 - HTML报告生成器
将分析结果渲染为交互式可视化报告
"""

import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)

def generate_html(data, output_path):
    """生成交互式HTML报告"""

    macro = data.get("macro", {})
    summary = data.get("portfolio_summary", {})
    holdings = data.get("holdings_advice", [])
    watchlist = data.get("watchlist_advice", [])
    mode = data.get("trading_mode", "稳健")

    # 构建持仓卡片HTML
    holdings_cards = ""
    for h in holdings:
        pnl_class = "up" if h["pnl_pct"] >= 0 else "dn"
        pnl_sign = "+" if h["pnl_pct"] >= 0 else ""
        scores = h.get("dimension_scores", {})

        market_tag = {"US": "tg-us", "HK": "tg-hk", "CN": "tg-cn"}.get(h["market"], "tg-us")
        market_label = {"US": "美股", "HK": "港股", "CN": "A股"}.get(h["market"], h["market"])

        signals_html = "".join(f'<div class="signal-item">{s}</div>' for s in h.get("tech_signals", [])[:3])
        risks_html = "".join(f'<div class="risk-item">{r}</div>' for r in h.get("risks", []))

        weight_change = h["suggested_weight"] - h["current_weight"]
        weight_arrow = "↑" if weight_change > 0 else "↓" if weight_change < 0 else "→"
        weight_class = "up" if weight_change > 0 else "dn" if weight_change < 0 else ""

        holdings_cards += f'''
        <div class="stock-card">
            <div class="sc-header">
                <div class="sc-info">
                    <span class="sc-name">{h["name"]}</span>
                    <span class="sc-symbol">{h["symbol"]}</span>
                    <span class="market-tag {market_tag}">{market_label}</span>
                    <span class="sector-tag">{h.get("sector", "")}</span>
                </div>
                <div class="sc-action">
                    <span class="action-badge">{h["action_emoji"]} {h["action"]}</span>
                </div>
            </div>

            <div class="sc-price-row">
                <div class="price-block">
                    <div class="price-label">现价</div>
                    <div class="price-value">{h["current_price"]:.2f}</div>
                </div>
                <div class="price-block">
                    <div class="price-label">成本</div>
                    <div class="price-value">{h["cost_price"]:.2f}</div>
                </div>
                <div class="price-block">
                    <div class="price-label">盈亏</div>
                    <div class="price-value {pnl_class}">{pnl_sign}{h["pnl_pct"]:.2f}%</div>
                </div>
                <div class="price-block">
                    <div class="price-label">综合评分</div>
                    <div class="price-value score-val">{h["composite_score"]:.1f}</div>
                </div>
            </div>

            <div class="sc-scores">
                <div class="score-bar-group">
                    <div class="sb-row"><span class="sb-label">基本面</span><div class="sb-track"><div class="sb-fill" style="width:{scores.get('fundamental',5)*10}%;background:var(--blue)"></div></div><span class="sb-val">{scores.get('fundamental',5):.1f}</span></div>
                    <div class="sb-row"><span class="sb-label">技术面</span><div class="sb-track"><div class="sb-fill" style="width:{scores.get('technical',5)*10}%;background:var(--cyan)"></div></div><span class="sb-val">{scores.get('technical',5):.1f}</span></div>
                    <div class="sb-row"><span class="sb-label">消息面</span><div class="sb-track"><div class="sb-fill" style="width:{scores.get('news',5)*10}%;background:var(--org)"></div></div><span class="sb-val">{scores.get('news',5):.1f}</span></div>
                    <div class="sb-row"><span class="sb-label">资金面</span><div class="sb-track"><div class="sb-fill" style="width:{scores.get('capital',5)*10}%;background:var(--grn)"></div></div><span class="sb-val">{scores.get('capital',5):.1f}</span></div>
                    <div class="sb-row"><span class="sb-label">宏观面</span><div class="sb-track"><div class="sb-fill" style="width:{scores.get('macro',5)*10}%;background:var(--purp)"></div></div><span class="sb-val">{scores.get('macro',5):.1f}</span></div>
                </div>
            </div>

            <div class="sc-detail-row">
                <div class="detail-block">
                    <span class="dl">仓位调整</span>
                    <span class="dv {weight_class}">{h["current_weight"]*100:.0f}% {weight_arrow} {h["suggested_weight"]*100:.0f}%</span>
                </div>
                <div class="detail-block">
                    <span class="dl">支撑位</span>
                    <span class="dv">{h["support"]:.2f}</span>
                </div>
                <div class="detail-block">
                    <span class="dl">阻力位</span>
                    <span class="dv">{h["resistance"]:.2f}</span>
                </div>
                <div class="detail-block">
                    <span class="dl">止损位</span>
                    <span class="dv dn">{h["stop_loss_price"]:.2f}</span>
                </div>
            </div>

            {f'<div class="sc-signals">{signals_html}</div>' if signals_html else ''}
            {f'<div class="sc-risks">{risks_html}</div>' if risks_html else ''}
        </div>
        '''

    # 关注列表卡片
    watchlist_cards = ""
    for w in watchlist:
        scores = w.get("dimension_scores", {})
        market_tag = {"US": "tg-us", "HK": "tg-hk", "CN": "tg-cn"}.get(w["market"], "tg-us")
        market_label = {"US": "美股", "HK": "港股", "CN": "A股"}.get(w["market"], w["market"])

        entry_class = "grn" if w["entry_signal"] == "已到建仓区间" else "org"

        watchlist_cards += f'''
        <div class="watch-card">
            <div class="wc-header">
                <span class="wc-name">{w["name"]}</span>
                <span class="wc-symbol">{w["symbol"]}</span>
                <span class="market-tag {market_tag}">{market_label}</span>
                <span class="entry-badge {entry_class}">{w["entry_signal"]}</span>
            </div>
            <div class="wc-row">
                <span>现价: <b>{w["current_price"]:.2f}</b></span>
                <span>目标建仓价: <b>{w["target_entry"]:.2f}</b></span>
                <span>综合评分: <b>{w["composite_score"]:.1f}</b></span>
            </div>
            <div class="wc-reason">{w.get("reason", "")}</div>
            <div class="wc-scores">
                基本面:{scores.get('fundamental',5):.1f} | 技术:{scores.get('technical',5):.1f} | 消息:{scores.get('news',5):.1f} | 资金:{scores.get('capital',5):.1f} | 宏观:{scores.get('macro',5):.1f}
            </div>
        </div>
        '''

    # 操作建议列表
    actions_html = ""
    for action in summary.get("actions", []):
        actions_html += f'<div class="action-item">{action}</div>'

    if not actions_html:
        actions_html = '<div class="action-item">当前无需调整，维持现有仓位</div>'

    # 象限可视化
    quadrant = macro.get("quadrant", "未知")
    q_positions = {"金发女孩": (2, 1), "过热": (2, 2), "衰退": (1, 1), "滞胀": (1, 2)}
    active_q = q_positions.get(quadrant, (1, 1))

    risk_color = summary.get("risk_color", "orange")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI交易助手 - 每日分析报告</title>
<style>
:root{{--b0:#0a0e17;--b1:#111827;--b2:#1a2332;--b3:#1f2b3d;--bd:#2a3548;--t1:#e5e7eb;--t2:#9ca3af;--t3:#6b7280;--blue:#3b82f6;--cyan:#06b6d4;--grn:#10b981;--red:#ef4444;--org:#f59e0b;--purp:#8b5cf6;--pink:#ec4899}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:var(--b0);color:var(--t1);min-height:100vh;line-height:1.6}}
::-webkit-scrollbar{{width:5px}}::-webkit-scrollbar-track{{background:var(--b0)}}::-webkit-scrollbar-thumb{{background:var(--bd);border-radius:3px}}

.header{{background:linear-gradient(135deg,rgba(17,24,39,.98),rgba(26,35,50,.95));border-bottom:1px solid var(--bd);padding:16px 24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}}
.header h1{{font-size:20px;background:linear-gradient(135deg,var(--blue),var(--cyan));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.header .meta{{font-size:11px;color:var(--t3)}}
.header .mode-badge{{background:linear-gradient(135deg,var(--blue),var(--cyan));color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600}}

.container{{max-width:1400px;margin:0 auto;padding:16px}}
.section{{margin-bottom:20px}}
.section-title{{font-size:14px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px}}

/* 宏观面板 */
.macro-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px}}
.macro-card{{background:var(--b2);border:1px solid var(--bd);border-radius:10px;padding:12px;text-align:center}}
.macro-label{{font-size:9px;color:var(--t3);margin-bottom:4px}}
.macro-value{{font-size:22px;font-weight:800}}
.macro-sub{{font-size:9px;margin-top:2px}}
.up{{color:var(--grn)}}.dn{{color:var(--red)}}

/* 风险与象限 */
.risk-panel{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:16px}}
.risk-card{{background:var(--b2);border:1px solid var(--bd);border-radius:12px;padding:16px}}
.risk-score{{font-size:48px;font-weight:800;text-align:center}}
.risk-label{{text-align:center;font-size:12px;font-weight:600;padding:4px 12px;border-radius:12px;display:inline-block;margin:6px auto;display:block;width:fit-content;margin:6px auto 0}}

/* 象限图 */
.quadrant-grid{{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:3px;height:140px;margin-top:8px}}
.q-cell{{border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;opacity:0.3;transition:.3s}}
.q-cell.active{{opacity:1;box-shadow:0 0 15px rgba(59,130,246,.3)}}
.q-goldilocks{{background:rgba(16,185,129,.15);color:var(--grn)}}
.q-overheat{{background:rgba(245,158,11,.15);color:var(--org)}}
.q-recession{{background:rgba(59,130,246,.15);color:var(--blue)}}
.q-stagflation{{background:rgba(239,68,68,.15);color:var(--red)}}

/* 持仓卡片 */
.stock-card{{background:var(--b2);border:1px solid var(--bd);border-radius:12px;padding:16px;margin-bottom:12px;transition:.2s}}
.stock-card:hover{{border-color:rgba(59,130,246,.3);transform:translateY(-1px)}}
.sc-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px}}
.sc-info{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.sc-name{{font-size:16px;font-weight:700}}
.sc-symbol{{font-size:11px;color:var(--t3)}}
.market-tag{{font-size:9px;padding:2px 6px;border-radius:4px;font-weight:600}}
.tg-us{{background:rgba(59,130,246,.15);color:var(--blue)}}
.tg-hk{{background:rgba(245,158,11,.15);color:var(--org)}}
.tg-cn{{background:rgba(239,68,68,.15);color:var(--red)}}
.sector-tag{{font-size:9px;padding:2px 6px;border-radius:4px;background:rgba(139,92,246,.15);color:var(--purp)}}
.action-badge{{font-size:11px;font-weight:600;padding:4px 10px;border-radius:8px;background:rgba(6,182,212,.12);color:var(--cyan)}}

.sc-price-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px}}
.price-block{{background:rgba(255,255,255,.03);padding:8px;border-radius:6px;text-align:center}}
.price-label{{font-size:9px;color:var(--t3);margin-bottom:2px}}
.price-value{{font-size:16px;font-weight:700}}
.score-val{{color:var(--cyan)}}

.sc-scores{{margin-bottom:10px}}
.sb-row{{display:flex;align-items:center;gap:6px;margin-bottom:4px}}
.sb-label{{font-size:9px;color:var(--t3);min-width:36px}}
.sb-track{{flex:1;height:6px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden}}
.sb-fill{{height:100%;border-radius:3px;transition:width .8s ease}}
.sb-val{{font-size:10px;font-weight:700;min-width:24px;text-align:right}}

.sc-detail-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:8px}}
.detail-block{{background:rgba(255,255,255,.03);padding:6px 8px;border-radius:5px}}
.dl{{font-size:9px;color:var(--t3);display:block}}.dv{{font-size:12px;font-weight:600}}

.sc-signals{{margin-top:6px}}
.signal-item{{font-size:10px;color:var(--cyan);padding:2px 0}}
.sc-risks{{margin-top:4px}}
.risk-item{{font-size:10px;color:var(--org);padding:2px 0}}

/* 关注列表 */
.watch-card{{background:var(--b2);border:1px solid var(--bd);border-radius:10px;padding:12px;margin-bottom:8px}}
.wc-header{{display:flex;align-items:center;gap:6px;margin-bottom:6px;flex-wrap:wrap}}
.wc-name{{font-size:14px;font-weight:700}}
.wc-symbol{{font-size:10px;color:var(--t3)}}
.entry-badge{{font-size:9px;padding:2px 6px;border-radius:4px;font-weight:600}}
.entry-badge.grn{{background:rgba(16,185,129,.15);color:var(--grn)}}
.entry-badge.org{{background:rgba(245,158,11,.15);color:var(--org)}}
.wc-row{{font-size:11px;color:var(--t2);margin-bottom:4px;display:flex;gap:16px;flex-wrap:wrap}}
.wc-reason{{font-size:10px;color:var(--t3);font-style:italic;margin-bottom:4px}}
.wc-scores{{font-size:9px;color:var(--t3)}}

/* 操作建议 */
.action-panel{{background:var(--b2);border:1px solid var(--bd);border-radius:12px;padding:16px}}
.action-item{{padding:6px 0;font-size:12px;border-bottom:1px solid rgba(255,255,255,.04)}}
.action-item:last-child{{border-bottom:none}}

/* 仓位建议 */
.position-summary{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}}
.ps-card{{background:var(--b2);border:1px solid var(--bd);border-radius:10px;padding:14px;text-align:center}}
.ps-label{{font-size:10px;color:var(--t3);margin-bottom:4px}}
.ps-value{{font-size:28px;font-weight:800}}

.footer{{text-align:center;padding:16px;color:var(--t3);font-size:9px;border-top:1px solid var(--bd);margin-top:20px}}

@media(max-width:768px){{
    .risk-panel{{grid-template-columns:1fr}}
    .sc-price-row,.sc-detail-row{{grid-template-columns:repeat(2,1fr)}}
    .position-summary{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>🤖 AI交易助手 - 每日分析报告</h1>
        <div class="meta">生成时间: {data.get("generated_at", datetime.now().isoformat())[:19]} | 达里奥全天候 + 巴菲特价值投资</div>
    </div>
    <span class="mode-badge">{mode}模式</span>
</div>

<div class="container">

    <!-- 宏观环境 -->
    <div class="section">
        <div class="section-title">🌍 宏观环境</div>
        <div class="macro-grid">
            <div class="macro-card">
                <div class="macro-label">VIX恐慌指数</div>
                <div class="macro-value" style="color:{'var(--red)' if macro.get('vix',0)>25 else 'var(--org)' if macro.get('vix',0)>18 else 'var(--grn)'}">{macro.get('vix', 'N/A')}</div>
                <div class="macro-sub {'up' if macro.get('vix',0)<20 else 'dn'}">{'平静' if macro.get('vix',0)<18 else '警惕' if macro.get('vix',0)<25 else '恐慌'}</div>
            </div>
            <div class="macro-card">
                <div class="macro-label">美10Y国债</div>
                <div class="macro-value">{macro.get('us10y', 'N/A')}</div>
                <div class="macro-sub">收益率</div>
            </div>
            <div class="macro-card">
                <div class="macro-label">美元指数</div>
                <div class="macro-value">{macro.get('dxy', 'N/A')}</div>
                <div class="macro-sub {'up' if macro.get('dxy_change',0)>0 else 'dn'}">{'+' if macro.get('dxy_change',0)>0 else ''}{macro.get('dxy_change',0):.2f}%</div>
            </div>
            <div class="macro-card">
                <div class="macro-label">S&P 500</div>
                <div class="macro-value {'up' if macro.get('sp500_chg',0)>0 else 'dn'}">{macro.get('sp500', 'N/A')}</div>
                <div class="macro-sub {'up' if macro.get('sp500_chg',0)>0 else 'dn'}">{'+' if macro.get('sp500_chg',0)>0 else ''}{macro.get('sp500_chg',0):.2f}%</div>
            </div>
            <div class="macro-card">
                <div class="macro-label">恒生指数</div>
                <div class="macro-value {'up' if macro.get('hsi_chg',0)>0 else 'dn'}">{macro.get('hsi', 'N/A')}</div>
                <div class="macro-sub {'up' if macro.get('hsi_chg',0)>0 else 'dn'}">{'+' if macro.get('hsi_chg',0)>0 else ''}{macro.get('hsi_chg',0):.2f}%</div>
            </div>
            <div class="macro-card">
                <div class="macro-label">上证指数</div>
                <div class="macro-value {'up' if macro.get('sse_chg',0)>0 else 'dn'}">{macro.get('sse', 'N/A')}</div>
                <div class="macro-sub {'up' if macro.get('sse_chg',0)>0 else 'dn'}">{'+' if macro.get('sse_chg',0)>0 else ''}{macro.get('sse_chg',0):.2f}%</div>
            </div>
            <div class="macro-card">
                <div class="macro-label">恐贪指数</div>
                <div class="macro-value">{macro.get('fear_greed', 50)}</div>
                <div class="macro-sub">{macro.get('fear_greed_label', 'Neutral')}</div>
            </div>
            <div class="macro-card">
                <div class="macro-label">北向资金</div>
                <div class="macro-value {'up' if macro.get('northbound_net',0)>0 else 'dn'}">{macro.get('northbound_net',0):.1f}</div>
                <div class="macro-sub">亿元</div>
            </div>
        </div>
    </div>

    <!-- 风险与象限 -->
    <div class="section">
        <div class="risk-panel">
            <div class="risk-card">
                <div class="section-title">📊 组合评分</div>
                <div class="risk-score" style="color:var(--cyan)">{summary.get('avg_score', 0):.1f}</div>
                <div class="risk-label" style="background:rgba(6,182,212,.12);color:var(--cyan)">综合得分 /10</div>
            </div>
            <div class="risk-card">
                <div class="section-title">⚠️ 风险等级</div>
                <div class="risk-score" style="color:var(--{risk_color})">{summary.get('risk_level', '中等')}</div>
                <div class="risk-label" style="background:rgba({'239,68,68' if risk_color=='red' else '245,158,11' if risk_color=='orange' else '16,185,129'},.12);color:var(--{risk_color})">VIX={macro.get('vix',0)}</div>
            </div>
            <div class="risk-card">
                <div class="section-title">🌐 达里奥象限</div>
                <div class="quadrant-grid">
                    <div class="q-cell q-goldilocks {'active' if quadrant=='金发女孩' else ''}">金发女孩<br>↑增长 ↓通胀</div>
                    <div class="q-cell q-overheat {'active' if quadrant=='过热' else ''}">过热<br>↑增长 ↑通胀</div>
                    <div class="q-cell q-recession {'active' if quadrant=='衰退' else ''}">衰退<br>↓增长 ↓通胀</div>
                    <div class="q-cell q-stagflation {'active' if quadrant=='滞胀' else ''}">滞胀<br>↓增长 ↑通胀</div>
                </div>
            </div>
        </div>
    </div>

    <!-- 仓位建议 -->
    <div class="section">
        <div class="section-title">💼 仓位建议</div>
        <div class="position-summary">
            <div class="ps-card">
                <div class="ps-label">建议总仓位</div>
                <div class="ps-value" style="color:var(--cyan)">{summary.get('suggested_total_position',0)*100:.0f}%</div>
            </div>
            <div class="ps-card">
                <div class="ps-label">现金储备</div>
                <div class="ps-value" style="color:var(--org)">{summary.get('cash_ratio',0)*100:.0f}%</div>
            </div>
            <div class="ps-card">
                <div class="ps-label">持仓标的数</div>
                <div class="ps-value">{summary.get('holdings_count',0)}</div>
            </div>
        </div>
    </div>

    <!-- 操作建议 -->
    <div class="section">
        <div class="section-title">🎯 今日操作建议</div>
        <div class="action-panel">{actions_html}</div>
    </div>

    <!-- 持仓分析 -->
    <div class="section">
        <div class="section-title">📋 持仓诊断 ({len(holdings)}只)</div>
        {holdings_cards}
    </div>

    <!-- 关注列表 -->
    <div class="section">
        <div class="section-title">👁️ 关注列表 ({len(watchlist)}只)</div>
        {watchlist_cards}
    </div>

</div>

<div class="footer">
    AI交易助手 v1.0 | 达里奥全天候 + 巴菲特价值投资 | 仅供参考，不构成投资建议<br>
    数据来源: Yahoo Finance / 东方财富 / FRED / Alternative.me | 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M")}
</div>

</body>
</html>'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ HTML报告已生成: {output_path}")
    return output_path


def main():
    # 读取分析结果
    analysis_path = os.path.join(SKILL_DIR, "latest_analysis.json")
    if not os.path.exists(analysis_path):
        print("❌ 未找到分析结果文件，请先运行 trading_analyzer.py")
        sys.exit(1)

    with open(analysis_path, encoding="utf-8") as f:
        data = json.load(f)

    # 生成报告
    output_path = os.path.join(SKILL_DIR, "trading-report.html")
    if len(sys.argv) > 1:
        output_path = sys.argv[1]

    generate_html(data, output_path)


if __name__ == "__main__":
    main()
