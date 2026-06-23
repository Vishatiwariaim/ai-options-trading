"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import Link from "next/link";

type Summary = {
  total_capital: number;
  invested: number;
  open_pnl: number;
  realized_pnl: number;
  total_pnl: number;
  daily_pnl: number;
  win_rate: number;
  total_trades: number;
  open_trades: number;
  max_drawdown: number;
  risk_score: number;
};

export default function PortfolioPage() {
  const { user, loading } = useAuth();
  const [s, setS] = useState<Summary | null>(null);

  useEffect(() => {
    if (user) api.get<Summary>("/api/paper/portfolio").then(setS);
  }, [user]);

  if (loading) return <div className="text-gray-400">Loading…</div>;
  if (!user)
    return (
      <div className="card max-w-md">
        Please{" "}
        <Link href="/login" className="text-accent">
          sign in
        </Link>{" "}
        to view your portfolio.
      </div>
    );

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Portfolio Dashboard</h1>
      <p className="text-gray-400 text-sm mb-6">Performance of your paper-trading account.</p>

      {!s ? (
        <div className="text-gray-400">Loading portfolio…</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Big label="Total Capital" value={`₹${s.total_capital.toLocaleString("en-IN")}`} />
            <Big label="Total P&L" value={`₹${s.total_pnl}`} tone={s.total_pnl >= 0 ? "bull" : "bear"} />
            <Big label="Daily P&L" value={`₹${s.daily_pnl}`} tone={s.daily_pnl >= 0 ? "bull" : "bear"} />
            <Big label="Win Rate" value={`${s.win_rate}%`} />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Small label="Realized P&L" value={`₹${s.realized_pnl}`} />
            <Small label="Open P&L" value={`₹${s.open_pnl}`} />
            <Small label="Invested" value={`₹${s.invested}`} />
            <Small label="Max Drawdown" value={`₹${s.max_drawdown}`} />
            <Small label="Total Trades" value={String(s.total_trades)} />
            <Small label="Open Trades" value={String(s.open_trades)} />
            <Small label="Risk Score" value={`${s.risk_score}/100`} />
          </div>

          <div className="card mt-6">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Risk exposure</span>
              <span>{s.risk_score}/100</span>
            </div>
            <div className="h-3 rounded bg-panel2 overflow-hidden">
              <div
                className={`h-full ${s.risk_score > 60 ? "bg-bear" : s.risk_score > 30 ? "bg-yellow-500" : "bg-bull"}`}
                style={{ width: `${Math.min(100, s.risk_score)}%` }}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Big({ label, value, tone }: { label: string; value: string; tone?: string }) {
  const c = tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : "text-white";
  return (
    <div className="card">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${c}`}>{value}</div>
    </div>
  );
}

function Small({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-semibold mt-1">{value}</div>
    </div>
  );
}
