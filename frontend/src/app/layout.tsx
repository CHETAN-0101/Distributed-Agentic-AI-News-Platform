import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/providers/QueryProvider";


export const metadata: Metadata = {
  title: "AgentOS — Distributed Agentic AI Platform",
  description:
    "A reliable operating layer for autonomous AI agents. Multi-agent intelligence platform with distributed tracing, evidence-backed results, and real-time observability.",
  keywords: "AI agents, distributed AI, multi-agent, news intelligence, AgentOS",
  openGraph: {
    title: "AgentOS",
    description: "Distributed Agentic AI Intelligence Platform",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  );
}
