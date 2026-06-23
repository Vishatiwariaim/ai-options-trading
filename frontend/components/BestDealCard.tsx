"use client";

import { BestDeal } from "@/lib/api";
import { PriceChart } from "./PriceChart";

const QUALITY_COLOR: Record<string, string> = {
  A: "bg-bull/20 text-bull",
  B: "bg-yellow-500/20 text-yellow-400",
  C: "bg-bear/20 text-bear",
};

export function BestDealCard({ deal }: { deal: BestDeal }) {
  const isCall = deal.instrument === "CE";
  const isPut = deal.instrument === "PE";
  const wait = deal.wait;

  const winColor = isCall ? "text-bull" : isPut ? "text-bear" : "text-gray-300";
  const actionColor = wait
    ? "bg-gray-500/20 text-gray-300"
    : isCall
    ? "bg-bull/20 text-bull"
    : "bg-bear/20 text-bear";

  return (
    <div className="card border-accent/40">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="text-xs uppercase tracking-wide text-accent">🤖 Aaj ka Best Deal — AI Agent v2</div>
          <div className="text-2xl font-bold mt-1">
            {deal.symbol} <span className="text-gray-500 text-base">· {deal.signal?.replace("_", " ")}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {deal.quality && (
            <span className={`badge ${QUALITY_COLOR[deal.quality] || ""} text-sm`} title="Setup quality grade">
              Grade {deal.quality}
            </span>
          )}
          <span className={`badge ${actionColor} text-base px-3 py-1`}>{deal.action}</span>
        </div>
      </div>

      {/* Signal-strength chips */}
      <div className="flex flex-wrap gap-2 mt-3">
        {deal.mtf_trend && (
          <Chip label="1h Trend" value={deal.mtf_trend} tone={deal.mtf_trend === "UP" ? "bull" : deal.mtf_trend === "DOWN" ? "bear" : "gray"} />
        )}
        {typeof deal.adx === "number" && (
          <Chip label="ADX" value={`${deal.adx} ${deal.adx >= 25 ? "(strong)" : deal.adx < 18 ? "(weak)" : ""}`} tone={deal.adx >= 25 ? "bull" : "gray"} />
        )}
        {deal.agreement && <Chip label="Agreement" value={deal.agreement} tone="gray" />}
        {typeof deal.expected_value === "number" && (
          <Chip label="Expected Value" value={`${deal.expected_value > 0 ? "+" : ""}${deal.expected_value}R`} tone={deal.expected_value > 0 ? "bull" : "bear"} />
        )}
      </div>

      {/* Win chance — the headline number */}
      {!wait && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-400 mb-1">
            <span>Paisa banne ka chance (probabilistic)</span>
            <span className={`font-bold ${winColor}`}>{deal.win_chance}%</span>
          </div>
          <div className="h-3 rounded bg-panel2 overflow-hidden">
            <div
              className={`h-full ${isCall ? "bg-bull" : "bg-bear"}`}
              style={{ width: `${Math.min(100, deal.win_chance)}%` }}
            />
          </div>
          <div className="text-[11px] text-gray-500 mt-1">
            Confidence {deal.confidence}% · score {deal.score}/100 · NOT a guarantee
          </div>
        </div>
      )}

      {wait && (
        <div className="mt-4 text-sm text-gray-300 bg-panel2 rounded-lg p-3">
          Agent ka verdict: <b>WAIT</b>. Abhi koi high-quality trade nahi — ya to trend weak hai (ADX kam),
          ya higher-timeframe ke against hai, ya expected value negative. Sabse accha trade lena = kab NA lena
          bhi pata ho. 🙏
        </div>
      )}

      {/* Reason */}
      <div className="mt-3 text-sm text-gray-400">
        <span className="text-gray-500">Why: </span>
        {deal.reason}
      </div>

      {/* Levels */}
      {!wait && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 text-sm">
            <Stat label="Entry" value={`₹${deal.entry}`} />
            <Stat label="Stop Loss" value={`₹${deal.stop_loss}`} tone="bear" />
            <Stat label="Target 1" value={`₹${deal.target1}`} tone="bull" />
            <Stat label="Target 2" value={`₹${deal.target2}`} tone="bull" />
          </div>
          <div className="mt-2 text-xs text-gray-400">
            Risk : Reward <span className="text-white font-semibold">{deal.risk_reward}</span>
          </div>
        </>
      )}

      {/* Chart */}
      {deal.candles && deal.candles.length > 0 && (
        <div className="mt-4">
          <div className="text-xs text-gray-500 mb-1">{deal.symbol} · 15m candles</div>
          <PriceChart candles={deal.candles} />
        </div>
      )}

      {/* Alternatives */}
      {deal.alternatives?.length > 0 && (
        <div className="mt-4">
          <div className="text-xs text-gray-500 mb-2">Other ranked setups (by expected value)</div>
          <div className="flex flex-wrap gap-2">
            {deal.alternatives.map((a) => (
              <span key={a.symbol} className="badge bg-panel2 text-gray-300 text-xs">
                {a.symbol} · {a.instrument}
                {a.quality ? ` · ${a.quality}` : ""}
                {typeof a.expected_value === "number" ? ` · EV ${a.expected_value}R` : ""}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 text-[11px] text-gray-600 leading-relaxed">{deal.disclaimer}</div>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  const c = tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : "text-white";
  return (
    <div className="bg-panel2 rounded-lg px-3 py-2">
      <div className="text-[11px] text-gray-500">{label}</div>
      <div className={`font-semibold ${c}`}>{value}</div>
    </div>
  );
}

function Chip({ label, value, tone }: { label: string; value: string; tone?: string }) {
  const c = tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : "text-gray-300";
  return (
    <span className="badge bg-panel2 text-xs">
      <span className="text-gray-500">{label}:</span> <span className={`font-semibold ${c}`}>{value}</span>
    </span>
  );
}
