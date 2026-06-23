"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";

export type Candle = {
  time: string; // "YYYY-MM-DD" or "YYYY-MM-DD HH:MM"
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

function toUnix(t: string): UTCTimestamp {
  // Interpret as UTC so intraday bars order correctly regardless of locale.
  return (Date.parse(t.replace(" ", "T") + "Z") / 1000) as UTCTimestamp;
}

export function PriceChart({
  candles,
  height = 280,
}: {
  candles: Candle[];
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || candles.length === 0) return;

    const chart: IChartApi = createChart(ref.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      timeScale: { timeVisible: true, borderColor: "rgba(255,255,255,0.1)" },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      crosshair: { mode: 1 },
      autoSize: true,
    });

    const series = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    // De-duplicate + sort by time (lightweight-charts requires strictly ascending).
    const seen = new Set<number>();
    const data = candles
      .map((c) => ({ time: toUnix(c.time), open: c.open, high: c.high, low: c.low, close: c.close }))
      .filter((c) => !Number.isNaN(c.time))
      .sort((a, b) => (a.time as number) - (b.time as number))
      .filter((c) => (seen.has(c.time as number) ? false : (seen.add(c.time as number), true)));

    series.setData(data);
    chart.timeScale().fitContent();

    return () => chart.remove();
  }, [candles, height]);

  if (candles.length === 0) {
    return <div className="text-gray-500 text-sm">No chart data.</div>;
  }
  return <div ref={ref} style={{ width: "100%", height }} />;
}
