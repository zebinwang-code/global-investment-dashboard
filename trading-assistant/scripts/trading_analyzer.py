#!/usr/bin/env python3
"""
AI交易助手 - 核心分析引擎
融合达里奥全天候 + 巴菲特价值投资原则
覆盖美股/港股/A股，五维评分系统
"""

import json
import sys
import os
import time
import math
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote

# ============================================================
# 配置
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(SKILL_DIR, "references", "portfolio-config.json")
RULES_PATH = os.path.join(SKILL_DIR, "references", "trading-rules.json")
XLSX_PATH = os.path.join(SKILL_DIR, "持仓录入模板.xlsx")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ============================================================
# 工具函数
# ============================================================

def fetch_json(url, headers=None, timeout=15):
    """安全的JSON获取"""
    h = {**HEADERS, **(headers or {})}
    try:
        req = Request(url, headers=h)
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [WARN] 获取失败: {url[:80]}... -> {e}")
        return None

def safe_float(val, default=0.0):
    try:
        if val is None or val == "N/A" or val == "":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

def pct_change(old, new):
    if old == 0:
        return 0
    return (new - old) / abs(old) * 100

# ============================================================
# 数据获取层
# ============================================================

class DataFetcher:
    """多源数据获取器，自动降级"""

    def __init__(self, api_keys=None):
        self.api_keys = api_keys or {}
        self.cache = {}

    # --- 价格与基本面 ---

    def get_quote_yahoo(self, symbol):
        """Yahoo Finance 行情 + 基本面"""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}?interval=1d&range=6mo&includePrePost=false"
        data = fetch_json(url)
        if not data or "chart" not in data:
            return None

        result = data["chart"]["result"]
        if not result:
            return None

        meta = result[0].get("meta", {})
        indicators = result[0].get("indicators", {})
        timestamps = result[0].get("timestamp", [])

        closes = []
        volumes = []
        if indicators.get("quote") and len(indicators["quote"]) > 0:
            q = indicators["quote"][0]
            closes = [c for c in (q.get("close") or []) if c is not None]
            volumes = [v for v in (q.get("volume") or []) if v is not None]

        current_price = meta.get("regularMarketPrice", closes[-1] if closes else 0)
        prev_close = meta.get("previousClose", meta.get("chartPreviousClose", 0))

        return {
            "symbol": symbol,
            "price": safe_float(current_price),
            "prev_close": safe_float(prev_close),
            "change_pct": pct_change(safe_float(prev_close), safe_float(current_price)),
            "currency": meta.get("currency", "USD"),
            "exchange": meta.get("exchangeName", ""),
            "closes": closes[-120:],  # 最近120个交易日
            "volumes": volumes[-120:],
            "timestamps": timestamps[-120:] if timestamps else [],
        }

    def get_fundamentals_yahoo(self, symbol):
        """Yahoo Finance 财务数据"""
        modules = "financialData,defaultKeyStatistics,summaryDetail,earningsTrend"
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{quote(symbol)}?modules={modules}"
        data = fetch_json(url)
        if not data or "quoteSummary" not in data:
            return {}

        result = data["quoteSummary"].get("result", [])
        if not result:
            return {}

        r = result[0]
        fd = r.get("financialData", {})
        ks = r.get("defaultKeyStatistics", {})
        sd = r.get("summaryDetail", {})

        def raw(d, key):
            v = d.get(key, {})
            if isinstance(v, dict):
                return v.get("raw", v.get("fmt", None))
            return v

        return {
            "pe_trailing": safe_float(raw(sd, "trailingPE")),
            "pe_forward": safe_float(raw(sd, "forwardPE")),
            "pb": safe_float(raw(sd, "priceToBook")),
            "ps": safe_float(raw(sd, "priceToSalesTrailing12Months")),
            "roe": safe_float(raw(fd, "returnOnEquity")) * 100,
            "roa": safe_float(raw(fd, "returnOnAssets")) * 100,
            "debt_to_equity": safe_float(raw(fd, "debtToEquity")),
            "current_ratio": safe_float(raw(fd, "currentRatio")),
            "revenue_growth": safe_float(raw(fd, "revenueGrowth")) * 100,
            "earnings_growth": safe_float(raw(fd, "earningsGrowth")) * 100,
            "profit_margin": safe_float(raw(fd, "profitMargins")) * 100,
            "gross_margin": safe_float(raw(fd, "grossMargins")) * 100,
            "operating_margin": safe_float(raw(fd, "operatingMargins")) * 100,
            "free_cashflow": safe_float(raw(fd, "freeCashflow")),
            "market_cap": safe_float(raw(sd, "marketCap")),
            "dividend_yield": safe_float(raw(sd, "dividendYield")) * 100,
            "beta": safe_float(raw(ks, "beta")),
            "52w_high": safe_float(raw(sd, "fiftyTwoWeekHigh")),
            "52w_low": safe_float(raw(sd, "fiftyTwoWeekLow")),
            "50d_avg": safe_float(raw(sd, "fiftyDayAverage")),
            "200d_avg": safe_float(raw(sd, "twoHundredDayAverage")),
            "peg_ratio": safe_float(raw(ks, "pegRatio")),
        }

    def get_eastmoney_quote(self, code, market_id):
        """东方财富 A股行情"""
        secid = f"{market_id}.{code}"
        url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f116,f117,f162,f167,f170,f171,f173"
        data = fetch_json(url)
        if not data or "data" not in data or data["data"] is None:
            return None
        d = data["data"]
        return {
            "symbol": d.get("f57", code),
            "name": d.get("f58", ""),
            "price": safe_float(d.get("f43", 0)) / 100,
            "change_pct": safe_float(d.get("f170", 0)) / 100,
            "pe": safe_float(d.get("f162", 0)) / 100,
            "pb": safe_float(d.get("f167", 0)) / 100,
            "market_cap": safe_float(d.get("f116", 0)),
            "volume": safe_float(d.get("f47", 0)),
            "turnover": safe_float(d.get("f48", 0)),
        }

    def get_stock_data(self, symbol, market):
        """统一入口：根据市场获取行情+基本面"""
        quote_data = {}
        fundamental_data = {}

        if market == "CN":
            # A股：用东方财富
            code = symbol.replace(".SS", "").replace(".SZ", "")
            market_id = 1 if ".SS" in symbol or code.startswith("6") else 0
            em_data = self.get_eastmoney_quote(code, market_id)
            if em_data:
                quote_data = em_data
            # 也尝试Yahoo获取更多数据
            yq = self.get_quote_yahoo(symbol)
            if yq:
                quote_data.update({k: v for k, v in yq.items() if k not in quote_data or not quote_data[k]})
        else:
            # 美股/港股：直接用Yahoo
            yq = self.get_quote_yahoo(symbol)
            if yq:
                quote_data = yq

        # 基本面数据
        fund = self.get_fundamentals_yahoo(symbol)
        if fund:
            fundamental_data = fund

        return {**quote_data, **fundamental_data}

    # --- 宏观数据 ---

    def get_macro_data(self):
        """获取宏观经济指标"""
        macro = {}

        # VIX
        vix = self.get_quote_yahoo("^VIX")
        if vix:
            macro["vix"] = vix["price"]
            macro["vix_change"] = vix["change_pct"]

        # 10年期国债
        tnx = self.get_quote_yahoo("^TNX")
        if tnx:
            macro["us10y"] = tnx["price"]

        # 2年期国债
        twoy = self.get_quote_yahoo("^IRX")
        if twoy:
            macro["us2y"] = twoy.get("price", 0)

        # 美元指数
        dxy = self.get_quote_yahoo("DX-Y.NYB")
        if dxy:
            macro["dxy"] = dxy["price"]
            macro["dxy_change"] = dxy["change_pct"]

        # 恐贪指数（加密，但可作参考）
        fng = fetch_json("https://api.alternative.me/fng/?limit=1")
        if fng and "data" in fng:
            macro["fear_greed"] = int(fng["data"][0].get("value", 50))
            macro["fear_greed_label"] = fng["data"][0].get("value_classification", "Neutral")

        # 主要指数
        for idx_symbol, idx_name in [("^GSPC", "sp500"), ("^HSI", "hsi"), ("000001.SS", "sse")]:
            idx = self.get_quote_yahoo(idx_symbol)
            if idx:
                macro[idx_name] = idx["price"]
                macro[f"{idx_name}_chg"] = idx["change_pct"]

        # FRED 数据（如果有key）
        fred_key = self.api_keys.get("fred", "")
        if fred_key:
            for series, name in [("CPIAUCSL", "cpi"), ("UNRATE", "unemployment"), ("FEDFUNDS", "fed_rate")]:
                url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={fred_key}&file_type=json&sort_order=desc&limit=2"
                data = fetch_json(url)
                if data and "observations" in data and len(data["observations"]) >= 2:
                    obs = data["observations"]
                    macro[name] = safe_float(obs[0]["value"])
                    macro[f"{name}_prev"] = safe_float(obs[1]["value"])

        return macro

    # --- 资金面 ---

    def get_northbound_flow(self):
        """获取北向资金数据"""
        url = "https://push2.eastmoney.com/api/qt/kamtbs.wss/get?fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14"
        data = fetch_json(url)
        if data and "data" in data and data["data"]:
            d = data["data"]
            return {
                "total_net": safe_float(d.get("f1", 0)) / 10000,  # 万转亿
                "sh_connect": safe_float(d.get("f2", 0)) / 10000,
                "sz_connect": safe_float(d.get("f3", 0)) / 10000,
            }
        return {"total_net": 0, "sh_connect": 0, "sz_connect": 0}

# ============================================================
# 技术分析引擎
# ============================================================

class TechnicalAnalyzer:
    """技术指标计算"""

    @staticmethod
    def moving_average(closes, period):
        if len(closes) < period:
            return None
        return sum(closes[-period:]) / period

    @staticmethod
    def ema(closes, period):
        if len(closes) < period:
            return None
        k = 2 / (period + 1)
        ema_val = sum(closes[:period]) / period
        for price in closes[period:]:
            ema_val = price * k + ema_val * (1 - k)
        return ema_val

    @staticmethod
    def macd(closes, fast=12, slow=26, signal=9):
        if len(closes) < slow + signal:
            return {"dif": 0, "dea": 0, "macd": 0, "signal": "中性"}

        k_fast = 2 / (fast + 1)
        k_slow = 2 / (slow + 1)

        ema_fast = sum(closes[:fast]) / fast
        ema_slow = sum(closes[:slow]) / slow

        dif_list = []
        for i in range(slow, len(closes)):
            ema_fast = closes[i] * k_fast + ema_fast * (1 - k_fast)
            ema_slow = closes[i] * k_slow + ema_slow * (1 - k_slow)
            dif_list.append(ema_fast - ema_slow)

        if len(dif_list) < signal:
            return {"dif": 0, "dea": 0, "macd": 0, "signal": "中性"}

        k_sig = 2 / (signal + 1)
        dea = sum(dif_list[:signal]) / signal
        for d in dif_list[signal:]:
            dea = d * k_sig + dea * (1 - k_sig)

        dif = dif_list[-1]
        macd_val = 2 * (dif - dea)

        sig = "中性"
        if len(dif_list) >= 2:
            if dif_list[-1] > dif_list[-2] and dif > dea:
                sig = "金叉/多头"
            elif dif_list[-1] < dif_list[-2] and dif < dea:
                sig = "死叉/空头"
            elif dif > dea:
                sig = "多头"
            else:
                sig = "空头"

        return {"dif": round(dif, 4), "dea": round(dea, 4), "macd": round(macd_val, 4), "signal": sig}

    @staticmethod
    def rsi(closes, period=14):
        if len(closes) < period + 1:
            return 50

        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return round(100 - 100 / (1 + rs), 2)

    @staticmethod
    def bollinger(closes, period=20, num_std=2):
        if len(closes) < period:
            return {"upper": 0, "middle": 0, "lower": 0, "position": "中轨"}

        recent = closes[-period:]
        middle = sum(recent) / period
        std = (sum((x - middle)**2 for x in recent) / period) ** 0.5
        upper = middle + num_std * std
        lower = middle - num_std * std

        current = closes[-1]
        if current > upper:
            pos = "超买(上轨之上)"
        elif current > middle:
            pos = "中轨之上"
        elif current > lower:
            pos = "中轨之下"
        else:
            pos = "超卖(下轨之下)"

        return {"upper": round(upper, 2), "middle": round(middle, 2), "lower": round(lower, 2), "position": pos}

    def analyze(self, closes, volumes=None):
        """完整技术分析"""
        if not closes or len(closes) < 30:
            return {"score": 5.0, "signals": [], "detail": "数据不足，无法进行完整技术分析"}

        ma5 = self.moving_average(closes, 5)
        ma10 = self.moving_average(closes, 10)
        ma20 = self.moving_average(closes, 20)
        ma60 = self.moving_average(closes, 60) if len(closes) >= 60 else None

        macd_result = self.macd(closes)
        rsi_val = self.rsi(closes)
        boll = self.bollinger(closes)

        current = closes[-1]
        signals = []
        score = 5.0  # 基准分

        # 趋势评分 (权重30%)
        trend_score = 5.0
        if ma5 and ma20:
            if ma5 > ma20:
                trend_score += 2
                signals.append("短期均线在长期之上，趋势偏多")
            else:
                trend_score -= 2
                signals.append("短期均线在长期之下，趋势偏空")

        if ma20 and ma60:
            if ma20 > ma60:
                trend_score += 1.5
            else:
                trend_score -= 1.5

        if current > (ma20 or current):
            trend_score += 0.5
        else:
            trend_score -= 0.5

        trend_score = max(0, min(10, trend_score))

        # 动量评分 (权重25%)
        momentum_score = 5.0
        if "多头" in macd_result["signal"] or "金叉" in macd_result["signal"]:
            momentum_score += 2.5
            signals.append(f"MACD {macd_result['signal']}")
        elif "空头" in macd_result["signal"] or "死叉" in macd_result["signal"]:
            momentum_score -= 2.5
            signals.append(f"MACD {macd_result['signal']}")

        momentum_score = max(0, min(10, momentum_score))

        # RSI评分 (权重20%)
        rsi_score = 5.0
        if rsi_val < 30:
            rsi_score = 9.0
            signals.append(f"RSI={rsi_val} 超卖区域，可能反弹")
        elif rsi_val < 40:
            rsi_score = 7.5
        elif rsi_val < 60:
            rsi_score = 5.5
        elif rsi_val < 70:
            rsi_score = 4.0
        else:
            rsi_score = 2.0
            signals.append(f"RSI={rsi_val} 超买区域，注意回调")

        # 量价评分 (权重25%)
        vol_score = 5.0
        if volumes and len(volumes) >= 5:
            avg_vol = sum(volumes[-5:]) / 5
            prev_avg = sum(volumes[-10:-5]) / 5 if len(volumes) >= 10 else avg_vol
            vol_ratio = avg_vol / prev_avg if prev_avg > 0 else 1

            price_up = closes[-1] > closes[-5] if len(closes) >= 5 else False
            if price_up and vol_ratio > 1.2:
                vol_score = 8.5
                signals.append("放量上涨，量价配合良好")
            elif price_up and vol_ratio < 0.8:
                vol_score = 6.0
                signals.append("缩量上涨，上攻动力可能不足")
            elif not price_up and vol_ratio > 1.5:
                vol_score = 2.5
                signals.append("放量下跌，空方力量强")
            elif not price_up and vol_ratio < 0.8:
                vol_score = 5.5
                signals.append("缩量下跌，抛压减弱")

        # 加权综合
        total_score = (
            trend_score * 0.30 +
            momentum_score * 0.25 +
            rsi_score * 0.20 +
            vol_score * 0.25
        )

        # 支撑/阻力位
        support = boll["lower"]
        resistance = boll["upper"]
        if ma60:
            support = min(support, ma60) if support > 0 else ma60

        return {
            "score": round(total_score, 1),
            "trend_score": round(trend_score, 1),
            "momentum_score": round(momentum_score, 1),
            "rsi_score": round(rsi_score, 1),
            "volume_score": round(vol_score, 1),
            "signals": signals,
            "indicators": {
                "ma5": round(ma5, 2) if ma5 else None,
                "ma20": round(ma20, 2) if ma20 else None,
                "ma60": round(ma60, 2) if ma60 else None,
                "macd": macd_result,
                "rsi": rsi_val,
                "bollinger": boll,
            },
            "support": round(support, 2),
            "resistance": round(resistance, 2),
        }

# ============================================================
# 评分引擎
# ============================================================

class ScoringEngine:
    """五维评分系统"""

    WEIGHT_PROFILES = {
        "保守": {"fundamental": 0.35, "technical": 0.15, "news": 0.15, "capital": 0.15, "macro": 0.20},
        "稳健": {"fundamental": 0.30, "technical": 0.20, "news": 0.15, "capital": 0.20, "macro": 0.15},
        "激进": {"fundamental": 0.20, "technical": 0.30, "news": 0.15, "capital": 0.25, "macro": 0.10},
    }

    def __init__(self, mode="稳健"):
        self.weights = self.WEIGHT_PROFILES.get(mode, self.WEIGHT_PROFILES["稳健"])
        self.ta = TechnicalAnalyzer()

    def score_fundamental(self, data):
        """基本面评分"""
        score = 5.0
        reasons = []

        # ROE
        roe = data.get("roe", 0)
        if roe > 20:
            score += 2.0
            reasons.append(f"ROE {roe:.1f}% 优秀")
        elif roe > 15:
            score += 1.0
            reasons.append(f"ROE {roe:.1f}% 良好")
        elif roe < 8:
            score -= 2.0
            reasons.append(f"ROE {roe:.1f}% 偏低")

        # PE估值
        pe = data.get("pe_trailing", 0) or data.get("pe", 0)
        if pe > 0:
            if pe < 12:
                score += 1.5
                reasons.append(f"PE {pe:.1f} 估值偏低")
            elif pe < 20:
                score += 0.5
            elif pe > 40:
                score -= 1.5
                reasons.append(f"PE {pe:.1f} 估值偏高")
            elif pe > 30:
                score -= 0.5

        # 利润率
        gm = data.get("gross_margin", 0)
        if gm > 50:
            score += 1.0
            reasons.append(f"毛利率 {gm:.1f}% 高壁垒")
        elif gm > 30:
            score += 0.5

        # 营收增长
        rg = data.get("revenue_growth", 0)
        if rg > 20:
            score += 1.0
            reasons.append(f"营收增长 {rg:.1f}%")
        elif rg < -5:
            score -= 1.0
            reasons.append(f"营收下滑 {rg:.1f}%")

        # 负债
        dte = data.get("debt_to_equity", 0)
        if dte > 200:
            score -= 1.5
            reasons.append(f"负债率偏高 D/E={dte:.0f}%")
        elif dte < 50:
            score += 0.5

        score = max(0, min(10, score))
        return {"score": round(score, 1), "reasons": reasons}

    def score_technical(self, closes, volumes=None):
        """技术面评分"""
        return self.ta.analyze(closes, volumes)

    def score_news(self, news_data=None):
        """消息面评分（简化版，依赖外部传入）"""
        if not news_data:
            return {"score": 5.0, "reasons": ["无最新消息数据"]}

        score = safe_float(news_data.get("sentiment_score", 5.0))
        reasons = news_data.get("reasons", [])
        return {"score": max(0, min(10, score)), "reasons": reasons}

    def score_capital(self, capital_data=None):
        """资金面评分"""
        if not capital_data:
            return {"score": 5.0, "reasons": ["无资金流向数据"]}

        score = 5.0
        reasons = []

        north_flow = capital_data.get("northbound_net", 0)
        if north_flow > 50:  # 亿
            score += 2.0
            reasons.append(f"北向资金净流入 {north_flow:.1f}亿")
        elif north_flow > 0:
            score += 1.0
            reasons.append(f"北向资金小幅净流入 {north_flow:.1f}亿")
        elif north_flow < -50:
            score -= 2.0
            reasons.append(f"北向资金大幅净流出 {north_flow:.1f}亿")
        elif north_flow < 0:
            score -= 1.0

        return {"score": max(0, min(10, score)), "reasons": reasons}

    def score_macro(self, macro, asset_type="stock"):
        """宏观面评分"""
        score = 5.0
        reasons = []

        vix = macro.get("vix", 20)
        us10y = macro.get("us10y", 4.0)
        dxy_chg = macro.get("dxy_change", 0)

        # 确定象限
        quadrant = self.determine_quadrant(macro)
        reasons.append(f"宏观象限: {quadrant}")

        # 根据象限给股票打分
        quadrant_scores = {
            "金发女孩": 9, "过热": 5, "衰退": 3, "滞胀": 2
        }
        score = quadrant_scores.get(quadrant, 5)

        # VIX修正
        if vix > 30:
            score -= 2
            reasons.append(f"VIX={vix:.1f} 极度恐慌")
        elif vix > 25:
            score -= 1
            reasons.append(f"VIX={vix:.1f} 市场恐慌")
        elif vix < 15:
            score += 0.5
            reasons.append(f"VIX={vix:.1f} 市场平静")

        # 美元修正（对港股/A股额外影响）
        if abs(dxy_chg) > 0.5:
            if dxy_chg > 0:
                score -= 0.5
                reasons.append("美元走强，新兴市场承压")
            else:
                score += 0.5

        score = max(0, min(10, score))
        return {"score": round(score, 1), "reasons": reasons, "quadrant": quadrant}

    def determine_quadrant(self, macro):
        """判断达里奥四象限"""
        # 简化判断逻辑
        vix = macro.get("vix", 20)
        us10y = macro.get("us10y", 4.0)
        sp500_chg = macro.get("sp500_chg", 0)
        cpi = macro.get("cpi", 3.0)
        unemployment = macro.get("unemployment", 4.0)

        # 增长信号
        growth_signals = 0
        if sp500_chg > 0:
            growth_signals += 1
        if vix < 20:
            growth_signals += 1
        if unemployment < 4.5:
            growth_signals += 1

        growth_positive = growth_signals >= 2

        # 通胀信号
        inflation_signals = 0
        if us10y > 4.5:
            inflation_signals += 1
        if cpi > 3.0:
            inflation_signals += 1

        inflation_positive = inflation_signals >= 1

        if growth_positive and inflation_positive:
            return "过热"
        elif growth_positive and not inflation_positive:
            return "金发女孩"
        elif not growth_positive and inflation_positive:
            return "滞胀"
        else:
            return "衰退"

    def calculate_composite(self, fundamental, technical, news, capital, macro):
        """计算综合评分"""
        scores = {
            "fundamental": fundamental["score"],
            "technical": technical["score"],
            "news": news["score"],
            "capital": capital["score"],
            "macro": macro["score"],
        }

        composite = sum(scores[k] * self.weights[k] for k in scores)

        return {
            "composite": round(composite, 2),
            "scores": {k: round(v, 1) for k, v in scores.items()},
            "weights": self.weights,
        }

# ============================================================
# 交易建议生成器
# ============================================================

class TradingAdvisor:
    """生成交易操作建议，基于trading-rules.json配置"""

    DEFAULT_ACTIONS = {
        (9, 10): ("强烈买入/加仓", "🔥"),
        (8, 9): ("买入/加仓", "📈"),
        (7, 8): ("持有/小幅加仓", "✅"),
        (6, 7): ("持有/观望", "⏸️"),
        (5, 6): ("观望/考虑减仓", "⚠️"),
        (4, 5): ("减仓", "📉"),
        (0, 4): ("清仓", "🔴"),
    }

    def __init__(self, risk_params, trading_rules=None):
        self.risk_params = risk_params
        self.rules = trading_rules or {}
        self.buy_rules = self.rules.get("买入规则", {})
        self.sell_rules = self.rules.get("卖出规则", {})
        self.hold_rules = self.rules.get("持有规则", {})
        self.clear_rules = self.rules.get("清仓规则", {})

    def get_action(self, score, pnl_pct=0, fundamental_score=5, news_score=5, quadrant=""):
        """基于交易规则判断操作，优先级：清仓 > 卖出 > 买入 > 持有"""

        # 1. 清仓规则检查（最高优先级）
        for rule in self.clear_rules.get("conditions", []):
            if not rule.get("启用", True):
                continue
            if rule["id"] == "C1" and pnl_pct <= self.risk_params.get("stop_loss_pct", -0.08) * 150:
                return "强制清仓", "🔴"
            if rule["id"] == "C2" and fundamental_score < 3.0:
                return "清仓(基本面崩塌)", "🔴"
            if rule["id"] == "C3" and news_score < 2.0:
                return "清仓(黑天鹅)", "🔴"
            if rule["id"] == "C4" and score < 4.0:
                return "清仓", "🔴"

        # 2. 卖出规则检查
        for rule in self.sell_rules.get("conditions", []):
            if not rule.get("启用", True):
                continue
            if rule["id"] == "S1" and pnl_pct <= self.risk_params.get("stop_loss_pct", -0.08) * 100:
                return "触发止损-减仓", "📉"
            if rule["id"] == "S2" and fundamental_score < 5.0:
                return "减仓(基本面恶化)", "📉"
            if rule["id"] == "S4" and quadrant == "滞胀" and score < 5.0:
                return "减仓(滞胀环境)", "📉"
            if rule["id"] == "S5" and score < 5.0:
                return "观望/考虑减仓", "⚠️"

        # 3. 买入规则检查
        buy_conditions = self.buy_rules.get("conditions", [])
        buy_pass = True
        for rule in buy_conditions:
            if not rule.get("启用", True):
                continue
            if rule["id"] == "B1" and score < 7.5:
                buy_pass = False
            if rule["id"] == "B2" and fundamental_score < 7.0:
                buy_pass = False

        if buy_pass and score >= 7.5:
            if score >= 9:
                return "强烈买入/加仓", "🔥"
            elif score >= 8:
                return "买入/加仓", "📈"
            else:
                return "持有/小幅加仓", "✅"

        # 4. 持有规则（默认）
        if score >= 6:
            return "持有/观望", "⏸️"

        # 5. 兜底
        for (lo, hi), (action, emoji) in self.DEFAULT_ACTIONS.items():
            if lo <= score < hi:
                return action, emoji
        return "观望", "⏸️"

    def generate_advice(self, holding, score_data, tech_data, current_price, macro_data):
        """生成单个标的的交易建议"""
        composite = score_data["composite"]
        fundamental_score = score_data["scores"].get("fundamental", 5)
        news_score = score_data["scores"].get("news", 5)
        quadrant = macro_data.get("quadrant", "")
        action, emoji = self.get_action(
            composite,
            pnl_pct=pct_change(holding.get("cost_price", 0), current_price) / 100 if holding.get("cost_price") else 0,
            fundamental_score=fundamental_score,
            news_score=news_score,
            quadrant=quadrant,
        )

        cost = holding.get("cost_price", 0)
        pnl_pct = pct_change(cost, current_price) if cost > 0 else 0

        # 仓位建议
        target_weight = holding.get("target_weight", 0.10)
        if composite >= 8:
            suggested_weight = min(target_weight * 1.3, self.risk_params.get("max_single_position", 0.15))
        elif composite >= 7:
            suggested_weight = target_weight
        elif composite >= 5:
            suggested_weight = target_weight * 0.7
        else:
            suggested_weight = 0  # 清仓

        # 止损/止盈
        stop_loss = self.risk_params.get("stop_loss_pct", -0.08)
        stop_loss_price = cost * (1 + stop_loss) if cost > 0 else 0
        take_profit = self.risk_params.get("take_profit_pct", 0.30)
        take_profit_price = cost * (1 + take_profit) if cost > 0 else 0

        # 风险提示
        risks = []
        if pnl_pct < stop_loss * 100:
            risks.append(f"⚠️ 已触及止损线 ({stop_loss*100:.0f}%)")
        if pnl_pct > take_profit * 100:
            risks.append(f"💰 已达止盈目标 ({take_profit*100:.0f}%)")

        quadrant = macro_data.get("quadrant", "未知")
        if quadrant in ("滞胀", "衰退"):
            risks.append(f"⚠️ 宏观环境处于{quadrant}象限，建议降低仓位")

        return {
            "symbol": holding["symbol"],
            "name": holding.get("name", holding["symbol"]),
            "market": holding.get("market", ""),
            "current_price": current_price,
            "cost_price": cost,
            "pnl_pct": round(pnl_pct, 2),
            "composite_score": composite,
            "dimension_scores": score_data["scores"],
            "action": action,
            "action_emoji": emoji,
            "current_weight": target_weight,
            "suggested_weight": round(suggested_weight, 4),
            "stop_loss_price": round(stop_loss_price, 2),
            "take_profit_price": round(take_profit_price, 2),
            "support": tech_data.get("support", 0),
            "resistance": tech_data.get("resistance", 0),
            "tech_signals": tech_data.get("signals", []),
            "fundamental_reasons": score_data.get("fundamental_reasons", []),
            "risks": risks,
            "sector": holding.get("sector", ""),
        }

    def generate_portfolio_summary(self, advices, macro_data):
        """生成组合整体建议"""
        if not advices:
            return {"error": "无持仓数据"}

        avg_score = sum(a["composite_score"] for a in advices) / len(advices)
        quadrant = macro_data.get("quadrant", "未知")

        # 总仓位建议
        quadrant_position = {
            "金发女孩": 0.85,
            "过热": 0.65,
            "衰退": 0.45,
            "滞胀": 0.35,
        }
        suggested_total = quadrant_position.get(quadrant, 0.60)

        # 风险等级
        vix = macro_data.get("vix", 20)
        if vix > 30 or quadrant in ("滞胀",):
            risk_level = "高风险"
            risk_color = "red"
        elif vix > 20 or quadrant in ("过热", "衰退"):
            risk_level = "中等风险"
            risk_color = "orange"
        else:
            risk_level = "低风险"
            risk_color = "green"

        # 操作优先级排序
        actions = []
        for a in sorted(advices, key=lambda x: abs(x["suggested_weight"] - x["current_weight"]), reverse=True):
            weight_diff = a["suggested_weight"] - a["current_weight"]
            if abs(weight_diff) > 0.02:  # 超过2%差异才建议操作
                if weight_diff > 0:
                    actions.append(f"📈 {a['name']}({a['symbol']}): 加仓 {a['current_weight']*100:.0f}% → {a['suggested_weight']*100:.0f}%")
                else:
                    actions.append(f"📉 {a['name']}({a['symbol']}): 减仓 {a['current_weight']*100:.0f}% → {a['suggested_weight']*100:.0f}%")

        return {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "avg_score": round(avg_score, 2),
            "quadrant": quadrant,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "suggested_total_position": suggested_total,
            "cash_ratio": 1 - suggested_total,
            "actions": actions,
            "vix": macro_data.get("vix", 0),
            "holdings_count": len(advices),
        }


# ============================================================
# 主执行
# ============================================================

def main():
    print("=" * 60)
    print("🤖 AI交易助手 - 分析引擎启动")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 如果Excel模板比config新，先自动导入
    if os.path.exists(XLSX_PATH) and os.path.exists(CONFIG_PATH):
        xlsx_mtime = os.path.getmtime(XLSX_PATH)
        config_mtime = os.path.getmtime(CONFIG_PATH)
        if xlsx_mtime > config_mtime:
            print("📥 检测到Excel模板有更新，自动导入...")
            import subprocess
            subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "import_portfolio.py"), XLSX_PATH],
                          cwd=SKILL_DIR, capture_output=False)
            print()
    elif os.path.exists(XLSX_PATH) and not os.path.exists(CONFIG_PATH):
        print("📥 首次运行，从Excel模板导入持仓...")
        import subprocess
        subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, "import_portfolio.py"), XLSX_PATH],
                      cwd=SKILL_DIR, capture_output=False)
        print()

    # 加载配置
    if not os.path.exists(CONFIG_PATH):
        print(f"❌ 配置文件不存在: {CONFIG_PATH}")
        print("请先配置 portfolio-config.json 或填写 持仓录入模板.xlsx")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    # 加载交易规则
    trading_rules = {}
    if os.path.exists(RULES_PATH):
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            trading_rules = json.load(f)
        print(f"📏 已加载交易规则配置")

    mode = config.get("meta", {}).get("trading_mode", "稳健")
    risk_params = config.get("risk_params", {})
    holdings = config.get("portfolio", {}).get("holdings", [])
    watchlist = config.get("portfolio", {}).get("watchlist", [])
    api_keys = config.get("api_keys", {})

    print(f"\n📋 交易模式: {mode}")
    print(f"📊 持仓标的: {len(holdings)}个")
    print(f"👁️  关注列表: {len(watchlist)}个")

    # 初始化
    fetcher = DataFetcher(api_keys)
    scorer = ScoringEngine(mode)
    advisor = TradingAdvisor(risk_params, trading_rules)

    # 获取宏观数据
    print("\n🌍 获取宏观数据...")
    macro = fetcher.get_macro_data()
    # 预先计算宏观评分（即使无持仓数据也需要）
    macro_score = scorer.score_macro(macro)
    print(f"  VIX: {macro.get('vix', 'N/A')}")
    print(f"  US10Y: {macro.get('us10y', 'N/A')}")
    sp_chg = macro.get('sp500_chg', 0)
    print(f"  S&P500变化: {sp_chg if isinstance(sp_chg, str) else f'{sp_chg:.2f}'}%")

    # 获取北向资金
    print("\n💰 获取资金面数据...")
    northbound = fetcher.get_northbound_flow()
    print(f"  北向资金净流入: {northbound['total_net']:.2f}亿")

    # 分析每个持仓
    print("\n📊 分析持仓标的...")
    advices = []

    for h in holdings:
        symbol = h["symbol"]
        market = h["market"]
        print(f"\n  → 分析 {h.get('name', symbol)} ({symbol})...")

        # 获取数据
        stock_data = fetcher.get_stock_data(symbol, market)
        current_price = stock_data.get("price", 0)
        closes = stock_data.get("closes", [])
        volumes = stock_data.get("volumes", [])

        if current_price == 0:
            print(f"    ⚠️ 无法获取 {symbol} 的价格数据，跳过")
            continue

        print(f"    价格: {current_price} | 盈亏: {pct_change(h.get('cost_price', 0), current_price):.2f}%")

        # 五维评分
        fundamental = scorer.score_fundamental(stock_data)
        technical = scorer.score_technical(closes, volumes)
        news = scorer.score_news()  # 简化版
        capital = scorer.score_capital({"northbound_net": northbound["total_net"]})
        macro_score = scorer.score_macro(macro)

        composite = scorer.calculate_composite(fundamental, technical, news, capital, macro_score)
        composite["fundamental_reasons"] = fundamental["reasons"]

        print(f"    综合评分: {composite['composite']:.1f}/10")
        print(f"    基本面:{fundamental['score']:.1f} 技术:{technical['score']:.1f} 消息:{news['score']:.1f} 资金:{capital['score']:.1f} 宏观:{macro_score['score']:.1f}")

        # 生成建议
        advice = advisor.generate_advice(h, composite, technical, current_price, macro_score)
        advices.append(advice)
        print(f"    建议: {advice['action_emoji']} {advice['action']}")

    # 分析关注列表
    print("\n👁️  分析关注列表...")
    watchlist_advices = []

    for w in watchlist:
        symbol = w["symbol"]
        market = w["market"]
        print(f"\n  → 分析 {w.get('name', symbol)} ({symbol})...")

        stock_data = fetcher.get_stock_data(symbol, market)
        current_price = stock_data.get("price", 0)
        closes = stock_data.get("closes", [])
        volumes = stock_data.get("volumes", [])

        if current_price == 0:
            print(f"    ⚠️ 无法获取 {symbol} 的价格数据，跳过")
            continue

        target_entry = w.get("target_entry", 0)
        entry_signal = "未到建仓价" if current_price > target_entry and target_entry > 0 else "已到建仓区间"

        fundamental = scorer.score_fundamental(stock_data)
        technical = scorer.score_technical(closes, volumes)
        news = scorer.score_news()
        capital = scorer.score_capital({"northbound_net": northbound["total_net"]})
        macro_score = scorer.score_macro(macro)

        composite = scorer.calculate_composite(fundamental, technical, news, capital, macro_score)

        watchlist_advices.append({
            "symbol": symbol,
            "name": w.get("name", symbol),
            "market": market,
            "current_price": current_price,
            "target_entry": target_entry,
            "entry_signal": entry_signal,
            "composite_score": composite["composite"],
            "dimension_scores": composite["scores"],
            "reason": w.get("reason", ""),
            "tech_signals": technical.get("signals", []),
            "support": technical.get("support", 0),
            "resistance": technical.get("resistance", 0),
        })

        print(f"    现价: {current_price} | 目标建仓价: {target_entry} | {entry_signal}")
        print(f"    综合评分: {composite['composite']:.1f}/10")

    # 生成组合摘要
    portfolio_summary = advisor.generate_portfolio_summary(advices, macro_score)

    # 输出结果
    result = {
        "generated_at": datetime.now().isoformat(),
        "trading_mode": mode,
        "macro": {
            "quadrant": macro_score.get("quadrant", "未知"),
            "vix": macro.get("vix", 0),
            "us10y": macro.get("us10y", 0),
            "sp500": macro.get("sp500", 0),
            "sp500_chg": macro.get("sp500_chg", 0),
            "hsi": macro.get("hsi", 0),
            "hsi_chg": macro.get("hsi_chg", 0),
            "sse": macro.get("sse", 0),
            "sse_chg": macro.get("sse_chg", 0),
            "dxy": macro.get("dxy", 0),
            "fear_greed": macro.get("fear_greed", 50),
            "fear_greed_label": macro.get("fear_greed_label", "Neutral"),
            "northbound_net": northbound["total_net"],
        },
        "portfolio_summary": portfolio_summary,
        "holdings_advice": advices,
        "watchlist_advice": watchlist_advices,
    }

    # 保存结果
    output_path = os.path.join(SKILL_DIR, "latest_analysis.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析完成，结果已保存至: {output_path}")
    print(f"\n{'='*60}")
    print(f"📋 组合摘要")
    print(f"{'='*60}")
    print(f"宏观象限: {portfolio_summary.get('quadrant', '未知')}")
    print(f"风险等级: {portfolio_summary.get('risk_level', '未知')}")
    print(f"组合均分: {portfolio_summary.get('avg_score', 0):.1f}/10")
    print(f"建议总仓位: {portfolio_summary.get('suggested_total_position', 0)*100:.0f}%")
    print(f"建议现金比例: {portfolio_summary.get('cash_ratio', 0)*100:.0f}%")

    if portfolio_summary.get("actions"):
        print(f"\n🎯 待执行操作:")
        for action in portfolio_summary["actions"]:
            print(f"  {action}")

    return result


if __name__ == "__main__":
    result = main()
