"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import {
  Search,
  ArrowRight,
  Play,
  CheckCircle,
  Newspaper,
  ChevronRight,
  Clock,
} from "lucide-react";

// ─── Agent nodes around the globe ───────────────────────────────────────────
const AGENT_NODES = [
  { id: "research",   label: "Research",   icon: "📄", angle:  30, dist: 175, color: "#a78bfa" },
  { id: "news",       label: "News",       icon: "📰", angle:  75, dist: 175, color: "#38bdf8" },
  { id: "finance",    label: "Finance",    icon: "📊", angle: 125, dist: 175, color: "#fbbf24" },
  { id: "security",   label: "Security",   icon: "🛡️", angle: 165, dist: 175, color: "#f87171" },
  { id: "coding",     label: "Coding",     icon: "💻", angle: 215, dist: 175, color: "#34d399" },
  { id: "healthcare", label: "Healthcare", icon: "❤️", angle: 255, dist: 175, color: "#f472b6" },
  { id: "legal",      label: "Legal",      icon: "⚖️", angle: 300, dist: 175, color: "#fb923c" },
  { id: "creative",   label: "Creative",   icon: "🎨", angle: 345, dist: 175, color: "#818cf8" },
];

// ─── Latest AI news (mock) ──────────────────────────────────────────────────
const LATEST_NEWS = [
  { id: 1, title: "OpenAI unveils GPT-5 with advanced reasoning capabilities", time: "2 hours ago", tag: "AI Models", logo: "🤖" },
  { id: 2, title: "Anthropic introduces Claude 3.5 with enhanced tool use",    time: "5 hours ago", tag: "AI Models", logo: "🔬" },
  { id: 3, title: "Google DeepMind achieves new milestone in AI safety",        time: "8 hours ago", tag: "AI Safety", logo: "🔷" },
  { id: 4, title: "Microsoft expands Copilot to more enterprise tools",         time: "12 hours ago", tag: "Enterprise", logo: "🟦" },
  { id: 5, title: "Meta releases open-source AI model for edge devices",        time: "1 day ago",  tag: "Open Source", logo: "🔵" },
];

// ─── Stats ──────────────────────────────────────────────────────────────────
const STATS = [
  { label: "Specialized Agents", value: "10+",    accent: "#a78bfa" },
  { label: "RabbitMQ Communication", value: "Real-time", accent: "#38bdf8" },
  { label: "AI News Monitoring",  value: "24/7",   accent: "#818cf8" },
  { label: "System Uptime",       value: "99.9%",  accent: "#a78bfa" },
  { label: "Knowledge Coverage",  value: "Global", accent: "#38bdf8" },
];

// ─── Specialized agents section ──────────────────────────────────────────────
const AGENTS = [
  { name: "Research Agent",  icon: "📄", color: "#a78bfa", desc: "Deep web research with source credibility scoring and evidence synthesis." },
  { name: "News Agent",      icon: "📰", color: "#38bdf8", desc: "Real-time RSS ingestion from 12+ global news sources with deduplication." },
  { name: "Finance Agent",   icon: "📊", color: "#fbbf24", desc: "Market analysis, earnings reports, and economic indicator tracking." },
  { name: "Security Agent",  icon: "🛡️", color: "#f87171", desc: "Defensive threat analysis, CVE assessment, and incident investigation." },
  { name: "Coding Agent",    icon: "💻", color: "#34d399", desc: "Code analysis, debugging, documentation, and technical synthesis." },
  { name: "Legal Agent",     icon: "⚖️", color: "#fb923c", desc: "Regulatory compliance, contract analysis, and policy interpretation." },
];

export default function LandingPage() {
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [time, setTime] = useState(0);
  const rafRef = useRef<number | null>(null);

  // Animate orbital ring slowly
  useEffect(() => {
    let t = 0;
    function tick() {
      t += 0.003;
      setTime(t);
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div className="min-h-screen" style={{ background: "linear-gradient(135deg, #0a0f1e 0%, #0d1530 50%, #0a0e1c 100%)" }}>

      {/* ── NAVBAR ───────────────────────────────────────────────────────── */}
      <nav
        className="sticky top-0 z-50 flex items-center px-6 py-3 border-b"
        style={{ background: "rgba(10,15,30,0.85)", backdropFilter: "blur(20px)", borderColor: "rgba(99,102,241,0.15)" }}
      >
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 mr-10">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center font-black text-white text-sm" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
            A
          </div>
          <div>
            <span className="font-bold text-white text-[15px]">AgentOS</span>
            <div className="text-[9px] text-indigo-400 leading-none">Many Agents. One Intelligence.</div>
          </div>
        </Link>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-6 mr-auto">
          {["Home", "Agents", "AI News", "Use Cases", "Docs", "Pricing"].map((item, i) => (
            <Link
              key={item}
              href={item === "Home" ? "/" : item === "Agents" ? "/dashboard/agents" : item === "AI News" ? "/dashboard/newsflow" : "#"}
              className={`text-sm transition-colors ${i === 0 ? "text-white font-medium border-b-2 border-indigo-500 pb-0.5" : "text-slate-400 hover:text-white"}`}
            >
              {item}
            </Link>
          ))}
        </div>

        {/* Right */}
        <div className="flex items-center gap-3 ml-6">
          <button className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors">
            <Search size={15} />
          </button>
          <Link href="/dashboard" className="text-sm text-slate-300 hover:text-white transition-colors">
            Sign In
          </Link>
          <Link
            href="/dashboard"
            className="px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all hover:opacity-90 hover:shadow-lg"
            style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 4px 15px rgba(99,102,241,0.3)" }}
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/3 left-1/4 w-[500px] h-[500px] rounded-full opacity-10" style={{ background: "radial-gradient(circle, #6366f1, transparent)" }} />
          <div className="absolute top-1/4 right-1/4 w-[400px] h-[400px] rounded-full opacity-8" style={{ background: "radial-gradient(circle, #8b5cf6, transparent)" }} />
        </div>

        <div className="relative max-w-screen-xl mx-auto px-6 pt-16 pb-8 grid grid-cols-1 lg:grid-cols-[1fr_auto_300px] gap-8 items-start">

          {/* LEFT — Copy */}
          <div className="space-y-7 pt-4">
            <div className="flex items-center gap-2 text-xs font-semibold tracking-widest text-indigo-400 uppercase">
              <span>Build</span><span className="text-slate-600">·</span>
              <span>Orchestrate</span><span className="text-slate-600">·</span>
              <span>Automate</span><span className="text-slate-600">·</span>
              <span>Stay Informed</span>
            </div>

            <h1 className="text-5xl font-black leading-[1.08] tracking-tight text-white">
              The Agentic AI
              <br />
              Platform for a{" "}
              <span style={{ background: "linear-gradient(135deg, #6366f1, #a78bfa)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Smarter
                <br />
                Tomorrow
              </span>
            </h1>

            <p className="text-slate-400 text-base leading-relaxed max-w-md">
              A unified platform of specialized AI agents that collaborate across domains, communicate via RabbitMQ, and deliver trusted, real-time intelligence — including the latest AI news.
            </p>

            <div className="flex items-center gap-3">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all hover:opacity-90 hover:shadow-xl hover:-translate-y-0.5"
                style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 6px 20px rgba(99,102,241,0.4)" }}
              >
                Get Started <ArrowRight size={15} />
              </Link>
              <button className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white border transition-all hover:bg-white/5"
                style={{ borderColor: "rgba(255,255,255,0.15)" }}>
                <div className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center">
                  <Play size={9} fill="white" />
                </div>
                Watch Demo
              </button>
            </div>

            {/* Feature pills */}
            <div className="flex flex-wrap gap-4 pt-2">
              {[
                { icon: "🧩", label: "Modular", sub: "AI Agents" },
                { icon: "⚡", label: "Real-time", sub: "Communication" },
                { icon: "✅", label: "Trusted &", sub: "Verifiable Answers" },
                { icon: "📸", label: "Always Updated", sub: "with AI News" },
              ].map((f) => (
                <div key={f.label} className="flex items-center gap-2">
                  <span className="text-base">{f.icon}</span>
                  <div>
                    <div className="text-[11px] font-semibold text-slate-300">{f.label}</div>
                    <div className="text-[10px] text-slate-500">{f.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CENTER — Animated Globe */}
          <div className="relative flex items-center justify-center" style={{ width: 400, height: 400 }}>
            {/* SVG orbit connections */}
            <svg className="absolute inset-0 w-full h-full" style={{ overflow: "visible" }}>
              <defs>
                <radialGradient id="globeGrad" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="#1e3a8a" />
                  <stop offset="60%" stopColor="#1e1b4b" />
                  <stop offset="100%" stopColor="#0a0f1e" />
                </radialGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Orbit ring */}
              <ellipse cx="200" cy="200" rx="175" ry="60" fill="none" stroke="rgba(99,102,241,0.18)" strokeWidth="1" />

              {/* Agent connector lines */}
              {AGENT_NODES.map((node) => {
                const rad = (node.angle * Math.PI) / 180;
                const nx = 200 + node.dist * Math.cos(rad);
                const ny = 200 + node.dist * 0.34 * Math.sin(rad);
                return (
                  <line
                    key={node.id}
                    x1="200" y1="200"
                    x2={nx} y2={ny}
                    stroke={node.color}
                    strokeWidth={activeNode === node.id ? 1.5 : 0.8}
                    strokeOpacity={activeNode === node.id ? 0.9 : 0.35}
                    strokeDasharray={activeNode === node.id ? "4 2" : "3 4"}
                    style={{ transition: "all 0.2s" }}
                  />
                );
              })}

              {/* Globe sphere */}
              <circle cx="200" cy="200" r="72" fill="url(#globeGrad)" filter="url(#glow)" />
              <circle cx="200" cy="200" r="72" fill="none" stroke="rgba(99,102,241,0.5)" strokeWidth="1.5" />
              {/* Latitude rings */}
              <ellipse cx="200" cy="200" rx="72" ry="22" fill="none" stroke="rgba(99,102,241,0.2)" strokeWidth="0.8" />
              <ellipse cx="200" cy="186" rx="62" ry="16" fill="none" stroke="rgba(99,102,241,0.15)" strokeWidth="0.6" />
              <ellipse cx="200" cy="214" rx="62" ry="16" fill="none" stroke="rgba(99,102,241,0.15)" strokeWidth="0.6" />
              {/* Vertical meridian */}
              <line x1="200" y1="128" x2="200" y2="272" stroke="rgba(99,102,241,0.2)" strokeWidth="0.8" />
            </svg>

            {/* Globe center label */}
            <div className="absolute flex flex-col items-center justify-center z-10 pointer-events-none">
              <div className="w-10 h-10 mb-1 flex items-center justify-center rounded-xl font-black text-lg text-white" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}>A</div>
              <span className="text-white text-sm font-bold">AgentOS</span>
            </div>

            {/* Agent nodes */}
            {AGENT_NODES.map((node) => {
              const rad = (node.angle * Math.PI) / 180;
              const nx = 200 + node.dist * Math.cos(rad);
              const ny = 200 + node.dist * 0.34 * Math.sin(rad);
              const isActive = activeNode === node.id;
              return (
                <button
                  key={node.id}
                  onMouseEnter={() => setActiveNode(node.id)}
                  onMouseLeave={() => setActiveNode(null)}
                  className="absolute flex flex-col items-center gap-1 transition-all"
                  style={{
                    left: nx,
                    top: ny,
                    transform: "translate(-50%, -50%)",
                    zIndex: 20,
                  }}
                >
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow-lg transition-all"
                    style={{
                      background: `${node.color}22`,
                      border: `1.5px solid ${node.color}${isActive ? "88" : "44"}`,
                      transform: isActive ? "scale(1.15)" : "scale(1)",
                      boxShadow: isActive ? `0 0 16px ${node.color}55` : "none",
                    }}
                  >
                    {node.icon}
                  </div>
                  <span className="text-[10px] font-semibold text-slate-300 whitespace-nowrap" style={{ textShadow: "0 1px 4px rgba(0,0,0,0.9)" }}>
                    {node.label}
                    <br />
                    <span className="text-slate-500">Agent</span>
                  </span>
                </button>
              );
            })}
          </div>

          {/* RIGHT — Latest AI News */}
          <div
            className="rounded-2xl p-4 flex flex-col gap-3"
            style={{ background: "rgba(15,20,40,0.9)", border: "1px solid rgba(99,102,241,0.2)", backdropFilter: "blur(16px)" }}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-bold text-white">Latest AI News</span>
              <Link href="/dashboard/newsflow" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5">
                View All <ChevronRight size={11} />
              </Link>
            </div>

            {LATEST_NEWS.map((item) => (
              <div
                key={item.id}
                className="flex items-start gap-2.5 p-2.5 rounded-xl cursor-pointer transition-all hover:bg-white/5"
              >
                <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-base shrink-0">
                  {item.logo}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-slate-200 leading-snug line-clamp-2 font-medium">
                    {item.title}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <Clock size={9} className="text-slate-500" />
                    <span className="text-[10px] text-slate-500">{item.time}</span>
                    <span className="text-[9px] text-indigo-400 bg-indigo-950 px-1.5 py-0.5 rounded-full font-semibold">
                      {item.tag}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── STATS BAR ────────────────────────────────────────────────────── */}
      <div className="border-y" style={{ borderColor: "rgba(99,102,241,0.12)", background: "rgba(255,255,255,0.02)" }}>
        <div className="max-w-screen-xl mx-auto px-6 py-5 grid grid-cols-2 md:grid-cols-5 gap-4">
          {STATS.map((s, i) => (
            <div key={s.label} className={`text-center ${i > 0 ? "border-l border-slate-800" : ""}`}>
              <div className="text-2xl font-black" style={{ color: s.accent }}>{s.value}</div>
              <div className="text-xs text-slate-500 mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── AGENTS SECTION ───────────────────────────────────────────────── */}
      <section className="max-w-screen-xl mx-auto px-6 py-20">
        <div className="text-center mb-12">
          <p className="text-xs font-bold tracking-widest uppercase text-indigo-400 mb-3">
            Powerful Agents for Every Domain
          </p>
          <h2 className="text-4xl font-black text-white">
            Specialized Agents.{" "}
            <span style={{ background: "linear-gradient(135deg,#6366f1,#a78bfa)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Real Impact.
            </span>
          </h2>
          <p className="text-slate-400 mt-3 max-w-md mx-auto text-sm leading-relaxed">
            From research to real-time news, our domain-specific agents work together to solve complex problems and deliver reliable results.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {AGENTS.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────────────────────── */}
      <section className="border-t border-slate-800 py-20">
        <div className="max-w-screen-xl mx-auto px-6">
          <div className="text-center mb-12">
            <p className="text-xs font-bold tracking-widest uppercase text-indigo-400 mb-3">
              Architecture
            </p>
            <h2 className="text-4xl font-black text-white">Built for Reliability</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { step: "01", title: "Ingest", desc: "12+ real RSS feeds ingested, normalized, and deduplicated in real-time via RabbitMQ event bus.", icon: "📡" },
              { step: "02", title: "Analyze", desc: "Specialized agents extract claims, verify against evidence, and build confidence-rated summaries.", icon: "🧠" },
              { step: "03", title: "Deliver", desc: "Evidence-backed intelligence delivered via WebSocket and REST API — confirmed, conflicting, unknown clearly separated.", icon: "⚡" },
            ].map((s) => (
              <div
                key={s.step}
                className="relative rounded-2xl p-6 transition-all hover:-translate-y-1"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(99,102,241,0.15)" }}
              >
                <div className="text-4xl mb-4">{s.icon}</div>
                <div className="text-xs font-black text-indigo-500 mb-1">{s.step}</div>
                <h3 className="text-lg font-bold text-white mb-2">{s.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="py-20 text-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ background: "radial-gradient(circle at 50% 50%, #6366f1, transparent)" }} />
        <div className="relative max-w-2xl mx-auto px-6">
          <h2 className="text-4xl font-black text-white mb-4">
            Start orchestrating your agents today
          </h2>
          <p className="text-slate-400 mb-8">
            Set up in minutes. All infrastructure included via Docker Compose.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/dashboard"
              className="px-8 py-4 rounded-xl font-bold text-white flex items-center gap-2 hover:opacity-90 transition-all hover:shadow-2xl"
              style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 8px 30px rgba(99,102,241,0.4)" }}
            >
              Open Dashboard <ArrowRight size={16} />
            </Link>
            <a
              href="https://github.com/CHETAN-0101/Distributed-Agentic-AI-News-Platform"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-4 rounded-xl font-bold text-slate-300 border border-slate-700 hover:border-slate-500 transition-all"
            >
              View on GitHub
            </a>
          </div>
          <div className="flex items-center justify-center gap-6 mt-8 text-xs text-slate-500">
            {["✓ Open source", "✓ Docker Compose", "✓ Mistral AI powered", "✓ Evidence-backed"].map((f) => (
              <span key={f}>{f}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-800 py-8">
        <div className="max-w-screen-xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md flex items-center justify-center font-black text-white text-xs" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}>A</div>
            <span className="text-sm font-bold text-slate-400">AgentOS</span>
            <span className="text-slate-700">·</span>
            <span className="text-xs text-slate-600">Distributed Agentic AI Platform</span>
          </div>
          <div className="flex gap-6 text-xs text-slate-600">
            <Link href="/dashboard" className="hover:text-slate-400 transition-colors">Dashboard</Link>
            <Link href="/dashboard/newsflow" className="hover:text-slate-400 transition-colors">AI News</Link>
            <Link href="/dashboard/agents" className="hover:text-slate-400 transition-colors">Agents</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function AgentCard({ agent }: { agent: typeof AGENTS[0] }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="rounded-2xl p-5 cursor-pointer transition-all duration-200"
      style={{
        background: hovered ? `${agent.color}0a` : "rgba(255,255,255,0.02)",
        border: `1px solid ${hovered ? agent.color + "44" : "rgba(255,255,255,0.06)"}`,
        transform: hovered ? "translateY(-3px)" : "none",
        boxShadow: hovered ? `0 8px 30px ${agent.color}22` : "none",
      }}
    >
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl mb-3"
        style={{ background: `${agent.color}18`, border: `1px solid ${agent.color}33` }}
      >
        {agent.icon}
      </div>
      <h3 className="text-sm font-bold text-white mb-1.5">{agent.name}</h3>
      <p className="text-xs text-slate-400 leading-relaxed">{agent.desc}</p>
      <div className="flex items-center gap-1 mt-3" style={{ color: agent.color }}>
        <CheckCircle size={11} />
        <span className="text-[10px] font-semibold">Active</span>
      </div>
    </div>
  );
}
