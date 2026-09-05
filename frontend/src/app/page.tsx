"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";

/* ──────────────────────────────────────────────────────────────────────────
   DATA
   ──────────────────────────────────────────────────────────────────────── */
const AGENT_NODES = [
  { id: "coding",     label: "Coding",     icon: "💻", angle: 270, color: "#34d399" },
  { id: "healthcare", label: "Healthcare", icon: "❤️", angle: 315, color: "#f472b6" },
  { id: "legal",      label: "Legal",      icon: "⚖️", angle:   0, color: "#fb923c" },
  { id: "creative",   label: "Creative",   icon: "🎨", angle:  45, color: "#818cf8" },
  { id: "research",   label: "Research",   icon: "📄", angle:  90, color: "#a78bfa" },
  { id: "news",       label: "News",       icon: "📰", angle: 135, color: "#38bdf8" },
  { id: "finance",    label: "Finance",    icon: "📊", angle: 180, color: "#fbbf24" },
  { id: "security",   label: "Security",   icon: "🛡️", angle: 225, color: "#f87171" },
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
   GLOBE (3D Orbit & Spacing)
   ──────────────────────────────────────────────────────────────────────── */
const VIZ_W = 460;
const VIZ_H = 340;
const CX = 230;
const CY = 170;
const ORBIT_RX = 185;
const ORBIT_RY = 82;
const GLOBE_RADIUS = 64;

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

  // Compute animated positions with 3D projection & depth layering
  const nodesWithPos = AGENT_NODES.map((n, idx) => {
    // Smooth 3D orbit rotation: 10 deg/sec
    const currentAngle = (n.angle + time * 10) % 360;
    const rad = degToRad(currentAngle);
    const cosVal = Math.cos(rad);
    const sinVal = Math.sin(rad);

    const x = CX + ORBIT_RX * cosVal;
    const bob = Math.sin(time * 2.2 + idx * 1.2) * 3.5;
    const y = CY + ORBIT_RY * sinVal + bob;

    // Depth: -1 (furthest back) to +1 (closest front)
    const isBack = sinVal < 0;
    const depth = (sinVal + 1) / 2; // 0 to 1
    const scale = 0.82 + depth * 0.32; // 0.82 (back) to 1.14 (front)
    const opacity = 0.58 + depth * 0.42; // 0.58 (back) to 1.0 (front)
    const zIndex = Math.round(5 + depth * 30); // 5 (back) to 35 (front)

    return {
      ...n,
      x,
      y,
      scale,
      opacity,
      zIndex,
      isBack,
      depth,
      rayPulse: 0.22 + 0.22 * Math.sin(time * 2.8 + idx * 0.8),
    };
  });

  const globePulse = 1 + 0.04 * Math.sin(time * 1.8);
  const glowOpacity = 0.35 + 0.12 * Math.sin(time * 1.8);
  const centerBob = Math.sin(time * 2.2) * 2;

  const renderRay = (n: typeof nodesWithPos[0]) => {
    const isA = active === n.id;
    return (
      <line
        key={n.id}
        x1={CX}
        y1={CY}
        x2={n.x}
        y2={n.y}
        stroke={n.color}
        strokeWidth={isA ? 2 : 1}
        strokeOpacity={isA ? 0.95 : n.rayPulse}
        strokeDasharray={isA ? "5 2" : "4 4"}
        strokeDashoffset={-time * 22}
      />
    );
  };

  return (
    <div style={{ position: "relative", width: VIZ_W, height: VIZ_H, flexShrink: 0, margin: "0 auto" }}>
      <svg
        width={VIZ_W}
        height={VIZ_H}
        style={{ overflow: "visible", position: "absolute", inset: 0 }}
      >
        <defs>
          <radialGradient id="g1" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="#1e3a8a" stopOpacity="1" />
            <stop offset="60%"  stopColor="#1e1b4b" stopOpacity="1" />
            <stop offset="100%" stopColor="#080c1a" stopOpacity="1" />
          </radialGradient>
          <radialGradient id="glow1" cx="50%" cy="30%" r="60%">
            <stop offset="0%"   stopColor="#6366f1" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="centerPulse" cx="50%" cy="50%" r="50%">
            <stop offset="0%"   stopColor="#818cf8" stopOpacity="0.45" />
            <stop offset="55%"  stopColor="#6366f1" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#4f46e5" stopOpacity="0" />
          </radialGradient>
          <filter id="blurGlobe">
            <feGaussianBlur in="SourceGraphic" stdDeviation="10" />
          </filter>
          <filter id="blurRing">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3" />
          </filter>
        </defs>

        {/* Ambient background aura */}
        <circle cx={CX} cy={CY} r={120 * globePulse} fill="url(#centerPulse)" />

        {/* Orbit ellipse (outer soft glow) */}
        <ellipse
          cx={CX}
          cy={CY}
          rx={ORBIT_RX}
          ry={ORBIT_RY}
          fill="none"
          stroke="rgba(99,102,241,0.35)"
          strokeWidth="2.5"
          filter="url(#blurRing)"
        />
        {/* Orbit ellipse with animated streaming dashes */}
        <ellipse
          cx={CX}
          cy={CY}
          rx={ORBIT_RX}
          ry={ORBIT_RY}
          fill="none"
          stroke="rgba(129,140,248,0.38)"
          strokeWidth="1.2"
          strokeDasharray="6 5"
          strokeDashoffset={-time * 14}
        />

        {/* 1. BACK RAYS (drawn behind the globe for true 3D occlusion) */}
        {nodesWithPos.filter(n => n.isBack).map(renderRay)}

        {/* 2. CENTER GLOBE */}
        <circle cx={CX} cy={CY} r={GLOBE_RADIUS * globePulse} fill="#6366f1" filter="url(#blurGlobe)" opacity={glowOpacity} />
        <circle cx={CX} cy={CY} r={GLOBE_RADIUS} fill="url(#g1)" />
        <circle cx={CX} cy={CY} r={GLOBE_RADIUS} fill="url(#glow1)" />
        <circle cx={CX} cy={CY} r={GLOBE_RADIUS} fill="none" stroke="rgba(99,102,241,0.65)" strokeWidth="1.5" />

        {/* Latitude grid lines */}
        <ellipse cx={CX} cy={CY} rx={GLOBE_RADIUS} ry={20} fill="none" stroke="rgba(99,102,241,0.25)" strokeWidth="0.8" />
        <ellipse cx={CX} cy={CY - 18} rx={54} ry={14} fill="none" stroke="rgba(99,102,241,0.18)" strokeWidth="0.6" />
        <ellipse cx={CX} cy={CY + 18} rx={54} ry={14} fill="none" stroke="rgba(99,102,241,0.18)" strokeWidth="0.6" />
        {/* Longitude vertical line */}
        <line
          x1={CX}
          y1={CY - GLOBE_RADIUS}
          x2={CX}
          y2={CY + GLOBE_RADIUS}
          stroke="rgba(99,102,241,0.25)"
          strokeWidth="0.8"
        />

        {/* 3. FRONT RAYS (drawn over the globe for depth) */}
        {nodesWithPos.filter(n => !n.isBack).map(renderRay)}
      </svg>

      {/* Center AgentOS Hub Badge (zIndex 18) */}
      <div
        style={{
          position: "absolute",
          left: CX,
          top: CY + centerBob,
          transform: "translate(-50%,-50%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 4,
          zIndex: 18,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 900,
            fontSize: 20,
            color: "#fff",
            boxShadow: `0 4px 28px rgba(99,102,241,${0.55 + 0.2 * Math.sin(time * 2)})`,
            transition: "box-shadow 0.2s",
          }}
        >
          A
        </div>
        <span
          style={{
            color: "#ffffff",
            fontWeight: 700,
            fontSize: 12,
            letterSpacing: "0.03em",
            textShadow: "0 2px 10px rgba(0,0,0,0.95)",
          }}
        >
          AgentOS
        </span>
      </div>

      {/* 4. ORBITING AGENT NODES */}
      {nodesWithPos.map((n) => {
        const isA = active === n.id;
        const currentScale = isA ? n.scale * 1.25 : n.scale;
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
              zIndex: isA ? 60 : n.zIndex,
              opacity: isA ? 1 : n.opacity,
              transition: "transform 0.15s ease-out, opacity 0.15s",
            }}
          >
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 11,
                background: `rgba(13,20,45,0.92)`,
                border: `1.5px solid ${n.color}${isA ? "ff" : "66"}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 19,
                boxShadow: isA
                  ? `0 0 24px ${n.color}99, inset 0 0 12px ${n.color}44`
                  : `0 2px 10px rgba(0,0,0,0.7), 0 0 12px ${n.color}22`,
                backdropFilter: "blur(8px)",
                transition: "all 0.18s",
              }}
            >
              {n.icon}
            </div>
            <div style={{ textAlign: "center", lineHeight: 1.15 }}>
              <div
                style={{
                  fontSize: 10.5,
                  fontWeight: 600,
                  color: isA ? "#ffffff" : "#f1f5f9",
                  textShadow: "0 1px 8px rgba(0,0,0,0.95)",
                  whiteSpace: "nowrap",
                }}
              >
                {n.label}
              </div>
              <div
                style={{
                  fontSize: 9,
                  fontWeight: 500,
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

const TYPED_WORDS = [
  "Smarter Tomorrow",
  "Autonomous Future",
  "Distributed Intelligence",
  "Real-Time Decisions",
  "Enterprise Scale",
];

function TypewriterText() {
  const [wordIdx, setWordIdx] = useState(0);
  const [displayedText, setDisplayedText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [blink, setBlink] = useState(true);

  // Blinking cursor
  useEffect(() => {
    const interval = setInterval(() => setBlink((b) => !b), 500);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const currentWord = TYPED_WORDS[wordIdx];
    let timer: NodeJS.Timeout;

    if (!isDeleting && displayedText === currentWord) {
      // Pause at full word so user can read comfortably
      timer = setTimeout(() => setIsDeleting(true), 3200);
    } else if (isDeleting && displayedText === "") {
      // Brief pause before starting next word
      timer = setTimeout(() => {
        setIsDeleting(false);
        setWordIdx((prev) => (prev + 1) % TYPED_WORDS.length);
      }, 400);
    } else {
      // Deliberate typing pace (135ms) and smooth backspacing (65ms)
      const speed = isDeleting ? 65 : 135;
      timer = setTimeout(() => {
        setDisplayedText((prev) =>
          isDeleting
            ? currentWord.substring(0, prev.length - 1)
            : currentWord.substring(0, prev.length + 1)
        );
      }, speed);
    }

    return () => clearTimeout(timer);
  }, [displayedText, isDeleting, wordIdx]);

  return (
    <span
      style={{
        display: "inline-block",
        background: "linear-gradient(135deg, #818cf8 0%, #c084fc 45%, #38bdf8 100%)",
        WebkitBackgroundClip: "text",
        WebkitTextFillColor: "transparent",
        textShadow: "0 0 35px rgba(129,140,248,0.35)",
        minHeight: "1.15em",
      }}
    >
      {displayedText}
      <span
        style={{
          opacity: blink ? 1 : 0,
          color: "#818cf8",
          WebkitTextFillColor: "#818cf8",
          marginLeft: 2,
          fontWeight: 400,
        }}
      >
        |
      </span>
    </span>
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
    <div
      style={{
        minHeight: "100vh",
        background: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.16), transparent 70%), #030712",
        backgroundImage:
          "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.035) 1px, transparent 0), radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99,102,241,0.18), transparent 70%), #030712",
        backgroundSize: "32px 32px, 100% 100%, 100% 100%",
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        color: "#e2e8f0",
      }}
    >
      {/* ── NAVBAR ─────────────────────────────────────────────────────── */}
      <nav
        style={{
          position: "sticky",
          top: 0,
          zIndex: 100,
          display: "flex",
          alignItems: "center",
          padding: "0 36px",
          height: 60,
          background: navScrolled ? "rgba(3,7,18,0.92)" : "rgba(3,7,18,0.72)",
          backdropFilter: "blur(24px)",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          transition: "background 0.3s, border-color 0.3s",
        }}
      >
        {/* Logo */}
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            textDecoration: "none",
            marginRight: 44,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 900,
              fontSize: 16,
              color: "#fff",
              boxShadow: "0 0 16px rgba(99,102,241,0.45)",
            }}
          >
            A
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15, color: "#fff", lineHeight: 1.1, letterSpacing: "-0.01em" }}>
              AgentOS
            </div>
            <div style={{ fontSize: 9, color: "#818cf8", lineHeight: 1, letterSpacing: "0.02em" }}>
              Distributed AI Platform
            </div>
          </div>
        </Link>

        {/* Nav links */}
        <div style={{ display: "flex", alignItems: "center", gap: 28, flex: 1 }}>
          {[
            { label: "Platform", href: "/" },
            { label: "Agents", href: "/dashboard/agents" },
            { label: "AI News", href: "/dashboard/newsflow" },
            { label: "Workflows", href: "/dashboard/workflows" },
            { label: "Approvals", href: "/dashboard/approvals" },
            { label: "Docs", href: "#" },
          ].map((item, i) => (
            <Link
              key={item.label}
              href={item.href}
              style={{
                textDecoration: "none",
                fontSize: 13.5,
                fontWeight: i === 0 ? 600 : 400,
                color: i === 0 ? "#ffffff" : "#94a3b8",
                borderBottom: i === 0 ? "2px solid #6366f1" : "none",
                paddingBottom: i === 0 ? 2 : 0,
                transition: "color 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#fff")}
              onMouseLeave={(e) => {
                if (i !== 0) e.currentTarget.style.color = "#94a3b8";
              }}
            >
              {item.label}
            </Link>
          ))}
        </div>

        {/* Right buttons */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 10px",
              borderRadius: 20,
              background: "rgba(16,185,129,0.08)",
              border: "1px solid rgba(16,185,129,0.25)",
              fontSize: 11,
              fontWeight: 600,
              color: "#34d399",
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", boxShadow: "0 0 6px #10b981" }} />
            <span>8 AGENTS ACTIVE</span>
          </div>

          <Link
            href="/dashboard"
            style={{
              fontSize: 13.5,
              color: "#cbd5e1",
              textDecoration: "none",
              padding: "6px 12px",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#fff")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#cbd5e1")}
          >
            Sign In
          </Link>
          <Link
            href="/dashboard"
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
              color: "#fff",
              fontWeight: 700,
              fontSize: 13.5,
              textDecoration: "none",
              boxShadow: "0 4px 14px rgba(99,102,241,0.35)",
              transition: "opacity 0.15s, transform 0.15s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.opacity = "0.88";
              e.currentTarget.style.transform = "translateY(-1px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = "1";
              e.currentTarget.style.transform = "none";
            }}
          >
            Open Platform
          </Link>
        </div>
      </nav>

      {/* ── HERO ───────────────────────────────────────────────────────── */}
      <section style={{ position: "relative", overflow: "hidden", padding: "64px 40px 48px" }}>
        {/* BG ambient glows */}
        <div
          style={{
            position: "absolute",
            top: "15%",
            left: "10%",
            width: 550,
            height: 550,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99,102,241,0.14), transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: "10%",
            right: "15%",
            width: 450,
            height: 450,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(139,92,246,0.12), transparent 70%)",
            pointerEvents: "none",
          }}
        />

        {/* 3-col layout */}
        <div
          style={{
            position: "relative",
            maxWidth: 1320,
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "1.05fr 460px 320px",
            gap: 24,
            alignItems: "center",
          }}
        >
          {/* LEFT: Headline & Actions */}
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Top pill badge */}
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 14px",
                borderRadius: 999,
                background: "rgba(99,102,241,0.08)",
                border: "1px solid rgba(99,102,241,0.28)",
                width: "fit-content",
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#818cf8",
                  boxShadow: "0 0 8px #818cf8",
                }}
              />
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  color: "#a5b4fc",
                }}
              >
                BUILD · ORCHESTRATE · AUTOMATE · STAY INFORMED
              </span>
            </div>

            {/* Autotyping Headline */}
            <h1
              style={{
                fontSize: 52,
                fontWeight: 900,
                lineHeight: 1.08,
                letterSpacing: "-0.03em",
                color: "#ffffff",
                margin: 0,
              }}
            >
              The Agentic AI
              <br />
              Platform for a{" "}
              <TypewriterText />
            </h1>

            <p
              style={{
                fontSize: 15,
                color: "#94a3b8",
                lineHeight: 1.65,
                maxWidth: 440,
                margin: 0,
              }}
            >
              A unified operating layer of specialized AI agents that collaborate across domains, communicate asynchronously via RabbitMQ, and deliver trusted, real-time intelligence.
            </p>

            {/* CTAs */}
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <Link
                href="/dashboard"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "13px 26px",
                  borderRadius: 10,
                  background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
                  color: "#fff",
                  fontWeight: 700,
                  fontSize: 14,
                  textDecoration: "none",
                  boxShadow: "0 6px 22px rgba(99,102,241,0.45)",
                  transition: "transform 0.15s, box-shadow 0.15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-2px)";
                  e.currentTarget.style.boxShadow = "0 10px 30px rgba(99,102,241,0.55)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "none";
                  e.currentTarget.style.boxShadow = "0 6px 22px rgba(99,102,241,0.45)";
                }}
              >
                Get Started <span style={{ fontSize: 16 }}>→</span>
              </Link>
              <Link
                href="/dashboard/newsflow"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "13px 24px",
                  borderRadius: 10,
                  cursor: "pointer",
                  background: "rgba(255,255,255,0.03)",
                  color: "#e2e8f0",
                  fontWeight: 600,
                  fontSize: 14,
                  textDecoration: "none",
                  border: "1px solid rgba(255,255,255,0.1)",
                  transition: "background 0.15s, border-color 0.15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.07)";
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.22)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                }}
              >
                <span
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    background: "rgba(255,255,255,0.08)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 10,
                  }}
                >
                  ▶
                </span>
                Live Intelligence
              </Link>
            </div>

            {/* Feature pills */}
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap", paddingTop: 4 }}>
              {[
                { icon: "🧩", label: "Modular", sub: "Autonomous Agents" },
                { icon: "⚡", label: "Real-time", sub: "RabbitMQ Events" },
                { icon: "✅", label: "Verifiable", sub: "Evidence Synthesis" },
                { icon: "📡", label: "Always Updated", sub: "24/7 AI News Flow" },
              ].map((f) => (
                <div key={f.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 16 }}>{f.icon}</span>
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "#cbd5e1", lineHeight: 1.2 }}>
                      {f.label}
                    </div>
                    <div style={{ fontSize: 10, color: "#64748b", lineHeight: 1.2 }}>{f.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CENTER: 3D Orbit Globe */}
          <GlobeViz />

          {/* RIGHT: Live News Panel */}
          <div
            style={{
              background: "rgba(10,15,30,0.85)",
              border: "1px solid rgba(255,255,255,0.08)",
              boxShadow: "0 20px 45px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05)",
              borderRadius: 18,
              padding: 18,
              backdropFilter: "blur(20px)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 14,
                paddingBottom: 10,
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background: "#38bdf8",
                    boxShadow: "0 0 8px #38bdf8",
                  }}
                />
                <span style={{ fontWeight: 700, fontSize: 13, color: "#fff", letterSpacing: "-0.01em" }}>
                  Live AI News
                </span>
              </div>
              <Link
                href="/dashboard/newsflow"
                style={{ fontSize: 11, fontWeight: 600, color: "#818cf8", textDecoration: "none" }}
              >
                Feed →
              </Link>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {LATEST_NEWS.map((item) => (
                <div
                  key={item.id}
                  style={{
                    display: "flex",
                    gap: 10,
                    padding: "10px 8px",
                    borderRadius: 10,
                    cursor: "pointer",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      background: item.bg,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 14,
                      flexShrink: 0,
                      border: "1px solid rgba(255,255,255,0.08)",
                    }}
                  >
                    {item.logo}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p
                      style={{
                        fontSize: 11.5,
                        fontWeight: 500,
                        color: "#e2e8f0",
                        lineHeight: 1.35,
                        margin: 0,
                        display: "-webkit-box",
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}
                    >
                      {item.title}
                    </p>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
                      <span style={{ fontSize: 9.5, color: "#64748b" }}>⏰ {item.time}</span>
                      <span
                        style={{
                          fontSize: 9,
                          fontWeight: 600,
                          color: "#818cf8",
                          background: "rgba(99,102,241,0.14)",
                          border: "1px solid rgba(99,102,241,0.25)",
                          padding: "1px 6px",
                          borderRadius: 20,
                        }}
                      >
                        {item.tag}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── STATS BAR ──────────────────────────────────────────────────── */}
      <div
        style={{
          borderTop: "1px solid rgba(255,255,255,0.06)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          background: "rgba(10,15,30,0.65)",
          backdropFilter: "blur(12px)",
          padding: "22px 40px",
        }}
      >
        <div
          style={{
            maxWidth: 1320,
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(5,1fr)",
            gap: 16,
            textAlign: "center",
          }}
        >
          {STATS.map((s, i) => (
            <div
              key={s.label}
              style={{
                borderLeft: i > 0 ? "1px solid rgba(255,255,255,0.06)" : "none",
                paddingLeft: i > 0 ? 16 : 0,
              }}
            >
              <div
                style={{
                  fontSize: 26,
                  fontWeight: 900,
                  color: s.color,
                  letterSpacing: "-0.02em",
                  textShadow: `0 0 20px ${s.color}33`,
                }}
              >
                {s.value}
              </div>
              <div style={{ fontSize: 11.5, color: "#64748b", marginTop: 2, fontWeight: 500 }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── AGENTS GRID ────────────────────────────────────────────────── */}
      <section style={{ maxWidth: 1320, margin: "0 auto", padding: "88px 40px" }}>
        <div style={{ textAlign: "center", marginBottom: 56 }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "#818cf8",
              marginBottom: 12,
            }}
          >
            Specialized Multi-Agent Mesh
          </p>
          <h2 style={{ fontSize: 42, fontWeight: 900, color: "#fff", margin: 0, letterSpacing: "-0.02em" }}>
            Specialized Agents.{" "}
            <span
              style={{
                background: "linear-gradient(135deg,#818cf8,#c084fc)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Real Autonomy.
            </span>
          </h2>
          <p
            style={{
              fontSize: 15,
              color: "#64748b",
              maxWidth: 520,
              margin: "12px auto 0",
              lineHeight: 1.65,
            }}
          >
            From web research to real-time AI news, each agent operates independently with its own tools, memory, and confidence scoring.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 18 }}>
          {AGENTS_GRID.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS ───────────────────────────────────────────────── */}
      <section
        style={{
          borderTop: "1px solid rgba(255,255,255,0.06)",
          background: "rgba(10,15,30,0.4)",
          padding: "88px 40px",
        }}
      >
        <div style={{ maxWidth: 1320, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: 52 }}>
            <p
              style={{
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "#818cf8",
                marginBottom: 12,
              }}
            >
              Architecture & Data Flow
            </p>
            <h2 style={{ fontSize: 38, fontWeight: 900, color: "#fff", margin: 0, letterSpacing: "-0.02em" }}>
              Engineered for Enterprise Reliability
            </h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 22 }}>
            {[
              {
                step: "01",
                title: "Ingest & Normalize",
                icon: "📡",
                desc: "12+ global RSS and live data feeds ingested, normalized, and deduplicated in real time over RabbitMQ event bus.",
              },
              {
                step: "02",
                title: "Synthesize & Verify",
                icon: "🧠",
                desc: "Specialized agents extract claims, cross-verify against evidence, and build confidence-rated summaries with source tracking.",
              },
              {
                step: "03",
                title: "Deliver & Act",
                icon: "⚡",
                desc: "Evidence-backed intelligence streamed live via WebSocket — separating verified facts, disputed claims, and unknowns.",
              },
            ].map((s) => (
              <div
                key={s.step}
                style={{
                  background: "rgba(10,15,30,0.7)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 18,
                  padding: 30,
                  boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
                  transition: "transform 0.18s, border-color 0.18s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-4px)";
                  e.currentTarget.style.borderColor = "rgba(99,102,241,0.4)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "none";
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                }}
              >
                <div style={{ fontSize: 38, marginBottom: 16 }}>{s.icon}</div>
                <div style={{ fontSize: 11, fontWeight: 800, color: "#818cf8", marginBottom: 6 }}>
                  {s.step}
                </div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: "#fff", margin: "0 0 10px 0" }}>
                  {s.title}
                </h3>
                <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.65, margin: 0 }}>
                  {s.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────────────── */}
      <section
        style={{
          padding: "88px 40px",
          textAlign: "center",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "radial-gradient(circle at 50% 50%, rgba(99,102,241,0.1), transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <div style={{ position: "relative", maxWidth: 640, margin: "0 auto" }}>
          <h2
            style={{
              fontSize: 42,
              fontWeight: 900,
              color: "#fff",
              margin: "0 0 14px",
              letterSpacing: "-0.02em",
            }}
          >
            Start orchestrating
            <br />
            your AI agents today
          </h2>
          <p style={{ fontSize: 15, color: "#64748b", marginBottom: 32 }}>
            Production-ready distributed AI runtime with RabbitMQ, Redis memory, and Docker Compose.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 14 }}>
            <Link
              href="/dashboard"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "14px 34px",
                borderRadius: 12,
                background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
                color: "#fff",
                fontWeight: 700,
                fontSize: 15,
                textDecoration: "none",
                boxShadow: "0 8px 28px rgba(99,102,241,0.45)",
              }}
            >
              Open Dashboard →
            </Link>
            <Link
              href="/dashboard/agents"
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "14px 30px",
                borderRadius: 12,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.12)",
                color: "#cbd5e1",
                fontWeight: 700,
                fontSize: 15,
                textDecoration: "none",
              }}
            >
              Explore Agents
            </Link>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 28,
              marginTop: 32,
              fontSize: 12,
              color: "#475569",
            }}
          >
            {["✓ Distributed Architecture", "✓ RabbitMQ Event Bus", "✓ Evidence Grounded", "✓ Docker Ready"].map(
              (f) => (
                <span key={f}>{f}</span>
              )
            )}
          </div>
        </div>
      </section>

      {/* ── FOOTER ─────────────────────────────────────────────────────── */}
      <footer
        style={{
          borderTop: "1px solid rgba(255,255,255,0.06)",
          padding: "24px 40px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: 6,
              background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 900,
              fontSize: 12,
              color: "#fff",
            }}
          >
            A
          </div>
          <span style={{ fontWeight: 700, fontSize: 13, color: "#94a3b8" }}>AgentOS</span>
          <span style={{ color: "#334155" }}>·</span>
          <span style={{ fontSize: 12, color: "#475569" }}>Distributed Agentic AI Intelligence Platform</span>
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          {[
            { label: "Dashboard", href: "/dashboard" },
            { label: "AI News", href: "/dashboard/newsflow" },
            { label: "Agents", href: "/dashboard/agents" },
            { label: "Workflows", href: "/dashboard/workflows" },
          ].map((l) => (
            <Link
              key={l.label}
              href={l.href}
              style={{ fontSize: 12, color: "#475569", textDecoration: "none" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#94a3af")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#475569")}
            >
              {l.label}
            </Link>
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
        background: hovered ? `${agent.color}0d` : "rgba(10,15,30,0.65)",
        border: `1px solid ${hovered ? agent.color + "66" : "rgba(255,255,255,0.07)"}`,
        borderRadius: 16,
        padding: "24px",
        transform: hovered ? "translateY(-4px)" : "none",
        boxShadow: hovered ? `0 12px 36px ${agent.color}22` : "0 4px 16px rgba(0,0,0,0.4)",
        transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
        cursor: "default",
        backdropFilter: "blur(12px)",
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 12,
          background: `${agent.color}18`,
          border: `1px solid ${agent.color}44`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 22,
          marginBottom: 16,
          boxShadow: `0 0 16px ${agent.color}22`,
        }}
      >
        {agent.icon}
      </div>
      <h3 style={{ fontWeight: 700, fontSize: 15, color: "#f1f5f9", margin: "0 0 8px", letterSpacing: "-0.01em" }}>
        {agent.name}
      </h3>
      <p style={{ fontSize: 12.5, color: "#64748b", lineHeight: 1.6, margin: "0 0 16px" }}>{agent.desc}</p>
      <div style={{ display: "flex", alignItems: "center", gap: 6, color: agent.color, fontSize: 11.5, fontWeight: 600 }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: agent.color, boxShadow: `0 0 6px ${agent.color}` }} />
        <span>Active Node</span>
      </div>
    </div>
  );
}
