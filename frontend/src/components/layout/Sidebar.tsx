"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Newspaper,
  Workflow,
  Bot,
  ShieldCheck,
  Brain,
  Activity,
  Settings,
  Zap,
  ChevronRight,
} from "lucide-react";
import { clsx } from "clsx";

const NAV_ITEMS = [
  {
    section: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/dashboard/agents", label: "Agents", icon: Bot },
      { href: "/dashboard/workflows", label: "Workflows", icon: Workflow },
    ],
  },
  {
    section: "NewsFlow AI",
    items: [
      { href: "/dashboard/newsflow", label: "News Intelligence", icon: Newspaper },
    ],
  },
  {
    section: "Intelligence",
    items: [
      { href: "/dashboard/memory", label: "Memory", icon: Brain },
      { href: "/dashboard/approvals", label: "Approvals", icon: ShieldCheck },
    ],
  },
  {
    section: "Observability",
    items: [
      { href: "/dashboard/metrics", label: "Metrics", icon: Activity },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar flex flex-col">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-[hsl(var(--border-subtle))]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg gradient-brand flex items-center justify-center shadow-lg">
            <Zap size={16} className="text-white" />
          </div>
          <div>
            <div className="font-bold text-[15px] tracking-tight gradient-text">
              AgentOS
            </div>
            <div className="text-[10px] text-[hsl(var(--text-muted))] font-medium tracking-widest uppercase">
              Platform
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        {NAV_ITEMS.map((section) => (
          <div key={section.section}>
            <div className="text-[10px] font-semibold tracking-widest uppercase text-[hsl(var(--text-muted))] px-3 mb-1.5">
              {section.section}
            </div>
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  item.href === "/dashboard"
                    ? pathname === "/dashboard"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx("sidebar-item", isActive && "active")}
                  >
                    <Icon size={16} />
                    <span>{item.label}</span>
                    {isActive && (
                      <ChevronRight
                        size={12}
                        className="ml-auto opacity-50"
                      />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-[hsl(var(--border-subtle))]">
        <Link href="/settings" className="sidebar-item w-full">
          <Settings size={16} />
          <span>Settings</span>
        </Link>
        <div className="mt-3 px-3">
          <div className="text-[10px] text-[hsl(var(--text-muted))]">
            AgentOS v1.0.0
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <div className="pulse-dot healthy w-2 h-2" />
            <span className="text-[11px] text-[hsl(var(--status-healthy))]">
              All systems operational
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
