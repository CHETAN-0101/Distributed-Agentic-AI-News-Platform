"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";

/* ──────────────────────────────────────────────────────────────────────────
   DATA
   ──────────────────────────────────────────────────────────────────────── */
const AGENT_NODES = [
  { id: "research",   label: "Research",   icon: "📄", angle:  20, color: "#a78bfa" },
  { id: "news",       label: "News",       icon: "📰", angle:  75, color: "#38bdf8" },
  { id: "finance",    label: "Finance",    icon: "📊", angle: 130, color: "#fbbf24" },
  { id: "security",   label: "Security",   icon: "🛡️", angle: 170, color: "#f87171" },
  { id: "coding",     label: "Coding",     icon: "💻", angle: 215, color: "#34d399" },
  { id: "healthcare", label: "Healthcare", icon: "❤️", angle: 255, color: "#f472b6" },
  { id: "legal",      label: "Legal",      icon: "⚖️", angle: 305, color: "#fb923c" },
  { id: "creative",   label: "Creative",   icon: "🎨", angle: 345, color: "#818cf8" },
];

const LATEST_NEWS = [
  { id: 1, title: "OpenAI unveils GPT-5 with advanced reasoning capabilities", time: "2 hours ago", tag: "AI Models",   logo: "🤖", bg: "#1e3a5f" },
  { id: 2, title: "Anthropic introduces Claude 3.5 with enhanced tool use",    time: "5 hours ago", tag: "AI Models",   logo: "🔬", bg: "#1e1b4b" },
  { id: 3, title: "Google DeepMind achieves new milestone in AI safety",        time: "8 hours ago", tag: "AI Safety",   logo: "🔷", bg: "#14532d" },
  { id: 4, title: "Microsoft expands Copilot to more enterprise tools",         time: "12 hours ago",tag: "Enterprise",  logo: "🟦", bg: "#1e3a5f" },
  { id: 5, title: "Meta releases open-source AI model for edge devices",        time: "1 day ago",   tag: "Open Source", logo: "🔵", bg: "#1e1b4b" },
];

const STATS = [
  { value: "10+",       label: "Specialized Agents",     color: "#a78bfa" },
  { value: "Real-time", label: "RabbitMQ Communication", color: "#38bdf8" },
  { value: "24/7",      label: "AI News Monitoring",     color: "#818cf8" },
  { value: "99.9%",     label: "System Uptime",          color: "#a78bfa" },
  { value: "Global",    label: "Knowledge Coverage",     color: "#38bdf8" },
];

const AGENTS_GRID = [
  { name: "Research Agent",  icon: "📄", color: "#a78bfa", desc: "Deep web research with source credibility scoring and evidence synthesis." },
  { name: "News Agent",      icon: "📰", color: "#38bdf8", desc: "Real-time RSS ingestion from 12+ global news sources with deduplication." },
  { name: "Finance Agent",   icon: "📊", color: "#fbbf24", desc: "Market analysis, earnings reports, and economic indicator tracking." },
  { name: "Security Agent",  icon: "🛡️", color: "#f87171", desc: "Defensive threat analysis, CVE assessment, and incident investigation." },
  { name: "Coding Agent",    icon: "💻", color: "#34d399", desc: "Code analysis, debugging, documentation, and technical synthesis." },
  { name: "Legal Agent",     icon: "⚖️", color: "#fb923c", desc: "Regulatory compliance, contract analysis, and policy interpretation." },
];

/* ──────────────────────────────────────────────────────────────────────────
   GLOBE
   ──────────────────────────────────────────────────────────────────────── */
const GLOBE_R = 190; // px, half-width of SVG container
const ORBIT_R = 145; // orbit distance

function degToRad(d: number) { return (d * Math.PI) / 180; }

function GlobeViz() {
  const [active, setActive] = useState<string | null>(null);
  const [time, setTime] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    let start: number | null = null;
    const loop = (now: number) => {
      if (start === null) start = now;
      const elapsed = (now - start) / 1000;
      setTime(elapsed);
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  // Compute animated positions for all nodes
  const nodesWithPos = AGENT_NODES.map((n, idx) => {
    // Slow smooth orbit: 9 deg/second (full revolution every 40s)
    const currentAngle = (n.angle + time * 9) % 360;
    const rad = degToRad(currentAngle);
    // 3D perspective projection onto tilted orbital plane
    const x = GLOBE_R + ORBIT_R * Math.cos(rad);
    // Vertical bobbing superimposed on elliptic orbit
    const bob = Math.sin(time * 2 + idx * 1.1) * 3;
    const y = GLOBE_R + ORBIT_R * 0.38 * Math.sin(rad) + bob;
    // Depth: sin(rad) ranges from -1 (top/back) to +1 (bottom/front)
    const depth = (Math.sin(rad) + 1) / 2; // 0 = back, 1 = front
    const scale = 0.88 + depth * 0.24; // 0.88 back, 1.12 front
    const opacity = 0.65 + depth * 0.35; // dimmer in back
    const zIndex = Math.round(10 + depth * 20);

    return {
      ...n,
      x,
      y,
      scale,
      opacity,
      zIndex,
      depth,
    };
  });

  const globePulse = 1 + 0.05 * Math.sin(time * 1.8);
  const glowOpacity = 0.32 + 0.12 * Math.sin(time * 1.8);
  const centerBob = Math.sin(time * 2.2) * 2;

  return (
    <div style={{ position: "relative", width: GLOBE_R * 2, height: GLOBE_R * 2, flexShrink: 0 }}>
      <svg
        width={GLOBE_R * 2}
        height={GLOBE_R * 2}
        style={{ overflow: "visible", position: "absolute", inset: 0 }}
      >
        <defs>
          <radialGradient id="g1" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="#1e3a8a" stopOpacity="1" />
            <stop offset="55%"  stopColor="#1e1b4b" stopOpacity="1" />
            <stop offset="100%" stopColor="#0a0e1c" stopOpacity="1" />
          </radialGradient>
          <radialGradient id="glow1" cx="50%" cy="30%" r="60%">
            <stop offset="0%"   stopColor="#6366f1" stopOpacity="0.55" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="centerPulse" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="#818cf8" stopOpacity="0.4" />
            <stop offset="60%"  stopColor="#6366f1" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#4f46e5" stopOpacity="0" />
          </radialGradient>
          <filter id="blur4">
            <feGaussianBlur in="SourceGraphic" stdDeviation="8" />
          </filter>
          <filter id="blurRing">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2" />
          </filter>
        </defs>

        {/* Ambient background aura */}
        <circle cx={GLOBE_R} cy={GLOBE_R} r={110 * globePulse} fill="url(#centerPulse)" />

        {/* Orbit ellipse (outer glow) */}
        <ellipse
          cx={GLOBE_R}
          cy={GLOBE_R}
          rx={ORBIT_R}
          ry={ORBIT_R * 0.38}
          fill="none"
          stroke="rgba(99,102,241,0.4)"
          strokeWidth="2"
          filter="url(#blurRing)"
        />
        {/* Orbit ellipse with animated dash */}
        <ellipse
          cx={GLOBE_R}
          cy={GLOBE_R}
          rx={ORBIT_R}
          ry={ORBIT_R * 0.38}
          fill="none"
          stroke="rgba(129,140,248,0.3)"
          strokeWidth="1.2"
          strokeDasharray="6 4"
          strokeDashoffset={-time * 12}
        />

        {/* Connector lines from center to nodes */}
        {nodesWithPos.map((n, idx) => {
          const isA = active === n.id;
          const rayPulse = 0.25 + 0.2 * Math.sin(time * 2.5 + idx * 0.8);
          return (
            <line
              key={n.id}
              x1={GLOBE_R}
              y1={GLOBE_R}
              x2={n.x}
              y2={n.y}
              stroke={n.color}
              strokeWidth={isA ? 1.8 : 0.9}
              strokeOpacity={isA ? 0.95 : rayPulse}
              strokeDasharray={isA ? "5 2" : "4 4"}
              strokeDashoffset={-time * 18}
            />
          );
        })}

        {/* Glow shadow behind globe */}
        <circle cx={GLOBE_R} cy={GLOBE_R} r={68 * globePulse} fill="#6366f1" filter="url(#blur4)" opacity={glowOpacity} />
        {/* Globe body */}
        <circle cx={GLOBE_R} cy={GLOBE_R} r={68} fill="url(#g1)" />
        <circle cx={GLOBE_R} cy={GLOBE_R} r={68} fill="url(#glow1)" />
        <circle cx={GLOBE_R} cy={GLOBE_R} r={68} fill="none" stroke="rgba(99,102,241,0.6)" strokeWidth="1.5" />
        {/* Latitude lines */}
        <ellipse cx={GLOBE_R} cy={GLOBE_R} rx={68} ry={21} fill="none" stroke="rgba(99,102,241,0.22)" strokeWidth="0.8" />
        <ellipse cx={GLOBE_R} cy={GLOBE_R - 18} rx={58} ry={15} fill="none" stroke="rgba(99,102,241,0.16)" strokeWidth="0.6" />
        <ellipse cx={GLOBE_R} cy={GLOBE_R + 18} rx={58} ry={15} fill="none" stroke="rgba(99,102,241,0.16)" strokeWidth="0.6" />
        {/* Vertical line */}
        <line
          x1={GLOBE_R}
          y1={GLOBE_R - 68}
          x2={GLOBE_R}
          y2={GLOBE_R + 68}
          stroke="rgba(99,102,241,0.22)"
          strokeWidth="0.8"
        />
      </svg>

      {/* Globe center label */}
      <div
        style={{
          position: "absolute",
          left: GLOBE_R,
          top: GLOBE_R + centerBob,
          transform: "translate(-50%,-50%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 4,
          zIndex: 25,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            width: 42,
            height: 42,
            borderRadius: 12,
            background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 900,
            fontSize: 19,
            color: "#fff",
            boxShadow: `0 4px 24px rgba(99,102,241,${0.5 + 0.2 * Math.sin(time * 2)})`,
            transition: "box-shadow 0.2s",
          }}
        >
          A
        </div>
        <span
          style={{
            color: "#fff",
            fontWeight: 700,
            fontSize: 12,
            letterSpacing: "0.02em",
            textShadow: "0 2px 10px rgba(0,0,0,0.9)",
          }}
        >
          AgentOS
        </span>
      </div>

      {/* Agent node buttons */}
      {nodesWithPos.map((n) => {
        const isA = active === n.id;
        const currentScale = isA ? n.scale * 1.22 : n.scale;
        return (
          <button
            key={n.id}
            onMouseEnter={() => setActive(n.id)}
            onMouseLeave={() => setActive(null)}
            style={{
              position: "absolute",
              left: n.x,
              top: n.y,
              transform: `translate(-50%,-50%) scale(${currentScale})`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 3,
              cursor: "pointer",
              background: "none",
              border: "none",
              padding: 0,
              zIndex: isA ? 50 : n.zIndex,
              opacity: isA ? 1 : n.opacity,
              transition: "transform 0.15s ease-out, opacity 0.15s",
            }}
          >
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 10,
                background: `rgba(15,23,42,0.85)`,
                border: `1.5px solid ${n.color}${isA ? "cc" : "55"}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 18,
                boxShadow: isA
                  ? `0 0 22px ${n.color}88, inset 0 0 10px ${n.color}33`
                  : `0 2px 8px rgba(0,0,0,0.6)`,
                backdropFilter: "blur(6px)",
                transition: "all 0.18s",
              }}
            >
              {n.icon}
            </div>
            <div style={{ textAlign: "center", lineHeight: 1.15 }}>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color: isA ? "#ffffff" : "#e2e8f0",
                  textShadow: "0 1px 6px rgba(0,0,0,0.95)",
                  whiteSpace: "nowrap",
                }}
              >
                {n.label}
              </div>
              <div
                style={{
                  fontSize: 9,
                  color: isA ? n.color : "#94a3b8",
                  textShadow: "0 1px 4px rgba(0,0,0,0.95)",
                }}
              >
                Agent
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────────
   MAIN PAGE
   ──────────────────────────────────────────────────────────────────────── */
export default function LandingPage() {
  const [navScrolled, setNavScrolled] = useState(false);

  useEffect(() => {
    const fn = () => setNavScrolled(window.scrollY > 10);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(160deg, #060b18 0%, #0d1530 45%, #080d1a 100%)",
      fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
      color: "#e2e8f0",
    }}>

      {/* ── NAVBAR ─────────────────────────────────────────────────────── */}
      <nav style={{
        position: "sticky", top: 0, zIndex: 100,
        display: "flex", alignItems: "center",
        padding: "0 32px", height: 58,
        background: navScrolled ? "rgba(6,11,24,0.92)" : "rgba(6,11,24,0.75)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(99,102,241,0.15)",
        transition: "background 0.3s",
      }}>
        {/* Logo */}
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", marginRight: 40 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 900, fontSize: 16, color: "#fff",
          }}>A</div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, color: "#fff", lineHeight: 1.1 }}>AgentOS</div>
            <div style={{ fontSize: 9, color: "#818cf8", lineHeight: 1 }}>Many Agents. One Intelligence.</div>
          </div>
        </Link>

        {/* Nav links */}
        <div style={{ display: "flex", alignItems: "center", gap: 28, flex: 1 }}>
          {[
            { label: "Home",      href: "/" },
            { label: "Agents",    href: "/dashboard/agents" },
            { label: "AI News",   href: "/dashboard/newsflow" },
            { label: "Use Cases", href: "#" },
            { label: "Docs",      href: "#" },
            { label: "Pricing",   href: "#" },
          ].map((item, i) => (
            <Link key={item.label} href={item.href} style={{
              textDecoration: "none",
              fontSize: 14,
              fontWeight: i === 0 ? 600 : 400,
              color: i === 0 ? "#fff" : "#94a3b8",
              borderBottom: i === 0 ? "2px solid #6366f1" : "none",
              paddingBottom: i === 0 ? 2 : 0,
              transition: "color 0.15s",
            }}
              onMouseEnter={e => (e.currentTarget.style.color = "#fff")}
              onMouseLeave={e => { if (i !== 0) e.currentTarget.style.color = "#94a3b8"; }}
            >{item.label}</Link>
          ))}
        </div>

        {/* Right buttons */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link href="/dashboard" style={{
            fontSize: 14, color: "#cbd5e1", textDecoration: "none",
            padding: "6px 12px",
          }}
            onMouseEnter={e => e.currentTarget.style.color = "#fff"}
            onMouseLeave={e => e.currentTarget.style.color = "#cbd5e1"}
          >Sign In</Link>
          <Link href="/dashboard" style={{
            padding: "8px 20px", borderRadius: 8,
            background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
            color: "#fff", fontWeight: 700, fontSize: 14, textDecoration: "none",
            boxShadow: "0 4px 14px rgba(99,102,241,0.35)",
            transition: "opacity 0.15s, transform 0.15s",
          }}
            onMouseEnter={e => { e.currentTarget.style.opacity = "0.88"; e.currentTarget.style.transform = "translateY(-1px)"; }}
            onMouseLeave={e => { e.currentTarget.style.opacity = "1"; e.currentTarget.style.transform = "none"; }}
          >Get Started</Link>
        </div>
      </nav>

      {/* ── HERO ───────────────────────────────────────────────────────── */}
      <section style={{ position: "relative", overflow: "hidden", padding: "60px 40px 40px" }}>
        {/* BG glows */}
        <div style={{ position: "absolute", top: "20%", left: "15%", width: 500, height: 500, borderRadius: "50%", background: "radial-gradient(circle, rgba(99,102,241,0.12), transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", top: "10%", right: "20%", width: 350, height: 350, borderRadius: "50%", background: "radial-gradient(circle, rgba(139,92,246,0.1), transparent 70%)", pointerEvents: "none" }} />

        {/* 3-col layout */}
        <div style={{
          position: "relative",
          maxWidth: 1280,
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "1fr 400px 300px",
          gap: 24,
          alignItems: "center",
        }}>

          {/* LEFT */}
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", color: "#818cf8" }}>
              <span>BUILD</span><span style={{ color: "#374151" }}>·</span>
              <span>ORCHESTRATE</span><span style={{ color: "#374151" }}>·</span>
              <span>AUTOMATE</span><span style={{ color: "#374151" }}>·</span>
              <span>STAY INFORMED</span>
            </div>

            <h1 style={{ fontSize: 52, fontWeight: 900, lineHeight: 1.06, letterSpacing: "-0.02em", color: "#fff", margin: 0 }}>
              The Agentic AI
              <br />Platform for a{" "}
              <span style={{ background: "linear-gradient(135deg, #6366f1, #a78bfa)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Smarter
                <br />Tomorrow
              </span>
            </h1>

            <p style={{ fontSize: 15, color: "#94a3b8", lineHeight: 1.65, maxWidth: 420, margin: 0 }}>
              A unified platform of specialized AI agents that collaborate across domains, communicate via RabbitMQ, and deliver trusted, real-time intelligence — including the latest AI news.
            </p>

            {/* CTAs */}
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <Link href="/dashboard" style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "12px 24px", borderRadius: 10,
                background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
                color: "#fff", fontWeight: 700, fontSize: 14, textDecoration: "none",
                boxShadow: "0 6px 20px rgba(99,102,241,0.4)",
                transition: "transform 0.15s, box-shadow 0.15s",
              }}
                onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 10px 28px rgba(99,102,241,0.5)"; }}
                onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "0 6px 20px rgba(99,102,241,0.4)"; }}
              >
                Get Started <span style={{ fontSize: 16 }}>→</span>
              </Link>
              <button style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "12px 24px", borderRadius: 10, cursor: "pointer",
                background: "transparent",
                color: "#e2e8f0", fontWeight: 600, fontSize: 14,
                border: "1px solid rgba(255,255,255,0.14)",
                transition: "background 0.15s, border-color 0.15s",
              }}
                onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.05)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.25)"; }}
                onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.14)"; }}
              >
                <span style={{ width: 24, height: 24, borderRadius: "50%", background: "rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10 }}>▶</span>
                Watch Demo
              </button>
            </div>

            {/* Feature pills */}
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
              {[
                { icon: "🧩", label: "Modular",      sub: "AI Agents" },
                { icon: "⚡", label: "Real-time",    sub: "Communication" },
                { icon: "✅", label: "Trusted &",    sub: "Verifiable Answers" },
                { icon: "📸", label: "Always Updated", sub: "with AI News" },
              ].map(f => (
                <div key={f.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 16 }}>{f.icon}</span>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "#cbd5e1", lineHeight: 1.2 }}>{f.label}</div>
                    <div style={{ fontSize: 10, color: "#4b5563", lineHeight: 1.2 }}>{f.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CENTER — Globe */}
          <GlobeViz />

          {/* RIGHT — News Panel */}
          <div style={{
            background: "rgba(13,20,45,0.88)",
            border: "1px solid rgba(99,102,241,0.22)",
            borderRadius: 16,
            padding: 16,
            backdropFilter: "blur(16px)",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <span style={{ fontWeight: 700, fontSize: 13, color: "#fff" }}>Latest AI News</span>
              <Link href="/dashboard/newsflow" style={{ fontSize: 11, color: "#818cf8", textDecoration: "none" }}>View All →</Link>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {LATEST_NEWS.map(item => (
                <div key={item.id} style={{
                  display: "flex", gap: 10, padding: "9px 8px", borderRadius: 10, cursor: "pointer",
                  transition: "background 0.15s",
                }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.05)"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                >
                  <div style={{
                    width: 32, height: 32, borderRadius: 8,
                    background: item.bg,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 14, flexShrink: 0,
                  }}>{item.logo}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{
                      fontSize: 11, fontWeight: 500, color: "#e2e8f0", lineHeight: 1.35, margin: 0,
                      display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden",
                    }}>{item.title}</p>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                      <span style={{ fontSize: 9, color: "#6b7280" }}>⏰ {item.time}</span>
                      <span style={{
                        fontSize: 9, fontWeight: 600, color: "#818cf8",
                        background: "rgba(99,102,241,0.12)", padding: "1px 6px", borderRadius: 20,
                      }}>{item.tag}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── STATS BAR ──────────────────────────────────────────────────── */}
      <div style={{
        borderTop: "1px solid rgba(99,102,241,0.12)",
        borderBottom: "1px solid rgba(99,102,241,0.12)",
        background: "rgba(255,255,255,0.015)",
        padding: "20px 40px",
      }}>
        <div style={{
          maxWidth: 1280, margin: "0 auto",
          display: "grid", gridTemplateColumns: "repeat(5,1fr)",
          gap: 16, textAlign: "center",
        }}>
          {STATS.map((s, i) => (
            <div key={s.label} style={{
              borderLeft: i > 0 ? "1px solid rgba(255,255,255,0.06)" : "none",
              paddingLeft: i > 0 ? 16 : 0,
            }}>
              <div style={{ fontSize: 26, fontWeight: 900, color: s.color, letterSpacing: "-0.02em" }}>{s.value}</div>
              <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── AGENTS GRID ────────────────────────────────────────────────── */}
      <section style={{ maxWidth: 1280, margin: "0 auto", padding: "80px 40px" }}>
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6366f1", marginBottom: 12 }}>
            Powerful Agents for Every Domain
          </p>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: "#fff", margin: 0, letterSpacing: "-0.02em" }}>
            Specialized Agents.{" "}
            <span style={{ background: "linear-gradient(135deg,#6366f1,#a78bfa)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Real Impact.
            </span>
          </h2>
          <p style={{ fontSize: 15, color: "#6b7280", maxWidth: 480, margin: "12px auto 0", lineHeight: 1.6 }}>
            From research to real-time news, our domain-specific agents work together to solve complex problems and deliver reliable results.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
          {AGENTS_GRID.map(agent => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS ───────────────────────────────────────────────── */}
      <section style={{ borderTop: "1px solid rgba(255,255,255,0.05)", padding: "80px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 48 }}>
            <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#6366f1", marginBottom: 12 }}>Architecture</p>
            <h2 style={{ fontSize: 36, fontWeight: 900, color: "#fff", margin: 0 }}>Built for Reliability</h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20 }}>
            {[
              { step: "01", title: "Ingest", icon: "📡", desc: "12+ real RSS feeds ingested, normalized, and deduplicated in real-time via RabbitMQ event bus." },
              { step: "02", title: "Analyze", icon: "🧠", desc: "Specialized agents extract claims, verify against evidence, and build confidence-rated summaries." },
              { step: "03", title: "Deliver", icon: "⚡", desc: "Evidence-backed intelligence delivered via WebSocket — confirmed, conflicting, unknown clearly separated." },
            ].map((s, i) => (
              <div key={s.step} style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(99,102,241,0.14)",
                borderRadius: 18, padding: 28,
                transition: "transform 0.18s, border-color 0.18s",
              }}
                onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-4px)"; e.currentTarget.style.borderColor = "rgba(99,102,241,0.35)"; }}
                onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.borderColor = "rgba(99,102,241,0.14)"; }}
              >
                <div style={{ fontSize: 36, marginBottom: 16 }}>{s.icon}</div>
                <div style={{ fontSize: 11, fontWeight: 800, color: "#6366f1", marginBottom: 6 }}>{s.step}</div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: "#fff", margin: "0 0 10px 0" }}>{s.title}</h3>
                <p style={{ fontSize: 13, color: "#6b7280", lineHeight: 1.65, margin: 0 }}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────────────── */}
      <section style={{ padding: "80px 40px", textAlign: "center", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(circle at 50% 50%, rgba(99,102,241,0.08), transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "relative", maxWidth: 600, margin: "0 auto" }}>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: "#fff", margin: "0 0 12px", letterSpacing: "-0.02em" }}>
            Start orchestrating<br />your agents today
          </h2>
          <p style={{ fontSize: 15, color: "#6b7280", marginBottom: 32 }}>
            Set up in minutes. All infrastructure included via Docker Compose.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 12 }}>
            <Link href="/dashboard" style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              padding: "14px 32px", borderRadius: 12,
              background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
              color: "#fff", fontWeight: 700, fontSize: 15, textDecoration: "none",
              boxShadow: "0 8px 28px rgba(99,102,241,0.45)",
            }}>
              Open Dashboard →
            </Link>
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" style={{
              display: "inline-flex", alignItems: "center",
              padding: "14px 32px", borderRadius: 12,
              background: "transparent", border: "1px solid rgba(255,255,255,0.12)",
              color: "#cbd5e1", fontWeight: 700, fontSize: 15, textDecoration: "none",
            }}>
              View on GitHub
            </a>
          </div>
          <div style={{ display: "flex", justifyContent: "center", gap: 28, marginTop: 28, fontSize: 12, color: "#4b5563" }}>
            {["✓ Open source","✓ Docker Compose","✓ Mistral AI powered","✓ Evidence-backed"].map(f => <span key={f}>{f}</span>)}
          </div>
        </div>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────── */}
      <footer style={{
        borderTop: "1px solid rgba(255,255,255,0.05)",
        padding: "24px 40px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        maxWidth: "none",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 24, height: 24, borderRadius: 6, background: "linear-gradient(135deg,#6366f1,#8b5cf6)", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 12, color: "#fff" }}>A</div>
          <span style={{ fontWeight: 700, fontSize: 13, color: "#6b7280" }}>AgentOS</span>
          <span style={{ color: "#374151" }}>·</span>
          <span style={{ fontSize: 12, color: "#374151" }}>Distributed Agentic AI Platform</span>
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          {[
            { label: "Dashboard", href: "/dashboard" },
            { label: "AI News",   href: "/dashboard/newsflow" },
            { label: "Agents",    href: "/dashboard/agents" },
          ].map(l => (
            <Link key={l.label} href={l.href} style={{ fontSize: 12, color: "#4b5563", textDecoration: "none" }}
              onMouseEnter={e => e.currentTarget.style.color = "#9ca3af"}
              onMouseLeave={e => e.currentTarget.style.color = "#4b5563"}
            >{l.label}</Link>
          ))}
        </div>
      </footer>
    </div>
  );
}

/* Agent Card component */
function AgentCard({ agent }: { agent: typeof AGENTS_GRID[0] }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered ? `${agent.color}0d` : "rgba(255,255,255,0.02)",
        border: `1px solid ${hovered ? agent.color + "55" : "rgba(255,255,255,0.06)"}`,
        borderRadius: 16, padding: "22px 22px",
        transform: hovered ? "translateY(-4px)" : "none",
        boxShadow: hovered ? `0 10px 32px ${agent.color}1a` : "none",
        transition: "all 0.2s",
        cursor: "default",
      }}
    >
      <div style={{
        width: 48, height: 48, borderRadius: 12,
        background: `${agent.color}1a`, border: `1px solid ${agent.color}33`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 22, marginBottom: 14,
      }}>{agent.icon}</div>
      <h3 style={{ fontWeight: 700, fontSize: 14, color: "#f1f5f9", margin: "0 0 8px" }}>{agent.name}</h3>
      <p style={{ fontSize: 12, color: "#6b7280", lineHeight: 1.6, margin: "0 0 12px" }}>{agent.desc}</p>
      <div style={{ display: "flex", alignItems: "center", gap: 4, color: agent.color, fontSize: 11, fontWeight: 600 }}>
        <span>✓</span><span>Active</span>
      </div>
    </div>
  );
}
