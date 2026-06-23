"use client";

import { useEffect, useState } from "react";
import { api, Signal } from "@/lib/api";
import { SignalCard } from "@/components/SignalCard";

type ScanRow = Signal;
type Prediction = {
  source: string;
  note: string;
  predictions: Record<string, { bullish: number; bearish: number }>;
};

export default function SignalsPage() {
  const [rows, setRows] = useState<ScanRow[]>([]);
  const [selected, setSelected] = useState<string>("NIFTY");
  const [detail, setDetail] = useState<Signal | null>(null);
  const [pred, setPred] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<{ results: ScanRow[] }>("/api/signals")
      .then((d) => setRows(d.results.filter((r: any) => !r.error)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setDetail(null);
    setPred(null);
    api.get<Signal>(`/api/signals/${selected}`).then(setDetail);
    api.get<Prediction>(`/api/signals/${selected}/prediction`).then(setPred);
  }, [selected]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">AI Trading Signals</h1>
      <p className="text-gray-400 text-sm mb-6">
        4-layer weighted scoring (indicators · price action · SMC · options) + ML ensemble.
        Probabilistic — not financial advice.
      </p>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <h2 className="font-semibold mb-2">Market Scan</h2>
          {loading ? (
            <div className="text-gray-400">Scanning…</div>
          ) : (
            <div className="space-y-2">
              {rows.map((r) => (
                <button
                  key={r.symbol}
                  onClick={() => setSelected(r.symbol)}
                  className={`card w-full text-left flex items-center justify-between ${
                    selected === r.symbol ? "border-accent/60" : ""
                  }`}
                >
                  <div>
                    <div className="font-semibold">{r.symbol}</div>
                    <div className="text-xs text-gray-500">{r.risk_reward}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold">{r.signal.replace("_", " ")}</div>
                    <div className="text-xs text-gray-500">{r.score}/100</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2 space-y-4">
          {detail && <SignalCard s={detail} />}

          {pred && (
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">ML Prediction (multi-horizon)</h3>
                <span className="badge bg-panel2 text-gray-400">{pred.source}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {Object.entries(pred.predictions).map(([h, p]) => (
                  <div key={h} className="bg-panel2 rounded-lg p-3">
                    <div className="text-xs text-gray-500 uppercase">{h}</div>
                    <div className="text-bull text-sm mt-1">Bullish {p.bullish}%</div>
                    <div className="text-bear text-sm">Bearish {p.bearish}%</div>
                  </div>
                ))}
              </div>
              <div className="text-xs text-gray-500 mt-3">{pred.note}</div>
            </div>
          )}

          {detail?.breakdown && (
            <div className="card">
              <h3 className="font-semibold mb-3">Score Breakdown</h3>
              <div className="space-y-2 text-sm">
                {["layer1_indicators", "layer2_price_action", "layer3_smc", "layer4_options", "sentiment"].map(
                  (k) => {
                    const b = detail.breakdown[k];
                    if (!b) return null;
                    return (
                      <div key={k}>
                        <div className="flex justify-between text-xs text-gray-400 mb-1">
                          <span>{k.replace(/_/g, " ")}</span>
                          <span>
                            {b.score} / {b.weight}
                          </span>
                        </div>
                        <div className="h-2 rounded bg-panel2 overflow-hidden">
                          <div
                            className="h-full bg-accent"
                            style={{ width: `${Math.min(100, (b.score / b.weight) * 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  }
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
