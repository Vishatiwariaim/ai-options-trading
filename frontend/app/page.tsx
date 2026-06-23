"use client";

import { useEffect, useState } from "react";
import { api, BestDeal } from "@/lib/api";
import { BestDealCard } from "@/components/BestDealCard";

type Sym = { symbol: string; name: string; lot: number };
type Quote = {
  symbol: string;
  name: string;
  last_price: number;
  change: number;
  change_pct: number;
  source?: "live" | "demo";
};

function DataBadge({ source }: { source: "live" | "demo" }) {
  const live = source === "live";
  return (
    <span
      className={`badge text-xs ${live ? "bg-bull/20 text-bull" : "bg-yellow-500/20 text-yellow-400"}`}
      title={
        live
          ? "Real market data from yfinance/NSE"
          : "Synthetic/demo data — live source blocked or unreachable on this network"
      }
    >
      {live ? "● LIVE DATA" : "● DEMO DATA (synthetic)"}
    </span>
  );
}

export default function Dashboard() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [deal, setDeal] = useState<BestDeal | null>(null);
  const [dealLoading, setDealLoading] = useState(true);
  const [source, setSource] = useState<"live" | "demo">("demo");

  const [updatedAt, setUpdatedAt] = useState<string>("");

  useEffect(() => {
    let alive = true;

    async function loadQuotes() {
      try {
        const syms = await api.get<Sym[]>("/api/market/symbols");
        const qs = await Promise.all(
          syms.map((s) => api.get<Quote>(`/api/market/quote/${s.symbol}`).catch(() => null))
        );
        if (alive) {
          setQuotes(qs.filter(Boolean) as Quote[]);
          setUpdatedAt(new Date().toLocaleTimeString("en-IN"));
        }
      } catch (e: any) {
        if (alive) setErr(e.message);
      } finally {
        if (alive) setLoading(false);
      }
    }

    async function loadDeal() {
      try {
        const d = await api.get<BestDeal>("/api/signals/best-deal");
        if (!alive) return;
        setDeal(d);
        setSource(d.data_source);
      } catch {
        /* keep last deal on transient errors */
      } finally {
        if (alive) setDealLoading(false);
      }
    }

    loadQuotes();
    loadDeal();
    // Auto-refresh so the dashboard feels live during market hours.
    const id = setInterval(() => {
      loadQuotes();
      loadDeal();
    }, 20000);

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-2 mb-1">
        <h1 className="text-2xl font-bold">Market Dashboard</h1>
        <DataBadge source={source} />
      </div>
      <p className="text-gray-400 text-sm mb-6">
        Live snapshot of NSE indices & tracked stocks · auto-refresh every 20s
        {updatedAt && <span className="text-gray-500"> · updated {updatedAt}</span>}
      </p>

      {/* AI Agent — today's best deal */}
      <div className="mb-8">
        {dealLoading ? (
          <div className="card text-gray-400">🤖 Agent aaj ka best deal dhoondh raha hai…</div>
        ) : deal ? (
          <BestDealCard deal={deal} />
        ) : (
          <div className="card text-gray-400">Best deal load nahi ho paya. Backend :8000 chal raha hai?</div>
        )}
      </div>

      {err && (
        <div className="card border-bear/40 text-bear mb-4">
          Failed to load market data: {err}. Is the backend running on :8000?
        </div>
      )}

      {loading ? (
        <div className="text-gray-400">Loading market data…</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quotes.map((q) => {
            const up = q.change >= 0;
            return (
              <div key={q.symbol} className="card">
                <div className="text-sm text-gray-400">{q.name}</div>
                <div className="text-xl font-bold mt-1">
                  ₹{q.last_price.toLocaleString("en-IN")}
                </div>
                <div className={`text-sm mt-1 ${up ? "text-bull" : "text-bear"}`}>
                  {up ? "▲" : "▼"} {q.change} ({q.change_pct}%)
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
        <FeatureLink href="/signals" title="AI Signals" desc="4-layer weighted scoring + ML probabilities" />
        <FeatureLink href="/option-chain" title="Option Chain" desc="PCR, Max Pain, OI support/resistance" />
        <FeatureLink href="/paper-trading" title="Paper Trading" desc="Trade with virtual capital, track P&L" />
      </div>
    </div>
  );
}

function FeatureLink({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <a href={href} className="card hover:border-accent/50 transition block">
      <div className="font-semibold">{title}</div>
      <div className="text-sm text-gray-400 mt-1">{desc}</div>
    </a>
  );
}
