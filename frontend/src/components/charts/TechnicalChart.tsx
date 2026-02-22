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
}

export default function TechnicalChart({ data, ema20, ema50, bbUpper, bbLower, height = 400 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#333",
      },
      grid: {
        vertLines: { color: "#f0f0f0" },
        horzLines: { color: "#f0f0f0" },
      },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: "#e5e7eb" },
      timeScale: { borderColor: "#e5e7eb" },
    });
    chartRef.current = chart;

    // Candlestick
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });
    candleSeries.setData(
      data.map((d) => ({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    // EMA 20
    if (ema20 && ema20.length === data.length) {
      const ema20Series = chart.addSeries(LineSeries, {
        color: "#3b82f6",
        lineWidth: 1,
        priceLineVisible: false,
      });
      ema20Series.setData(
        data.map((d, i) => ({ time: d.time, value: ema20[i] })).filter((d) => d.value)
      );
    }

    // EMA 50
    if (ema50 && ema50.length === data.length) {
      const ema50Series = chart.addSeries(LineSeries, {
        color: "#f59e0b",
        lineWidth: 1,
        priceLineVisible: false,
      });
      ema50Series.setData(
        data.map((d, i) => ({ time: d.time, value: ema50[i] })).filter((d) => d.value)
      );
    }

    // Bollinger Bands
    if (bbUpper && bbLower && bbUpper.length === data.length) {
      const bbUpperSeries = chart.addSeries(LineSeries, {
        color: "rgba(156, 163, 175, 0.5)",
        lineWidth: 1,
        priceLineVisible: false,
        lineStyle: 2,
      });
      bbUpperSeries.setData(
        data.map((d, i) => ({ time: d.time, value: bbUpper[i] })).filter((d) => d.value)
      );

      const bbLowerSeries = chart.addSeries(LineSeries, {
        color: "rgba(156, 163, 175, 0.5)",
        lineWidth: 1,
        priceLineVisible: false,
        lineStyle: 2,
      });
      bbLowerSeries.setData(
        data.map((d, i) => ({ time: d.time, value: bbLower[i] })).filter((d) => d.value)
      );
    }

    // Volume
    if (data.some((d) => d.volume)) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      volumeSeries.setData(
        data.map((d) => ({
          time: d.time,
          value: d.volume ?? 0,
          color: d.close >= d.open ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)",
        }))
      );
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, ema20, ema50, bbUpper, bbLower, height]);

  return <div ref={containerRef} />;
}
