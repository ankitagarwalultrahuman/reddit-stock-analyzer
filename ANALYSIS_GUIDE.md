# Stock Analysis Interpretation Guide

A comprehensive guide to interpreting results from the Reddit Stock Analyzer and making informed trading decisions.

---

## Table of Contents
1. [Technical Indicators](#1-technical-indicators)
2. [Reddit Sentiment Analysis](#2-reddit-sentiment-analysis)
3. [Sector Rotation](#3-sector-rotation)
4. [Watchlist Scanner Strategies](#4-watchlist-scanner-strategies)
5. [Combining Multiple Signals](#5-combining-multiple-signals-confluence)
6. [Risk Management](#6-risk-management)
7. [Common Patterns & Examples](#7-common-patterns--examples)

---

## 1. Technical Indicators

### RSI (Relative Strength Index)

**What it measures:** Momentum - whether a stock is overbought or oversold.

| RSI Value | Interpretation | Action Consideration |
|-----------|---------------|---------------------|
| 0-30 | **Oversold** - Stock may be undervalued | Potential buy opportunity (look for reversal confirmation) |
| 30-40 | Approaching oversold | Watch for entry if other signals align |
| 40-60 | **Neutral** - Normal trading range | No strong signal |
| 60-70 | Approaching overbought | Consider taking partial profits |
| 70-100 | **Overbought** - Stock may be overvalued | Potential sell/avoid buying (look for reversal) |

**Key insights:**
- RSI < 30 doesn't mean "buy immediately" - wait for RSI to turn upward
- RSI > 70 in a strong uptrend can stay overbought for extended periods
- Look for **RSI divergence**: Price makes new high but RSI doesn't = potential reversal

---

### MACD (Moving Average Convergence Divergence)

**What it measures:** Trend direction and momentum strength.

**Components:**
- **MACD Line** (blue): Difference between 12-day and 26-day EMA
- **Signal Line** (orange): 9-day EMA of MACD line
- **Histogram**: Difference between MACD and Signal line

| Signal | What it means | Action |
|--------|--------------|--------|
| MACD crosses ABOVE signal | **Bullish crossover** | Buy signal |
| MACD crosses BELOW signal | **Bearish crossover** | Sell signal |
| Histogram growing (positive) | Bullish momentum increasing | Hold/add to position |
| Histogram shrinking | Momentum weakening | Prepare for reversal |
| MACD above zero line | Overall bullish trend | Favor long positions |
| MACD below zero line | Overall bearish trend | Favor short/cash |

**Key insights:**
- Crossovers are more reliable when they occur far from the zero line
- **MACD divergence**: Price makes new high but MACD doesn't = potential reversal
- In ranging markets, MACD gives many false signals

---

### Moving Averages (EMA 20, 50, 200)

**What they measure:** Trend direction and support/resistance levels.

| Indicator | Timeframe | Use |
|-----------|-----------|-----|
| EMA 20 | Short-term | Day trading, quick trends |
| EMA 50 | Medium-term | Swing trading (days to weeks) |
| EMA 200 | Long-term | Investment decisions, major trend |

**Key signals:**

| Pattern | Interpretation |
|---------|---------------|
| Price > EMA 20 > EMA 50 > EMA 200 | **Strong uptrend** - Bullish |
| Price < EMA 20 < EMA 50 < EMA 200 | **Strong downtrend** - Bearish |
| EMA 50 crosses above EMA 200 | **Golden Cross** - Major bullish signal |
| EMA 50 crosses below EMA 200 | **Death Cross** - Major bearish signal |
| Price bounces off EMA 50/200 | These act as **support** in uptrends |
| Price rejected at EMA 50/200 | These act as **resistance** in downtrends |

---

### Bollinger Bands

**What they measure:** Volatility and potential price extremes.

| Position | Interpretation |
|----------|---------------|
| Price at upper band | Potentially overbought / strong momentum |
| Price at lower band | Potentially oversold / weak momentum |
| Bands widening | Volatility increasing |
| Bands narrowing (squeeze) | Low volatility - big move coming |
| Price breaks out of bands | Strong momentum in that direction |

**Key insights:**
- In trends, price can "ride" the upper/lower band for extended periods
- **Bollinger Squeeze** (narrow bands) often precedes significant moves
- Use with RSI: Price at lower band + RSI oversold = stronger buy signal

---

### ATR (Average True Range)

**What it measures:** Volatility - how much a stock typically moves.

**Uses:**
1. **Position sizing**: Higher ATR = more volatile = smaller position size
2. **Stop-loss placement**: Set stops 1.5-2x ATR below entry
3. **Profit targets**: Expect moves of 1-2x ATR

| ATR Interpretation | Example (Stock at ₹100) |
|-------------------|------------------------|
| ATR = 2 (2% of price) | Low volatility - tight stops, smaller moves |
| ATR = 5 (5% of price) | Medium volatility - normal trading |
| ATR = 10 (10% of price) | High volatility - wide stops, larger moves |

---

## 2. Reddit Sentiment Analysis

### Sentiment Categories

| Sentiment | Meaning | Typical Action |
|-----------|---------|---------------|
| **Bullish** (>60% positive) | Community expects price to rise | Consider buying if technicals agree |
| **Bearish** (>60% negative) | Community expects price to fall | Avoid or consider shorting |
| **Neutral** | Mixed opinions, no clear direction | Wait for clearer signals |
| **Mixed** | Strong opinions both ways | High uncertainty - be cautious |

### Interpreting Citation Counts

| Mentions | Interpretation |
|----------|---------------|
| 1-5 posts | Low interest - signal may be noise |
| 5-15 posts | Moderate interest - worth investigating |
| 15+ posts | High interest - significant community focus |

**Comments matter more than posts** - A post with 100+ comments shows real engagement.

### Sentiment Reliability Factors

**Higher reliability:**
- High citation count (many independent sources)
- Consistent sentiment across multiple subreddits
- Sentiment backed by fundamental/technical reasoning in posts
- Posts from r/IndiaInvestments (tends to be more analytical)

**Lower reliability:**
- Single post with few comments
- Emotional language ("rocket", "moon", "disaster")
- Pump-like patterns (sudden spike in positive mentions)
- Weekend/after-hours posts (less serious traders)

### Caution Flags

When the report shows **Caution Flags**, pay attention:
- **High Leverage Risks**: MTF/margin warnings
- **FOMO indicators**: People chasing momentum
- **Pump patterns**: Sudden coordinated positive sentiment
- **Emotional trading**: Fear/greed driven decisions

---

## 3. Sector Rotation

### Momentum Score (0-100)

| Score | Interpretation | Strategy |
|-------|---------------|----------|
| 70-100 | **Strong momentum** - Sector outperforming | Overweight this sector |
| 50-70 | **Moderate momentum** - Neutral | Market weight |
| 30-50 | **Weak momentum** - Underperforming | Underweight |
| 0-30 | **Very weak** - Significant decline | Avoid or look for bottom |

### Sector Trend Signals

| Trend | Meaning | Action |
|-------|---------|--------|
| **Gaining** | Momentum increasing | Rotate INTO this sector |
| **Neutral** | Stable, no clear direction | Hold current allocation |
| **Losing** | Momentum decreasing | Rotate OUT of this sector |

### Classic Sector Rotation (Economic Cycle)

```
Economic Cycle Position → Sectors That Typically Lead

Early Recovery:    Consumer Discretionary, Financials, Real Estate
Mid Expansion:     Technology, Industrials, Materials
Late Expansion:    Energy, Materials, Industrials
Early Recession:   Consumer Staples, Healthcare, Utilities
Full Recession:    Consumer Staples, Utilities (Defensive)
```

### Using Sector Data

1. **Check relative strength**: Which sectors beat NIFTY50?
2. **Look for rotation**: Money flowing from one sector to another
3. **Oversold sectors**: Low RSI + losing momentum = potential bounce
4. **Overbought sectors**: High RSI + slowing momentum = potential correction

---

## 4. Watchlist Scanner Strategies

### Strategy Descriptions

| Strategy | What it finds | Best for |
|----------|--------------|----------|
| **RSI Oversold** | Stocks with RSI < 35 | Contrarian buying |
| **RSI Overbought** | Stocks with RSI > 65 | Taking profits / shorting |
| **MACD Bullish** | Positive MACD crossover | Trend following (long) |
| **MACD Bearish** | Negative MACD crossover | Trend following (short) |
| **Trend Following** | Price > EMA50 + Bullish MACD | Momentum trading |
| **Mean Reversion** | RSI oversold + near lower Bollinger | Bounce plays |
| **Breakout** | Near upper Bollinger + high volume | Momentum breakouts |
| **Full Scan** | All stocks with technical data | Screening starting point |

### Interpreting Scanner Results

**Strong buy candidates show:**
- RSI: 30-45 (oversold but turning up)
- MACD: Bullish or about to cross
- Price: Near support (EMA or Bollinger lower)
- Technical Bias: "Bullish"

**Strong sell/avoid candidates show:**
- RSI: 65+ (overbought)
- MACD: Bearish or about to cross down
- Price: Near resistance
- Technical Bias: "Bearish"

---

## 5. Combining Multiple Signals (Confluence)

### The Confluence Principle

**More aligned signals = Higher probability trade**

Single signal accuracy: ~50-55%
Two aligned signals: ~60-65%
Three+ aligned signals: ~70%+

### Confluence Checklist for BUYING

Award 1 point for each:

| Factor | Bullish Condition | Points |
|--------|------------------|--------|
| RSI | Below 40 or rising from oversold | +1 |
| MACD | Bullish crossover or positive histogram | +1 |
| Moving Averages | Price above EMA50, or bouncing off EMA | +1 |
| Bollinger | Near lower band or breaking out of squeeze | +1 |
| Reddit Sentiment | Bullish with 5+ citations | +1 |
| Sector | Sector momentum > 50, gaining | +1 |
| Volume | Above average | +1 |

**Scoring:**
- 5-7 points: **Strong Buy** - High conviction
- 3-4 points: **Moderate Buy** - Proceed with caution
- 1-2 points: **Weak** - Wait for more confirmation
- 0 points: **Avoid** - No supporting evidence

### Confluence Checklist for SELLING

| Factor | Bearish Condition | Points |
|--------|------------------|--------|
| RSI | Above 70 or falling from overbought | +1 |
| MACD | Bearish crossover or negative histogram | +1 |
| Moving Averages | Price below EMA50, or rejected at EMA | +1 |
| Bollinger | Near upper band (in downtrend) | +1 |
| Reddit Sentiment | Bearish with 5+ citations | +1 |
| Sector | Sector momentum < 50, losing | +1 |
| Volume | High volume on down days | +1 |

### Real-World Confluence Examples

**Example 1: Strong Buy Setup**
```
Stock: TATAPOWER
- RSI: 32 (oversold) ✓
- MACD: Bullish crossover forming ✓
- Price: At 50-day EMA support ✓
- Reddit: Bullish (12 posts, 34 comments) ✓
- Sector (Energy): Momentum 58, gaining ✓
- Volume: 1.4x average ✓

Confluence Score: 6/7 = STRONG BUY
```

**Example 2: Avoid/Sell Setup**
```
Stock: XYZ
- RSI: 78 (overbought) ✓
- MACD: Bearish divergence ✓
- Price: At upper Bollinger, below EMA ✓
- Reddit: Bearish (8 posts, negative sentiment) ✓
- Sector: Momentum 35, losing ✓

Confluence Score: 5/7 = STRONG SELL/AVOID
```

**Example 3: Mixed Signals - WAIT**
```
Stock: ABC
- RSI: 55 (neutral)
- MACD: Bullish ✓
- Price: Between EMAs
- Reddit: Mixed sentiment
- Sector: Neutral

Confluence Score: 1-2/7 = WAIT for clarity
```

---

## 6. Risk Management

### Position Sizing Rules

| Conviction Level | Max Position Size |
|-----------------|------------------|
| High confluence (5+ signals) | 3-5% of portfolio |
| Moderate confluence (3-4 signals) | 1-2% of portfolio |
| Speculative (1-2 signals) | 0.5-1% of portfolio |

### Stop-Loss Guidelines

| Volatility (ATR%) | Stop-Loss Distance |
|-------------------|-------------------|
| Low (<2%) | 3-5% below entry |
| Medium (2-5%) | 5-8% below entry |
| High (>5%) | 8-12% below entry |

**Alternative: ATR-based stops**
- Conservative: 1.5 x ATR below entry
- Normal: 2 x ATR below entry
- Wide: 3 x ATR below entry

### When to Ignore Signals

**Don't trade when:**
1. Confluence score < 3 (insufficient confirmation)
2. Major news event pending (earnings, budget, RBI policy)
3. Market-wide panic or euphoria
4. You're emotionally compromised
5. Position would exceed risk limits

---

## 7. Common Patterns & Examples

### Pattern 1: Oversold Bounce

**Setup:**
- RSI < 30 and turning up
- Price at lower Bollinger Band
- MACD histogram improving (less negative)
- Sector not in freefall

**Entry:** When RSI crosses above 30
**Stop:** Below recent low or 2x ATR
**Target:** Middle Bollinger Band or EMA50

### Pattern 2: Trend Continuation

**Setup:**
- Price > EMA20 > EMA50
- RSI between 50-70
- MACD positive and histogram growing
- Sector momentum > 50

**Entry:** On pullback to EMA20
**Stop:** Below EMA50
**Target:** Previous high + ATR

### Pattern 3: Sentiment-Driven Move

**Setup:**
- Reddit sentiment shifts significantly (neutral → bullish)
- High citation count (15+ posts)
- Technical setup neutral or bullish
- No obvious pump patterns

**Entry:** Gradually, not all at once
**Stop:** If sentiment reverses or technicals break
**Target:** Re-evaluate as sentiment develops

### Pattern 4: Sector Rotation Play

**Setup:**
- Sector gaining momentum (score > 60)
- Individual stock in sector with good technicals
- Stock underperformed sector recently (catch-up potential)

**Entry:** When stock shows technical strength
**Stop:** If sector momentum reverses
**Target:** Sector average performance

---

## Quick Reference Card

### Bullish Signals
- RSI < 40 and rising
- MACD bullish crossover
- Price > EMA50, bouncing off EMA
- Near lower Bollinger Band
- Bullish Reddit sentiment (5+ citations)
- Sector momentum > 50, gaining

### Bearish Signals
- RSI > 60 and falling
- MACD bearish crossover
- Price < EMA50, rejected at EMA
- Near upper Bollinger Band (in downtrend)
- Bearish Reddit sentiment (5+ citations)
- Sector momentum < 50, losing

### Neutral/Wait
- RSI 40-60
- MACD near zero, no clear direction
- Price between EMAs
- Mixed Reddit sentiment
- Sector momentum ~50

---

## Disclaimer

This guide is for educational purposes only. Always:
1. Do your own research (DYOR)
2. Never invest more than you can afford to lose
3. Consider consulting a SEBI-registered financial advisor
4. Past patterns don't guarantee future results
5. Social media sentiment can be manipulated

---

*Generated for Reddit Stock Analyzer - Last updated: January 2026*
