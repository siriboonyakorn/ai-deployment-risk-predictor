"use client";

import { useState } from "react";

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      <div className="mb-4">
        <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{title}</div>
        <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{description}</div>
      </div>
      {children}
    </div>
  );
}

function InputField({
  label,
  placeholder,
  value,
  type = "text",
  onChange,
  hint,
}: {
  label: string;
  placeholder: string;
  value: string;
  type?: string;
  onChange: (v: string) => void;
  hint?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-muted)" }}>
        {label}
      </label>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-md text-sm font-mono outline-none"
        style={{
          background: "var(--surface-raised)",
          border: "1px solid var(--border)",
          color: "var(--foreground)",
        }}
      />
      {hint && (
        <p className="text-[11px] mt-1.5" style={{ color: "var(--text-muted)" }}>{hint}</p>
      )}
    </div>
  );
}

function ComingSoonSection({
  title,
  description,
  items,
}: {
  title: string;
  description: string;
  items: string[];
}) {
  return (
    <div
      className="card p-5 opacity-60"
      style={{ borderStyle: "dashed" }}
    >
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>{title}</div>
          <div className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{description}</div>
        </div>
        <span
          className="badge flex-shrink-0"
          style={{ background: "var(--surface-raised)", color: "var(--text-muted)", borderColor: "var(--border)" }}
        >
          Coming Soon
        </span>
      </div>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item} className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
            <span className="w-1 h-1 rounded-full bg-current opacity-40 flex-shrink-0" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function SettingsPage() {
  const [githubToken, setGithubToken] = useState("");
  const [apiUrl, setApiUrl] = useState("http://localhost:8000");
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    // In a real app these would be persisted to .env or a secrets store.
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 border-b flex-shrink-0"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <div>
          <h1 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
            Settings
          </h1>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            API configuration, integrations and preferences
          </p>
        </div>
      </header>

      <main className="flex-1 p-6">
        <div className="max-w-2xl space-y-4">
          {/* API Configuration */}
          <form onSubmit={handleSave}>
            <Section
              title="API Configuration"
              description="Connect the dashboard to the FastAPI backend and GitHub API."
            >
              <div className="space-y-4">
                <InputField
                  label="Backend API URL"
                  placeholder="http://localhost:8000"
                  value={apiUrl}
                  onChange={setApiUrl}
                  hint="The URL of the FastAPI backend. Next.js rewrites /api/v1/* to this host."
                />
                <InputField
                  label="GitHub Personal Access Token"
                  placeholder="github_pat_…"
                  type="password"
                  value={githubToken}
                  onChange={setGithubToken}
                  hint="Required for private repositories and higher GitHub API rate limits. Set GITHUB_TOKEN in backend/.env for server-side fetches."
                />
                <div className="pt-1">
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-md text-sm font-medium transition-opacity hover:opacity-80"
                    style={{ background: "var(--accent)", color: "white" }}
                  >
                    {saved ? "✓ Saved" : "Save Changes"}
                  </button>
                </div>
              </div>
            </Section>
          </form>

          {/* App info */}
          <Section
            title="Application Info"
            description="Current build and model information."
          >
            <div className="space-y-2 text-xs font-mono">
              {[
                ["Version", "0.1.0"],
                ["Stage", "MVP — Rule-based scoring"],
                ["Model", "rule-v1 (scikit-learn LR planned)"],
                ["Backend", "FastAPI + SQLAlchemy"],
                ["Database", "SQLite (dev) / PostgreSQL (prod)"],
                ["Queue", "Redis + Celery (configured)"],
              ].map(([k, v]) => (
                <div key={k} className="flex items-center gap-3">
                  <span className="w-28 flex-shrink-0" style={{ color: "var(--text-muted)" }}>{k}</span>
                  <span style={{ color: "var(--foreground)" }}>{v}</span>
                </div>
              ))}
            </div>
          </Section>

          {/* Coming-soon sections */}
          <ComingSoonSection
            title="GitHub OAuth"
            description="Sign in with GitHub for automatic repo access and PR commenting."
            items={[
              "GitHub OAuth flow (CLIENT_ID + CLIENT_SECRET configured)",
              "Auto-connect user repositories",
              "Post risk score as PR comment",
              "Webhook auto-registration",
            ]}
          />

          <ComingSoonSection
            title="Notifications"
            description="Get alerted when high-risk commits are detected."
            items={[
              "Email alerts for HIGH risk commits",
              "Slack / Discord webhook notifications",
              "Per-repository alert thresholds",
              "Daily digest reports",
            ]}
          />

          <ComingSoonSection
            title="Team & Access Control"
            description="Manage team members and repository permissions."
            items={[
              "Invite team members",
              "Role-based access (Admin / Viewer)",
              "Audit log",
              "Enterprise SSO",
            ]}
          />

          <ComingSoonSection
            title="Billing"
            description="SaaS subscription management."
            items={[
              "Free tier: 3 repos, 500 commits/month",
              "Pro tier: unlimited repos + ML model",
              "Enterprise: on-premise deployment",
            ]}
          />
        </div>
      </main>
    </div>
  );
}
