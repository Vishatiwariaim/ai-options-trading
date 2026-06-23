export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function token(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const t = token();
  if (t) headers["Authorization"] = `Bearer ${t}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(p: string) => request<T>(p),
  post: <T>(p: string, body?: unknown) =>
    request<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),

  // auth uses form-encoded login
  async login(email: string, password: string) {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!res.ok) throw new Error("Invalid email or password");
    return res.json();
  },
};

export type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

export type BestDeal = {
  as_of: string;
  action: string; // "BUY CALL (CE)" | "BUY PUT (PE)" | "WAIT …"
  wait: boolean;
  symbol: string;
  instrument: string; // CE | PE | EQ
  signal: string;
  win_chance: number;
  expected_value?: number;
  quality?: "A" | "B" | "C";
  mtf_trend?: "UP" | "DOWN" | "FLAT";
  adx?: number;
  agreement?: string;
  confidence: number;
  score: number;
  entry: number;
  target1: number;
  target2: number;
  stop_loss: number;
  risk_reward: string;
  reason: string;
  data_source: "live" | "demo";
  alternatives: {
    symbol: string;
    signal: string;
    instrument: string;
    quality?: string;
    win_probability?: number;
    expected_value?: number;
  }[];
  candles?: Candle[];
  disclaimer: string;
};

export type Signal = {
  symbol: string;
  signal: string;
  instrument: string;
  confidence: number;
  score: number;
  entry: number;
  target1: number;
  target2: number;
  stop_loss: number;
  risk_reward: string;
  breakdown?: any;
  disclaimer?: string;
};
