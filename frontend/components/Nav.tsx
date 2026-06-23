"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/signals", label: "Signals" },
  { href: "/option-chain", label: "Option Chain" },
  { href: "/paper-trading", label: "Paper Trading" },
  { href: "/portfolio", label: "Portfolio" },
];

export function Nav() {
  const path = usePathname();
  const { user, logout } = useAuth();

  return (
    <nav className="border-b border-white/5 bg-panel/60 backdrop-blur sticky top-0 z-20">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link href="/" className="font-bold text-accent whitespace-nowrap">
          ⚡ AI Options
        </Link>
        <div className="flex items-center gap-1 overflow-x-auto">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`px-3 py-1.5 rounded-lg text-sm whitespace-nowrap ${
                path === l.href ? "bg-panel2 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-3 text-sm">
          {user ? (
            <>
              <span className="text-gray-400 hidden sm:inline">{user.email}</span>
              {user.role === "admin" && (
                <span className="badge bg-accent/20 text-accent">ADMIN</span>
              )}
              <button onClick={logout} className="btn-ghost">
                Logout
              </button>
            </>
          ) : (
            <Link href="/login" className="btn">
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
