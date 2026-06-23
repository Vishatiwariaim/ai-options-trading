"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Row = {
  strike: number;
  ce_oi: number;
  ce_chg_oi: number;
  ce_ltp: number;
  pe_oi: number;
  pe_chg_oi: number;
  pe_ltp: number;
};
type Chain = {
  symbol: string;
  spot: number;
  pcr: number;
  max_pain: number;
  support: number[];
  resistance: number[];
  bias: string;
  total_ce_oi: number;
  total_pe_oi: number;
  rows: Row[];
};

const SYMBOLS = ["NIFTY", "BANKNIFTY", "FINNIFTY"];

export default function OptionChainPage() {
  const [sym, setSym] = useState("NIFTY");
  const [data, setData] = useState<Chain | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get<Chain>(`/api/market/option-chain/${sym}`)
      .then(setData)
      .finally(() => setLoading(false));
  }, [sym]);

  const maxOi = data ? Math.max(...data.rows.flatMap((r) => [r.ce_oi, r.pe_oi]), 1) : 1;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Option Chain Analyzer</h1>
      <p className="text-gray-400 text-sm mb-4">
        OI, ΔOI, PCR, Max Pain & OI-based support/resistance.
      </p>

      <div className="flex gap-2 mb-4">
        {SYMBOLS.map((s) => (
          <button
            key={s}
            onClick={() => setSym(s)}
            className={sym === s ? "btn" : "btn-ghost"}
          >
            {s}
          </button>
        ))}
      </div>

      {loading || !data ? (
        <div className="text-gray-400">Loading option chain…</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
            <Metric label="Spot" value={data.spot.toLocaleString("en-IN")} />
            <Metric label="PCR" value={String(data.pcr)} tone={data.pcr > 1 ? "bull" : "bear"} />
            <Metric label="Max Pain" value={String(data.max_pain)} />
            <Metric label="Bias" value={data.bias} tone={data.bias === "BULLISH" ? "bull" : data.bias === "BEARISH" ? "bear" : ""} />
            <Metric label="Support / Resist" value={`${data.support[0] ?? "-"} / ${data.resistance[0] ?? "-"}`} />
          </div>

          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-gray-500 text-xs">
                <tr>
                  <th className="text-right p-2">CE ΔOI</th>
                  <th className="text-right p-2">CE OI</th>
                  <th className="text-right p-2">CE LTP</th>
                  <th className="text-center p-2 bg-panel2">STRIKE</th>
                  <th className="text-right p-2">PE LTP</th>
                  <th className="text-right p-2">PE OI</th>
                  <th className="text-right p-2">PE ΔOI</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => {
                  const atm = Math.abs(r.strike - data.spot) < (data.rows[1]?.strike - data.rows[0]?.strike || 50);
                  return (
                    <tr key={r.strike} className={atm ? "bg-accent/10" : ""}>
                      <td className={`text-right p-2 ${r.ce_chg_oi >= 0 ? "text-bull" : "text-bear"}`}>
                        {r.ce_chg_oi.toLocaleString("en-IN")}
                      </td>
                      <td className="text-right p-2 relative">
                        <span className="relative z-10">{r.ce_oi.toLocaleString("en-IN")}</span>
                        <span
                          className="absolute right-0 top-0 h-full bg-bear/15"
                          style={{ width: `${(r.ce_oi / maxOi) * 100}%` }}
                        />
                      </td>
                      <td className="text-right p-2 text-gray-400">{r.ce_ltp}</td>
                      <td className="text-center p-2 font-semibold bg-panel2">{r.strike}</td>
                      <td className="text-right p-2 text-gray-400">{r.pe_ltp}</td>
                      <td className="text-right p-2 relative">
                        <span className="relative z-10">{r.pe_oi.toLocaleString("en-IN")}</span>
                        <span
                          className="absolute left-0 top-0 h-full bg-bull/15"
                          style={{ width: `${(r.pe_oi / maxOi) * 100}%` }}
                        />
                      </td>
                      <td className={`text-right p-2 ${r.pe_chg_oi >= 0 ? "text-bull" : "text-bear"}`}>
                        {r.pe_chg_oi.toLocaleString("en-IN")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  const c = tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : "text-white";
  return (
    <div className="card">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-lg font-bold ${c}`}>{value}</div>
    </div>
  );
}
