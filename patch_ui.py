import re

file_path = "frontend/src/app/admin/page.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace App Component state and effects
new_app = """export default function App() {
  const [isPaused, setIsPaused] = useState(true);
  const [cloudflareDebug, setCloudflareDebug] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [processed, setProcessed] = useState(0);
  const [total, setTotal] = useState(100000);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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
  };"""

content = re.sub(
    r"export default function App\(\) \{.*?return \(",
    new_app + "\n\n  return (",
    content,
    flags=re.DOTALL
)

# Update MassSyncCard props
content = content.replace(
    "<MassSyncCard isPaused={isPaused} setIsPaused={setIsPaused} />",
    "<MassSyncCard isPaused={isPaused} handleToggleSync={handleToggleSync} progress={progress} processed={processed} total={total} />"
)

# Update MassSyncCard implementation
mass_sync_card_old = """function MassSyncCard({
  isPaused,
  setIsPaused,
}: {
  isPaused: boolean;
  setIsPaused: (v: boolean) => void;
}) {
  const PROGRESS = 65;
  const PROCESSED = "65,432";
  const TOTAL = "100,000";"""

mass_sync_card_new = """function MassSyncCard({
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
  const TOTAL = total.toLocaleString();"""

content = content.replace(mass_sync_card_old, mass_sync_card_new)

# Update the button onClick
content = content.replace(
    "onClick={() => setIsPaused(!isPaused)}",
    "onClick={handleToggleSync}"
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully")
