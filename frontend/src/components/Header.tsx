"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { CSSProperties } from "react";

const navBase: CSSProperties = {
  border: 0,
  fontSize: 14.5,
  fontWeight: 700,
  padding: "9px 20px",
  borderRadius: 11,
  display: "inline-flex",
};
const navOn: CSSProperties = { ...navBase, background: "#fff", color: "#12181F", boxShadow: "0 1px 4px rgba(18,24,31,.12)" };
const navOff: CSSProperties = { ...navBase, background: "transparent", color: "#6B7684" };

export default function Header() {
  const pathname = usePathname();
  const isHome = pathname === "/";
  const isTrends = pathname === "/trends";

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        gap: 32,
        padding: "16px 40px",
        position: "sticky",
        top: 0,
        background: "rgba(242,245,247,.82)",
        backdropFilter: "blur(16px)",
        zIndex: 20,
      }}
    >
      <Link
        href="/"
        style={{ display: "flex", alignItems: "center", gap: 11, marginRight: "auto", color: "#12181F" }}
      >
        <span
          style={{
            width: 36,
            height: 36,
            borderRadius: 12,
            background: "linear-gradient(145deg,#14C08F,#0B8F6B)",
            display: "grid",
            placeItems: "center",
            boxShadow: "0 4px 12px rgba(15,169,127,.32)",
            flex: "none",
          }}
        >
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3.5 12.5h4l2-5 3.5 10 2.5-5h5"></path>
          </svg>
        </span>
        <span style={{ fontWeight: 800, fontSize: 21, letterSpacing: "-.03em", color: "#12181F" }}>VaX</span>
        <span style={{ fontSize: 13, color: "#7C8894", fontWeight: 500 }}>Vaccine discourse monitor</span>
      </Link>

      <nav style={{ display: "flex", gap: 4, alignItems: "center", background: "#E4EAEE", padding: 4, borderRadius: 14 }}>
        <Link href="/" style={isHome ? navOn : navOff}>
          Home
        </Link>
        <Link href="/trends" style={isTrends ? navOn : navOff}>
          Trends
        </Link>
      </nav>

      <button
        type="button"
        className="vx-btn-dark"
        style={{ border: 0, color: "#fff", fontWeight: 600, fontSize: 14, padding: "10px 20px", borderRadius: 14, flex: "none" }}
      >
        Sign in
      </button>
    </header>
  );
}
