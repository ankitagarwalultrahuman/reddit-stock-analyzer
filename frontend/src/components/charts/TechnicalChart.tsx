"use client";

import { useEffect, useRef } from "react";
import { createChart, type IChartApi, CandlestickSeries, LineSeries, HistogramSeries } from "lightweight-charts";

interface OHLCData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface Props {
  data: OHLCData[];
  ema20?: number[];
  ema50?: number[];
  bbUpper?: number[];
  bbLower?: number[];
  height?: number;
  showRSI?: boolean;
  showMACD?: boolean;
}

/** Compute EMA from close prices */
function computeEMA(closes: number[], period: number): number[] {
  const result: number[] = [];
  const k = 2 / (period + 1);
  let ema = 0;
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      result.push(0);
    } else if (i === period - 1) {
      // SMA for initial value
      let sum = 0;
      for (let j = 0; j < period; j++) sum += closes[i - j];
      ema = sum / period;
      result.push(ema);
    } else {
      ema = closes[i] * k + ema * (1 - k);
      result.push(ema);
    }
  }
  return result;
}

/** Compute RSI */
function computeRSI(closes: number[], period = 14): number[] {
  const result: number[] = new Array(closes.length).fill(0);
  if (closes.length < period + 1) return result;

  let avgGain = 0;
  let avgLoss = 0;

  for (let i = 1; i <= period; i++) {
    const change = closes[i] - closes[i - 1];
    if (change > 0) avgGain += change;
    else avgLoss += Math.abs(change);
  }
  avgGain /= period;
  avgLoss /= period;

  result[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    const gain = change > 0 ? change : 0;
    const loss = change < 0 ? Math.abs(change) : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    result[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return result;
}

/** Compute MACD (12, 26, 9) */
function computeMACD(closes: number[]): { macd: number[]; signal: number[]; histogram: number[] } {
  const ema12 = computeEMA(closes, 12);
  const ema26 = computeEMA(closes, 26);
  const macd = closes.map((_, i) => (ema12[i] && ema26[i] ? ema12[i] - ema26[i] : 0));
  const signal = computeEMA(macd.map((v) => v || 0), 9);
  const histogram = macd.map((v, i) => v - (signal[i] || 0));
  return { macd, signal, histogram };
}

/** Compute Bollinger Bands (20, 2) */
function computeBB(closes: number[], period = 20, mult = 2): { upper: number[]; lower: number[] } {
  const upper: number[] = [];
  const lower: number[] = [];
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) {
      upper.push(0);
      lower.push(0);
    } else {
      const slice = closes.slice(i - period + 1, i + 1);
      const mean = slice.reduce((a, b) => a + b, 0) / period;
      const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / period;
      const std = Math.sqrt(variance);
      upper.push(mean + mult * std);
      lower.push(mean - mult * std);
    }
  }
  return { upper, lower };
}

const CHART_BG = "#ffffff";
const GRID_COLOR = "#f0f0f0";

export default function TechnicalChart({
  data,
  ema20: propsEma20,
  ema50: propsEma50,
  bbUpper: propsBbUpper,
  bbLower: propsBbLower,
  height = 400,
  showRSI = false,
  showMACD = false,
}: Props) {
  const mainRef = useRef<HTMLDivElement>(null);
  const rsiRef = useRef<HTMLDivElement>(null);
  const macdRef = useRef<HTMLDivElement>(null);
  const chartsRef = useRef<IChartApi[]>([]);

  useEffect(() => {
    if (!mainRef.current || data.length === 0) return;

    // Cleanup previous
    chartsRef.current.forEach((c) => c.remove());
    chartsRef.current = [];

    const closes = data.map((d) => d.close);

    // Client-side computed overlays (only if not provided as props)
    const ema20 = propsEma20 ?? computeEMA(closes, 20);
    const ema50 = propsEma50 ?? computeEMA(closes, 50);
    const bb = propsBbUpper && propsBbLower ? { upper: propsBbUpper, lower: propsBbLower } : computeBB(closes);

    // ======= MAIN CHART =======
    const mainChart = createChart(mainRef.current, {
      width: mainRef.current.clientWidth,
      height,
      layout: { background: { color: CHART_BG }, textColor: "#333" },
      grid: { vertLines: { color: GRID_COLOR }, horzLines: { color: GRID_COLOR } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#e5e7eb" },
      timeScale: { borderColor: "#e5e7eb" },
    });
    chartsRef.current.push(mainChart);

    // Candlestick
    const candleSeries = mainChart.addSeries(CandlestickSeries, {
      upColor: "#22c55e", downColor: "#ef4444",
      borderUpColor: "#22c55e", borderDownColor: "#ef4444",
      wickUpColor: "#22c55e", wickDownColor: "#ef4444",
    });
    candleSeries.setData(data.map((d) => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close })));

    // EMA 20
    if (ema20.length === data.length) {
      const ema20S = mainChart.addSeries(LineSeries, { color: "#3b82f6", lineWidth: 1, priceLineVisible: false });
      ema20S.setData(data.map((d, i) => ({ time: d.time, value: ema20[i] })).filter((d) => d.value));
    }

    // EMA 50
    if (ema50.length === data.length) {
      const ema50S = mainChart.addSeries(LineSeries, { color: "#f59e0b", lineWidth: 1, priceLineVisible: false });
      ema50S.setData(data.map((d, i) => ({ time: d.time, value: ema50[i] })).filter((d) => d.value));
    }

    // Bollinger Bands
    if (bb.upper.length === data.length) {
      const bbUS = mainChart.addSeries(LineSeries, { color: "rgba(156,163,175,0.5)", lineWidth: 1, priceLineVisible: false, lineStyle: 2 });
      bbUS.setData(data.map((d, i) => ({ time: d.time, value: bb.upper[i] })).filter((d) => d.value));
      const bbLS = mainChart.addSeries(LineSeries, { color: "rgba(156,163,175,0.5)", lineWidth: 1, priceLineVisible: false, lineStyle: 2 });
      bbLS.setData(data.map((d, i) => ({ time: d.time, value: bb.lower[i] })).filter((d) => d.value));
    }

    // Volume
    if (data.some((d) => d.volume)) {
      const volS = mainChart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "volume" });
      mainChart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      volS.setData(data.map((d) => ({ time: d.time, value: d.volume ?? 0, color: d.close >= d.open ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)" })));
    }

    mainChart.timeScale().fitContent();

    // ======= RSI SUB-PANEL =======
    if (showRSI && rsiRef.current) {
      const rsiChart = createChart(rsiRef.current, {
        width: rsiRef.current.clientWidth,
        height: 120,
        layout: { background: { color: CHART_BG }, textColor: "#333" },
        grid: { vertLines: { color: GRID_COLOR }, horzLines: { color: GRID_COLOR } },
        rightPriceScale: { borderColor: "#e5e7eb" },
        timeScale: { visible: false },
      });
      chartsRef.current.push(rsiChart);

      const rsiValues = computeRSI(closes);
      const rsiS = rsiChart.addSeries(LineSeries, { color: "#8b5cf6", lineWidth: 2, priceLineVisible: false });
      rsiS.setData(data.map((d, i) => ({ time: d.time, value: rsiValues[i] })).filter((_, i) => rsiValues[i] > 0));

      // 70/30 lines
      const line70 = rsiChart.addSeries(LineSeries, { color: "rgba(239,68,68,0.4)", lineWidth: 1, priceLineVisible: false, lineStyle: 2 });
      line70.setData(data.map((d) => ({ time: d.time, value: 70 })));
      const line30 = rsiChart.addSeries(LineSeries, { color: "rgba(34,197,94,0.4)", lineWidth: 1, priceLineVisible: false, lineStyle: 2 });
      line30.setData(data.map((d) => ({ time: d.time, value: 30 })));

      rsiChart.timeScale().fitContent();

      // Sync time scales
      mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) rsiChart.timeScale().setVisibleLogicalRange(range);
      });
    }

    // ======= MACD SUB-PANEL =======
    if (showMACD && macdRef.current) {
      const macdChart = createChart(macdRef.current, {
        width: macdRef.current.clientWidth,
        height: 120,
        layout: { background: { color: CHART_BG }, textColor: "#333" },
        grid: { vertLines: { color: GRID_COLOR }, horzLines: { color: GRID_COLOR } },
        rightPriceScale: { borderColor: "#e5e7eb" },
        timeScale: { visible: false },
      });
      chartsRef.current.push(macdChart);

      const macdData = computeMACD(closes);

      // MACD line
      const macdLine = macdChart.addSeries(LineSeries, { color: "#3b82f6", lineWidth: 2, priceLineVisible: false });
      macdLine.setData(data.map((d, i) => ({ time: d.time, value: macdData.macd[i] })).filter((_, i) => i >= 25));

      // Signal line
      const signalLine = macdChart.addSeries(LineSeries, { color: "#f59e0b", lineWidth: 1, priceLineVisible: false });
      signalLine.setData(data.map((d, i) => ({ time: d.time, value: macdData.signal[i] })).filter((_, i) => i >= 33));

      // Histogram
      const histS = macdChart.addSeries(HistogramSeries, { priceLineVisible: false });
      histS.setData(
        data.map((d, i) => ({
          time: d.time,
          value: macdData.histogram[i],
          color: macdData.histogram[i] >= 0 ? "rgba(34,197,94,0.6)" : "rgba(239,68,68,0.6)",
        })).filter((_, i) => i >= 25)
      );

      macdChart.timeScale().fitContent();

      // Sync time scales
      mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (range) macdChart.timeScale().setVisibleLogicalRange(range);
      });
    }

    // Resize handling
    const handleResize = () => {
      chartsRef.current.forEach((chart, idx) => {
        const ref = idx === 0 ? mainRef : idx === 1 && showRSI ? rsiRef : macdRef;
        if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
      });
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chartsRef.current.forEach((c) => c.remove());
      chartsRef.current = [];
    };
  }, [data, propsEma20, propsEma50, propsBbUpper, propsBbLower, height, showRSI, showMACD]);

  return (
    <div className="space-y-0">
      <div ref={mainRef} />
      {showRSI && (
        <div>
          <p className="text-xs text-muted-foreground px-1 py-0.5">RSI (14)</p>
          <div ref={rsiRef} />
        </div>
      )}
      {showMACD && (
        <div>
          <p className="text-xs text-muted-foreground px-1 py-0.5">MACD (12, 26, 9)</p>
          <div ref={macdRef} />
        </div>
      )}
    </div>
  );
}
