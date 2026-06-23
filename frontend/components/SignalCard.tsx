import { Signal } from "@/lib/api";

const COLORS: Record<string, string> = {
  STRONG_BUY: "bg-bull/20 text-bull",
  BUY: "bg-bull/15 text-bull",
  NEUTRAL: "bg-gray-500/20 text-gray-300",
  SELL: "bg-bear/15 text-bear",
  STRONG_SELL: "bg-bear/20 text-bear",
};

export function SignalCard({ s }: { s: Signal }) {
  const color = COLORS[s.signal] || "bg-gray-500/20 text-gray-300";
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-bold">{s.symbol}</div>
          <div className="text-xs text-gray-500">
            Instrument: {s.instrument} · Score {s.score}/100
          </div>
        </div>
        <span className={`badge ${color} text-sm`}>{s.signal.replace("_", " ")}</span>
      </div>

      <div className="mt-3">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Confidence</span>
          <span>{s.confidence}%</span>
        </div>
        <div className="h-2 rounded bg-panel2 overflow-hidden">
          <div
            className="h-full bg-accent"
            style={{ width: `${Math.min(100, s.confidence)}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mt-4 text-sm">
        <Stat label="Entry" value={`₹${s.entry}`} />
        <Stat label="Stop Loss" value={`₹${s.stop_loss}`} tone="bear" />
        <Stat label="Target 1" value={`₹${s.target1}`} tone="bull" />
        <Stat label="Target 2" value={`₹${s.target2}`} tone="bull" />
      </div>
      <div className="mt-3 text-xs text-gray-400">
        Risk : Reward <span className="text-white font-semibold">{s.risk_reward}</span>
      </div>
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
