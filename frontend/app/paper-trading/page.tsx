"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Link from "next/link";

type Trade = {
  id: number;
  symbol: string;
  instrument: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number | null;
  stop_loss: number | null;
  target: number | null;
  status: string;
  pnl: number;
};

export default function PaperTradingPage() {
  const { user, loading } = useAuth();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [form, setForm] = useState({
    symbol: "NIFTY",
    instrument: "CE",
    side: "BUY",
    quantity: 50,
    entry_price: 0,
    stop_loss: 0,
    target: 0,
  });
  const [risk, setRisk] = useState<any>(null);
  const [msg, setMsg] = useState("");

  async function refresh() {
    const t = await api.get<Trade[]>("/api/paper/trades");
    setTrades(t);
  }

  useEffect(() => {
    if (user) refresh();
  }, [user]);

  async function calcRisk() {
    const r = await api.post("/api/risk/position-size", {
      capital: user?.capital ?? 100000,
      risk_pct: 1,
      entry: form.entry_price,
      stop_loss: form.stop_loss,
      lot_size: 1,
    });
    setRisk(r);
  }

  async function openTrade(e: React.FormEvent) {
    e.preventDefault();
    setMsg("");
    try {
      await api.post("/api/paper/trades", {
        ...form,
        quantity: Number(form.quantity),
        entry_price: Number(form.entry_price),
        stop_loss: Number(form.stop_loss) || null,
        target: Number(form.target) || null,
      });
      setMsg("Trade opened ✔");
      refresh();
    } catch (e: any) {
      setMsg(e.message);
    }
  }

  async function closeTrade(t: Trade) {
    const px = prompt(`Exit price for ${t.symbol}?`, String(t.entry_price));
    if (!px) return;
    await api.post(`/api/paper/trades/${t.id}/close`, { exit_price: Number(px) });
    refresh();
  }

  if (loading) return <div className="text-gray-400">Loading…</div>;
  if (!user)
    return (
      <div className="card max-w-md">
        Please{" "}
        <Link href="/login" className="text-accent">
          sign in
        </Link>{" "}
        to use paper trading.
      </div>
    );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Paper Trading</h1>
      <p className="text-gray-400 text-sm mb-6">
        Virtual capital: ₹{user.capital.toLocaleString("en-IN")}. Simulated fills, real P&L tracking.
      </p>

      <div className="grid lg:grid-cols-3 gap-6">
        <form onSubmit={openTrade} className="card space-y-3">
          <h2 className="font-semibold">New Trade</h2>
          <input
            className="input"
            value={form.symbol}
            onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
            placeholder="Symbol"
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              className="input"
              value={form.instrument}
              onChange={(e) => setForm({ ...form, instrument: e.target.value })}
            >
              {["CE", "PE", "EQ", "FUT"].map((i) => (
                <option key={i}>{i}</option>
              ))}
            </select>
            <select
              className="input"
              value={form.side}
              onChange={(e) => setForm({ ...form, side: e.target.value })}
            >
              {["BUY", "SELL"].map((i) => (
                <option key={i}>{i}</option>
              ))}
            </select>
          </div>
          <NumberField label="Quantity" v={form.quantity} set={(v) => setForm({ ...form, quantity: v })} />
          <NumberField label="Entry Price" v={form.entry_price} set={(v) => setForm({ ...form, entry_price: v })} />
          <div className="grid grid-cols-2 gap-2">
            <NumberField label="Stop Loss" v={form.stop_loss} set={(v) => setForm({ ...form, stop_loss: v })} />
            <NumberField label="Target" v={form.target} set={(v) => setForm({ ...form, target: v })} />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={calcRisk} className="btn-ghost flex-1">
              Calc Risk
            </button>
            <button className="btn flex-1">Open Trade</button>
          </div>
          {risk && (
            <div className="text-xs text-gray-400 bg-panel2 rounded-lg p-2">
              Suggested qty: <b className="text-white">{risk.suggested_quantity}</b> · Max risk ₹
              {risk.max_risk_amount} · Exposure ₹{risk.exposure}
            </div>
          )}
          {msg && <div className="text-sm text-accent">{msg}</div>}
        </form>

        <div className="lg:col-span-2 card overflow-x-auto">
          <h2 className="font-semibold mb-3">Your Trades</h2>
          {trades.length === 0 ? (
            <div className="text-gray-500 text-sm">No trades yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-gray-500 text-xs text-left">
                <tr>
                  <th className="p-2">Symbol</th>
                  <th className="p-2">Side</th>
                  <th className="p-2 text-right">Qty</th>
                  <th className="p-2 text-right">Entry</th>
                  <th className="p-2 text-right">Exit</th>
                  <th className="p-2 text-right">P&L</th>
                  <th className="p-2">Status</th>
                  <th className="p-2"></th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr key={t.id} className="border-t border-white/5">
                    <td className="p-2 font-medium">
                      {t.symbol} <span className="text-gray-500">{t.instrument}</span>
                    </td>
                    <td className={`p-2 ${t.side === "BUY" ? "text-bull" : "text-bear"}`}>{t.side}</td>
                    <td className="p-2 text-right">{t.quantity}</td>
                    <td className="p-2 text-right">{t.entry_price}</td>
                    <td className="p-2 text-right">{t.exit_price ?? "-"}</td>
                    <td className={`p-2 text-right ${t.pnl >= 0 ? "text-bull" : "text-bear"}`}>
                      {t.pnl}
                    </td>
                    <td className="p-2">{t.status}</td>
                    <td className="p-2">
                      {t.status === "OPEN" && (
                        <button onClick={() => closeTrade(t)} className="btn-ghost text-xs">
                          Close
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function NumberField({ label, v, set }: { label: string; v: number; set: (n: number) => void }) {
  return (
    <label className="block">
      <span className="text-xs text-gray-500">{label}</span>
      <input
        type="number"
        className="input"
        value={v}
        onChange={(e) => set(Number(e.target.value))}
      />
    </label>
  );
}
