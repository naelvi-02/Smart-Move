"use client";
import { useState, useEffect, useRef } from "react";
import { Pause, X, RefreshCw, ChevronRight, Circle } from "lucide-react";

type LogLevel = "INFO" | "CACHE" | "OK" | "WARN" | "DONE" | "ERROR";

interface LogEntry {
  id: number;
  time: string;
  level: LogLevel;
  message: string;
}

const SEED_LOGS: LogEntry[] = [
  { id: 1, time: "12:48:21", level: "INFO",  message: "Sync started — 100,000 records queued" },
  { id: 2, time: "12:48:24", level: "INFO",  message: "Connecting to model registry (us-east-1)" },
  { id: 3, time: "12:48:29", level: "CACHE", message: "Cloudflare edge refreshed (us-east-1, eu-west-2)" },
  { id: 4, time: "12:48:31", level: "INFO",  message: "Processing batch 652..." },
  { id: 5, time: "12:48:32", level: "OK",    message: "Batch 652 completed in 412ms" },
  { id: 6, time: "12:48:33", level: "INFO",  message: "Processing batch 653..." },
  { id: 7, time: "12:48:34", level: "OK",    message: "Batch 653 completed in 388ms" },
  { id: 8, time: "12:48:35", level: "WARN",  message: "Retry request #18 — upstream timeout (5s)" },
  { id: 9, time: "12:48:38", level: "INFO",  message: "Processing batch 654..." },
  { id: 10, time: "12:48:41", level: "DONE", message: "Model registry updated — 65,432 entries committed" },
];

const STREAM_MESSAGES: Array<{ level: LogLevel; message: string }> = [
  { level: "INFO",  message: "Processing batch 655..." },
  { level: "OK",    message: "Batch 655 completed in 402ms" },
  { level: "CACHE", message: "Cache TTL extended — edge nodes synced (3 regions)" },
  { level: "INFO",  message: "Processing batch 656..." },
  { level: "WARN",  message: "Latency spike detected — P99 > 820ms" },
  { level: "OK",    message: "Batch 656 completed in 531ms" },
  { level: "INFO",  message: "Processing batch 657..." },
  { level: "OK",    message: "Batch 657 completed in 377ms" },
  { level: "DONE",  message: "Checkpoint saved — offset 65,792" },
  { level: "INFO",  message: "Processing batch 658..." },
];

const LEVEL_STYLES: Record<LogLevel, { label: string; text: string; bg: string }> = {
  INFO:  { label: "INFO ", text: "text-blue-400",    bg: "bg-blue-500/10" },
  CACHE: { label: "CACHE", text: "text-cyan-400",    bg: "bg-cyan-500/10" },
  OK:    { label: "OK   ", text: "text-green-400",   bg: "bg-green-500/10" },
  WARN:  { label: "WARN ", text: "text-amber-400",   bg: "bg-amber-500/10" },
  DONE:  { label: "DONE ", text: "text-emerald-400", bg: "bg-emerald-500/10" },
  ERROR: { label: "ERROR", text: "text-red-400",     bg: "bg-red-500/10" },
};

function getCurrentTime() {
  return new Date().toTimeString().slice(0, 8);
}

export default function App() {
  const [isPaused, setIsPaused] = useState(true);
  const [cloudflareDebug, setCloudflareDebug] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [processed, setProcessed] = useState(0);
  const [total, setTotal] = useState(100000);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.naelvi.com";

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/admin/sync/status`);
        if (res.ok) {
          const data = await res.json();
          setIsPaused(!data.is_running);
          if (data.logs) setLogs(data.logs);
          if (data.progress !== undefined) setProgress(data.progress);
          if (data.processed !== undefined) setProcessed(data.processed);
          if (data.total !== undefined) setTotal(data.total);
        }
      } catch (e) {
        console.error("Status fetch error", e);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  const handleToggleSync = async () => {
    if (isPaused) {
      try {
        await fetch(`${API_URL}/api/admin/sync/start`, { method: "POST" });
        setIsPaused(false);
      } catch (e) {
        console.error("Start sync error", e);
      }
    } else {
        alert("Pause is not implemented in the backend yet. You can cancel the process manually.");
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

        @keyframes shimmer {
          0%   { transform: translateX(-180%); }
          100% { transform: translateX(300%); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.2; }
        }
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .shimmer-bar { animation: shimmer 2.6s ease-in-out infinite; }
        .live-dot    { animation: blink 1.4s ease-in-out infinite; }
        .log-entry   { animation: fadeSlideIn 0.22s ease-out both; }

        .logs-pane {
          scrollbar-width: thin;
          scrollbar-color: rgba(255,255,255,0.08) transparent;
        }
        .logs-pane::-webkit-scrollbar       { width: 4px; }
        .logs-pane::-webkit-scrollbar-track { background: transparent; }
        .logs-pane::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.08);
          border-radius: 2px;
        }
        .logs-pane::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.16); }

        .btn:focus-visible,
        .toggle-track:focus-visible { outline: 2px solid rgba(59,130,246,0.7); outline-offset: 3px; border-radius: 6px; }
      `}</style>

      <div
        className="min-h-screen bg-[#09090B] text-[#FAFAFA]"
        style={{ fontFamily: "'Inter', system-ui, sans-serif" }}
      >
        <div className="max-w-[1200px] mx-auto px-8 py-14 space-y-5">

          {/* ── Page header ─────────────────────────────────────────────── */}
          <div className="mb-10">
            <nav className="flex items-center gap-1.5 mb-3">
              <span
                className="text-[11px] text-[#52525B] tracking-[0.1em] uppercase"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                AI Model Platform
              </span>
              <ChevronRight size={12} className="text-[#3F3F46]" />
              <span
                className="text-[11px] text-[#52525B] tracking-[0.1em] uppercase"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                Management
              </span>
            </nav>
            <h1 className="text-[22px] font-semibold tracking-[-0.02em] text-white">
              Data Sync &amp; Management
            </h1>
          </div>

          {/* ── Section 1: Mass Sync ─────────────────────────────────────── */}
          <MassSyncCard isPaused={isPaused} handleToggleSync={handleToggleSync} progress={progress} processed={processed} total={total} />

          {/* ── Section 2: System Logs ───────────────────────────────────── */}
          <SystemLogsCard
            logs={logs}
            logsEndRef={logsEndRef}
            cloudflareDebug={cloudflareDebug}
            setCloudflareDebug={setCloudflareDebug}
            isPaused={isPaused}
          />

        </div>
      </div>
    </>
  );
}

/* ════════════════════════════════════════════════════════════════════
   Mass Sync Card
   ════════════════════════════════════════════════════════════════════ */
function MassSyncCard({
  isPaused,
  handleToggleSync,
  progress,
  processed,
  total
}: {
  isPaused: boolean;
  handleToggleSync: () => void;
  progress: number;
  processed: number;
  total: number;
}) {
  const PROGRESS = progress;
  const PROCESSED = processed.toLocaleString();
  const TOTAL = total.toLocaleString();

  return (
    <div
      className="rounded-[20px] border border-white/[0.07] overflow-hidden"
      style={{
        background: "rgba(15,15,17,0.95)",
        backdropFilter: "blur(12px)",
        boxShadow: "0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 32px rgba(0,0,0,0.5)",
      }}
    >
      {/* Card top bar */}
      <div
        className="px-8 pt-7 pb-6 border-b border-white/[0.06]"
        style={{ background: "rgba(255,255,255,0.015)" }}
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-[17px] font-semibold tracking-[-0.015em] text-white">
                Mass Sync
              </h2>
              <LiveBadge active={!isPaused} />
            </div>
            <p className="text-[13px] text-[#52525B]">
              Synchronizing model metadata across environments
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2.5">
            <button
              className="btn flex items-center gap-2 px-4 py-2 rounded-[10px] text-[13px] font-medium text-[#A1A1AA] border border-white/[0.08] transition-all duration-150"
              style={{ background: "rgba(255,255,255,0.04)" }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.07)";
                (e.currentTarget as HTMLElement).style.color = "#FAFAFA";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.04)";
                (e.currentTarget as HTMLElement).style.color = "#A1A1AA";
              }}
            >
              <X size={13} />
              Cancel
            </button>
            <button
              className="btn flex items-center gap-2 px-4 py-2 rounded-[10px] text-[13px] font-medium text-white transition-all duration-150"
              style={{
                background: isPaused
                  ? "linear-gradient(135deg, #22C55E 0%, #16A34A 100%)"
                  : "linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)",
                boxShadow: isPaused
                  ? "0 0 0 1px rgba(34,197,94,0.3), 0 2px 8px rgba(34,197,94,0.2)"
                  : "0 0 0 1px rgba(59,130,246,0.3), 0 2px 8px rgba(59,130,246,0.2)",
              }}
              onClick={handleToggleSync}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.filter = "brightness(1.08)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.filter = "brightness(1)";
              }}
            >
              {isPaused ? (
                <><RefreshCw size={13} /> Resume Sync</>
              ) : (
                <><Pause size={13} /> Pause Sync</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Progress area */}
      <div className="px-8 pt-7 pb-6 border-b border-white/[0.06]">
        {/* Progress header row */}
        <div className="flex items-center justify-between mb-3.5">
          <span className="text-[12px] font-medium text-[#52525B] tracking-[0.06em] uppercase"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            Sync Progress
          </span>
          <span
            className="text-[13px] font-medium"
            style={{ fontFamily: "'JetBrains Mono', monospace", color: "#3B82F6" }}
          >
            {PROGRESS}%
          </span>
        </div>

        {/* Track */}
        <div
          className="relative h-2 w-full rounded-full overflow-hidden"
          style={{ background: "rgba(255,255,255,0.06)" }}
        >
          {/* Fill */}
          <div
            className="absolute inset-y-0 left-0 rounded-full overflow-hidden transition-all duration-700"
            style={{
              width: `${PROGRESS}%`,
              background: "linear-gradient(90deg, #2563EB 0%, #3B82F6 60%, #60A5FA 100%)",
              boxShadow: "0 0 10px rgba(59,130,246,0.5), 0 0 20px rgba(59,130,246,0.15)",
            }}
          >
            {/* Shimmer */}
            {!isPaused && (
              <div
                className="shimmer-bar absolute inset-y-0 w-16 rounded-full"
                style={{
                  background:
                    "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.28) 50%, transparent 100%)",
                }}
              />
            )}
          </div>
        </div>

        {/* Tick labels */}
        <div className="flex justify-between mt-2">
          <span className="text-[11px] text-[#3F3F46]" style={{ fontFamily: "'JetBrains Mono', monospace" }}>0</span>
          <span className="text-[11px] text-[#3F3F46]" style={{ fontFamily: "'JetBrains Mono', monospace" }}>50K</span>
          <span className="text-[11px] text-[#3F3F46]" style={{ fontFamily: "'JetBrains Mono', monospace" }}>100K</span>
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-3 divide-x divide-white/[0.06] px-0">
        <MetricCell
          label="Processed"
          value={`${PROCESSED} / ${TOTAL}`}
          mono
        />
        <MetricCell
          label="ETA"
          value="~8 min remaining"
          mono
        />
        <MetricCell
          label="Speed"
          value="1,280 rec/min"
          mono
        />
      </div>
    </div>
  );
}

function MetricCell({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="px-8 py-5 group">
      <p className="text-[11px] text-[#52525B] tracking-[0.08em] uppercase mb-2"
        style={{ fontFamily: "'JetBrains Mono', monospace" }}>
        {label}
      </p>
      <p
        className="text-[14px] font-medium text-[#E4E4E7] group-hover:text-white transition-colors duration-150"
        style={mono ? { fontFamily: "'JetBrains Mono', monospace" } : undefined}
      >
        {value}
      </p>
    </div>
  );
}

function LiveBadge({ active }: { active: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium tracking-wide border"
      style={
        active
          ? {
              color: "#4ADE80",
              borderColor: "rgba(74,222,128,0.25)",
              background: "rgba(74,222,128,0.08)",
            }
          : {
              color: "#71717A",
              borderColor: "rgba(113,113,122,0.2)",
              background: "rgba(113,113,122,0.06)",
            }
      }
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{
          background: active ? "#4ADE80" : "#52525B",
          ...(active ? { animation: "blink 1.4s ease-in-out infinite" } : {}),
        }}
      />
      {active ? "Live Sync" : "Paused"}
    </span>
  );
}

/* ════════════════════════════════════════════════════════════════════
   System Logs Card
   ════════════════════════════════════════════════════════════════════ */
function SystemLogsCard({
  logs,
  logsEndRef,
  cloudflareDebug,
  setCloudflareDebug,
  isPaused,
}: {
  logs: LogEntry[];
  logsEndRef: React.RefObject<HTMLDivElement>;
  cloudflareDebug: boolean;
  setCloudflareDebug: (v: boolean) => void;
  isPaused: boolean;
}) {
  return (
    <div
      className="rounded-[20px] border border-white/[0.07] overflow-hidden"
      style={{
        background: "rgba(15,15,17,0.95)",
        backdropFilter: "blur(12px)",
        boxShadow: "0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 32px rgba(0,0,0,0.5)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-8 py-5 border-b border-white/[0.06]"
        style={{ background: "rgba(255,255,255,0.015)" }}
      >
        <div className="flex items-center gap-3">
          <h2 className="text-[15px] font-semibold tracking-[-0.01em] text-white">
            System Logs
          </h2>
          {/* Stream indicator */}
          <span
            className="inline-flex items-center gap-1.5 text-[11px] text-[#52525B]"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            {!isPaused ? (
              <>
                <span className="live-dot inline-block w-1.5 h-1.5 rounded-full bg-blue-400" />
                streaming
              </>
            ) : (
              <>
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#3F3F46]" />
                paused
              </>
            )}
          </span>
        </div>

        {/* Cloudflare debugging toggle */}
        <label className="flex items-center gap-3 cursor-pointer select-none group">
          <span className="text-[12px] text-[#52525B] group-hover:text-[#71717A] transition-colors duration-150">
            Enable Cloudflare Debugging
          </span>
          <button
            role="switch"
            aria-checked={cloudflareDebug}
            className="toggle-track relative inline-flex h-5 w-9 shrink-0 rounded-full border transition-all duration-200"
            style={{
              background: cloudflareDebug
                ? "linear-gradient(90deg, #2563EB, #3B82F6)"
                : "rgba(255,255,255,0.07)",
              borderColor: cloudflareDebug ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.1)",
              boxShadow: cloudflareDebug ? "0 0 8px rgba(59,130,246,0.3)" : "none",
            }}
            onClick={() => setCloudflareDebug(!cloudflareDebug)}
          >
            <span
              className="absolute top-[2px] h-[14px] w-[14px] rounded-full shadow-sm transition-transform duration-200"
              style={{
                background: "#FAFAFA",
                transform: cloudflareDebug ? "translateX(17px)" : "translateX(2px)",
              }}
            />
          </button>
        </label>
      </div>

      {/* Log pane */}
      <div
        className="logs-pane overflow-y-auto"
        style={{
          height: 360,
          background: "rgba(9,9,11,0.6)",
        }}
      >
        {/* Column headers */}
        <div
          className="sticky top-0 z-10 flex items-center gap-4 px-8 py-2 border-b border-white/[0.04]"
          style={{
            background: "rgba(15,15,17,0.95)",
            backdropFilter: "blur(8px)",
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          <span className="text-[10px] text-[#3F3F46] tracking-[0.1em] uppercase w-[70px]">Time</span>
          <span className="text-[10px] text-[#3F3F46] tracking-[0.1em] uppercase w-[46px]">Level</span>
          <span className="text-[10px] text-[#3F3F46] tracking-[0.1em] uppercase">Message</span>
        </div>

        <div className="px-8 py-3 space-y-[2px]">
          {logs.map((entry, i) => (
            <LogRow key={entry.id} entry={entry} isLast={i === logs.length - 1} />
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Footer */}
      <div
        className="flex items-center justify-between px-8 py-3.5 border-t border-white/[0.05]"
        style={{
          background: "rgba(255,255,255,0.01)",
          fontFamily: "'JetBrains Mono', monospace",
        }}
      >
        <span className="text-[11px] text-[#3F3F46]">
          {logs.length} entries — auto-scrolling
        </span>
        <span className="text-[11px] text-[#3F3F46]">
          {cloudflareDebug ? "CF debug: on" : "CF debug: off"}
        </span>
      </div>
    </div>
  );
}

function LogRow({ entry, isLast }: { entry: LogEntry; isLast: boolean }) {
  const style = LEVEL_STYLES[entry.level];

  return (
    <div
      className="log-entry flex items-start gap-4 px-3 py-[5px] rounded-[8px] group transition-colors duration-100 hover:bg-white/[0.03]"
      style={{ fontFamily: "'JetBrains Mono', monospace" }}
    >
      {/* Timestamp */}
      <span className="shrink-0 text-[12px] text-[#3F3F46] group-hover:text-[#52525B] transition-colors duration-100 w-[70px] tabular-nums">
        {entry.time}
      </span>

      {/* Level badge */}
      <span
        className={`shrink-0 text-[11px] font-medium px-1.5 py-[1px] rounded-[5px] w-[46px] text-center ${style.text} ${style.bg}`}
      >
        {entry.level}
      </span>

      {/* Message */}
      <span
        className={`text-[12px] leading-relaxed ${
          entry.level === "WARN" || entry.level === "ERROR"
            ? "text-[#D4D4D8]"
            : isLast
            ? "text-[#E4E4E7]"
            : "text-[#71717A] group-hover:text-[#A1A1AA]"
        } transition-colors duration-100`}
      >
        {entry.message}
      </span>

      {/* Cursor blink on last entry */}
      {isLast && (
        <span
          className="live-dot shrink-0 mt-[3px] w-1.5 h-[14px] rounded-sm"
          style={{ background: "rgba(59,130,246,0.6)" }}
        />
      )}
    </div>
  );
}
