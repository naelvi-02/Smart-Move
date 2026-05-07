'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  BarChart3,
  Cpu,
  Database,
  Globe,
  Zap,
  ArrowRight,
  Sparkles,
  Layers,
  Image as ImageIcon,
  DollarSign,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Download,
  RefreshCw,
  ExternalLink
} from 'lucide-react';
import { debugApi, modelsApi, ModelStats } from '@/lib/api';
import { cn } from '@/lib/utils'; // Make sure you have this utility or use clsx directly

// --- Components ---
const StatCard = ({ title, value, icon: Icon, color, delay }: any) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.5 }}
    className="glass-card p-6 rounded-2xl relative overflow-hidden group"
  >
    <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${color}`}>
      <Icon size={80} />
    </div>
    <div className="relative z-10">
      <div className={`p-3 rounded-lg w-fit mb-4 bg-white/5 group-hover:bg-white/10 transition-colors ${color}`}>
        <Icon size={24} className="text-white" />
      </div>
      <h3 className="text-3xl font-bold text-white mb-1 tracking-tight">{value}</h3>
      <p className="text-sm font-medium text-slate-400">{title}</p>
    </div>
  </motion.div>
);

const BentoCard = ({ children, className, delay }: any) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ delay, duration: 0.4 }}
    className={cn("glass-card rounded-2xl p-6 flex flex-col", className)}
  >
    {children}
  </motion.div>
);

type SyncState = 'idle' | 'syncing' | 'success' | 'error';
const DASHBOARD_SYNC_STORAGE_KEY = 'smart-move-dashboard-sync';

const SYNC_SOURCES = [
  { key: 'openrouter', label: 'OpenRouter', accent: 'text-indigo-400' },
  { key: 'civitai', label: 'Civitai', accent: 'text-pink-400' },
  { key: 'novita', label: 'Novita', accent: 'text-cyan-400' },
] as const;

export default function Dashboard() {
  const [stats, setStats] = useState<ModelStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<'idle' | 'checking' | 'available' | 'up_to_date' | 'installing' | 'error'>('idle');
  const [updateMessage, setUpdateMessage] = useState('');
  const [debugInfo, setDebugInfo] = useState({
    apiBaseUrl: debugApi.baseUrl(),
    health: 'pending',
    stats: 'pending',
  });
  const [syncStatus, setSyncStatus] = useState<Record<string, SyncState>>({
    openrouter: 'idle',
    civitai: 'idle',
    novita: 'idle',
  });
  const [syncDetails, setSyncDetails] = useState<Record<string, string>>({});
  const totalSources = SYNC_SOURCES.length;
  const finishedSources = SYNC_SOURCES.filter(source => {
    const status = syncStatus[source.key];
    return status === 'success' || status === 'error';
  }).length;
  const activeSourceIndex = SYNC_SOURCES.findIndex(source => syncStatus[source.key] === 'syncing');
  const overallProgress = syncing
    ? Math.min(100, ((finishedSources + (activeSourceIndex >= 0 ? 0.5 : 0)) / totalSources) * 100)
    : (finishedSources / totalSources) * 100;

  const persistSyncState = useCallback((nextSyncing: boolean, nextStatus: Record<string, SyncState>, nextDetails: Record<string, string>) => {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(DASHBOARD_SYNC_STORAGE_KEY, JSON.stringify({
      syncing: nextSyncing,
      syncStatus: nextStatus,
      syncDetails: nextDetails,
      updatedAt: Date.now(),
    }));
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const result = await debugApi.health();
      setDebugInfo(prev => ({ ...prev, health: result.status }));
    } catch (error) {
      setDebugInfo(prev => ({
        ...prev,
        health: error instanceof Error ? error.message : 'failed',
      }));
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const data = await modelsApi.getStats();
      setStats(data);
      setDebugInfo(prev => ({ ...prev, stats: 'ok' }));
    } catch (err) {
      console.error('Failed to load stats:', err);
      setDebugInfo(prev => ({
        ...prev,
        stats: err instanceof Error ? err.message : 'failed',
      }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const raw = window.localStorage.getItem(DASHBOARD_SYNC_STORAGE_KEY);
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as {
            syncing?: boolean;
            syncStatus?: Record<string, SyncState>;
            syncDetails?: Record<string, string>;
            updatedAt?: number;
          };

          if (parsed.syncStatus) {
            setSyncStatus(parsed.syncStatus);
          }

          if (parsed.syncDetails) {
            setSyncDetails(parsed.syncDetails);
          }

          if (parsed.syncing && parsed.updatedAt && Date.now() - parsed.updatedAt < 15 * 60 * 1000) {
            setSyncing(true);
          }
        } catch {
        }
      }
    }

    checkHealth();
    loadStats();
  }, [checkHealth, loadStats]);

  const checkForDesktopUpdate = async () => {
    setCheckingUpdate(true);
    setUpdateStatus('checking');
    setUpdateMessage('Checking GitHub Releases...');

    try {
      if (typeof window === 'undefined' || !(window as Window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__) {
        setUpdateStatus('error');
        setUpdateMessage('Desktop updater is only available inside the Tauri app.');
        return;
      }

      const [{ check }, { relaunch }] = await Promise.all([
        import('@tauri-apps/plugin-updater'),
        import('@tauri-apps/plugin-process'),
      ]);

      const update = await check();

      if (!update) {
        setUpdateStatus('up_to_date');
        setUpdateMessage('You are already on the latest version.');
        return;
      }

      setUpdateStatus('available');
      setUpdateMessage(`Found v${update.version}. Downloading update...`);

      await update.downloadAndInstall(event => {
        if (event.event === 'Started') {
          setUpdateMessage(`Downloading ${event.data.contentLength} bytes...`);
        }

        if (event.event === 'Progress') {
          setUpdateMessage(`Downloaded ${event.data.chunkLength} bytes...`);
        }
      });

      setUpdateStatus('installing');
      setUpdateMessage('Update installed. Restarting app...');
      await relaunch();
    } catch (error) {
      console.error('Update check failed:', error);
      setUpdateStatus('error');
      setUpdateMessage('Auto-update is not ready yet. Open Releases to install manually.');
    } finally {
      setCheckingUpdate(false);
    }
  };

  const syncAll = async () => {
    let currentStatus = { openrouter: 'idle', civitai: 'idle', novita: 'idle' } as Record<string, SyncState>;
    let currentDetails = {} as Record<string, string>;

    try {
      setSyncing(true);
      setSyncStatus(currentStatus);
      setSyncDetails(currentDetails);
      persistSyncState(true, currentStatus, currentDetails);

      const steps = [
        { key: 'openrouter', label: 'OpenRouter', run: modelsApi.syncOpenRouter },
        { key: 'civitai', label: 'Civitai', run: modelsApi.syncCivitai },
        { key: 'novita', label: 'Novita', run: modelsApi.syncNovita },
      ] as const;

      for (const step of steps) {
        currentStatus = { ...currentStatus, [step.key]: 'syncing' };
        setSyncStatus(currentStatus);
        persistSyncState(true, currentStatus, currentDetails);

        try {
          const result = await step.run();
          currentStatus = { ...currentStatus, [step.key]: 'success' };
          currentDetails = {
            ...currentDetails,
            [step.key]: `${result.models_synced} new, ${result.models_updated} updated`,
          };
          setSyncStatus(currentStatus);
          setSyncDetails(currentDetails);
          persistSyncState(true, currentStatus, currentDetails);

          if (step.key === 'openrouter') {
            try {
              const scoreResult = await modelsApi.syncNsfwScores();
              setDebugInfo(prev => ({
                ...prev,
                stats: `ok · scores updated ${scoreResult.updated}`,
              }));
            } catch (error) {
              console.error('Failed to sync NSFW scores:', error);
            }
          }
        } catch (error) {
          currentStatus = { ...currentStatus, [step.key]: 'error' };
          currentDetails = {
            ...currentDetails,
            [step.key]: error instanceof Error ? error.message : 'Sync failed',
          };
          setSyncStatus(currentStatus);
          setSyncDetails(currentDetails);
          persistSyncState(true, currentStatus, currentDetails);
          console.error(`Failed to sync ${step.label}:`, error);
        }
      }

      await loadStats();
    } catch (err) {
      console.error('Failed to sync:', err);
    } finally {
      setSyncing(false);
      persistSyncState(false, currentStatus, currentDetails);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold text-indigo-400 uppercase tracking-widest">
              Research Interface
            </span>
          </div>
          <h1 className="text-4xl font-bold text-white mb-2 tracking-tight">
            Research <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">Hub</span>
          </h1>
          <p className="text-slate-400 max-w-md">
            Advanced analytics and intelligence for Large Language Models and Generative AI assets.
          </p>
        </motion.div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={syncAll}
          disabled={syncing}
          className="px-5 py-3 rounded-xl bg-white text-black font-semibold flex items-center gap-2 shadow-[0_0_20px_rgba(255,255,255,0.2)] hover:shadow-[0_0_30px_rgba(255,255,255,0.3)] transition-all disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {syncing ? <Sparkles className="animate-spin w-4 h-4" /> : <Database className="w-4 h-4" />}
          {syncing ? 'Syncing...' : 'Sync Database'}
        </motion.button>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mb-6 glass-card rounded-2xl p-4 border border-white/5"
      >
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <p className="text-sm font-semibold text-white">Sync Progress</p>
            <p className="text-xs text-slate-500">Each source updates independently, so you can see which platform is still running.</p>
          </div>
          <span className="text-xs px-2 py-1 rounded-full bg-white/5 border border-white/10 text-slate-300">
            {syncing ? 'Sync in progress' : 'Idle'}
          </span>
        </div>

        <div className="mb-4">
          <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
            <span>Overall sync progress</span>
            <span>{finishedSources}/{totalSources} sources completed</span>
          </div>
          <div className="h-2 rounded-full bg-white/5 overflow-hidden border border-white/5">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${overallProgress}%` }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-violet-500 to-cyan-500"
            />
          </div>
        </div>

        <div className="mb-4 rounded-xl bg-black/20 border border-white/5 px-4 py-3 text-xs text-slate-400 space-y-1">
          <p><span className="text-slate-500">API:</span> {debugInfo.apiBaseUrl}</p>
          <p><span className="text-slate-500">Health:</span> {debugInfo.health}</p>
          <p><span className="text-slate-500">Stats:</span> {debugInfo.stats}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {SYNC_SOURCES.map(source => {
            const status = syncStatus[source.key];
            const detail = syncDetails[source.key];
            const sourceProgress = status === 'syncing' ? 60 : status === 'success' || status === 'error' ? 100 : 0;

            const icon = status === 'syncing'
              ? <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
              : status === 'success'
                ? <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                : status === 'error'
                  ? <AlertCircle className="w-4 h-4 text-rose-400" />
                  : <Database className="w-4 h-4 text-slate-500" />;

            const statusLabel = status === 'syncing'
              ? 'Syncing...'
              : status === 'success'
                ? 'Done'
                : status === 'error'
                  ? 'Error'
                  : 'Waiting';

            return (
              <div key={source.key} className="rounded-xl bg-white/5 border border-white/5 px-4 py-3">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-2 rounded-lg bg-black/20 ${source.accent}`}>
                      {icon}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white truncate">{source.label}</p>
                      <p className="text-xs text-slate-500 truncate">{detail || 'Not started'}</p>
                    </div>
                  </div>
                  <span className={`text-[11px] px-2 py-1 rounded-full border whitespace-nowrap ${
                    status === 'syncing'
                      ? 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                      : status === 'success'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                        : status === 'error'
                          ? 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                          : 'bg-white/5 border-white/10 text-slate-400'
                  }`}>
                    {statusLabel}
                  </span>
                </div>

                <div className="h-2 rounded-full bg-black/20 overflow-hidden border border-white/5">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${sourceProgress}%` }}
                    transition={{ duration: 0.35, ease: 'easeOut' }}
                    className={`h-full rounded-full ${
                      status === 'syncing'
                        ? 'bg-gradient-to-r from-amber-400 to-orange-400'
                        : status === 'success'
                          ? 'bg-gradient-to-r from-emerald-400 to-cyan-400'
                          : status === 'error'
                            ? 'bg-gradient-to-r from-rose-400 to-red-400'
                            : 'bg-slate-500'
                    }`}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mb-6 glass-card rounded-2xl p-4 border border-white/5 flex items-center justify-between gap-4"
      >
        <div>
          <p className="text-sm font-semibold text-white">App Updates</p>
          <p className="text-xs text-slate-500">Check, download, and install the latest desktop update from GitHub Releases.</p>
          <p className="text-xs text-slate-400 mt-1">{updateMessage || 'Ready to check for updates.'}</p>
          <p className="text-[11px] uppercase tracking-widest text-slate-500 mt-2">Status: {updateStatus}</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={checkForDesktopUpdate}
            disabled={checkingUpdate}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm font-medium border border-white/5 hover:border-white/10 transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {checkingUpdate ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {checkingUpdate ? 'Checking...' : 'Check Updates'}
          </button>
          <a
            href="https://github.com/naelvi-02/Smart-Move/releases"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm font-medium border border-white/5 hover:border-white/10 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            Releases
          </a>
        </div>
      </motion.div>

      {loading ? (
        // Skeleton Loader
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 animate-pulse">
          {[1, 2, 3, 4].map(i => <div key={i} className="h-40 bg-white/5 rounded-2xl" />)}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Top Stats Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Total Models"
              value={stats?.total_models || 0}
              icon={Database}
              color="text-indigo-400"
              delay={0.1}
            />
            <StatCard
              title="LLM Models"
              value={stats?.by_type?.llm || 0}
              icon={Cpu}
              color="text-violet-400"
              delay={0.2}
            />
            <StatCard
              title="Image Generator"
              value={stats?.by_type?.image || 0}
              icon={ImageIcon}
              color="text-pink-400"
              delay={0.3}
            />
            <StatCard
              title="Active Sources"
              value={(stats?.by_source?.openrouter || 0) + (stats?.by_source?.civitai || 0) + (stats?.by_source?.novita || 0)}
              icon={Globe}
              color="text-emerald-400"
              delay={0.4}
            />
          </div>

          {/* Main Bento Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-auto md:h-[500px]">
            {/* Source Distribution - Large Card */}
            <BentoCard className="md:col-span-2 relative overflow-hidden" delay={0.5}>
              <div className="absolute top-0 right-0 p-10 opacity-5 pointer-events-none">
                <Globe size={300} />
              </div>
              <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                <Layers className="text-indigo-400" /> Model Distribution
              </h3>

              <div className="grid gap-6">
                {[
                  { label: 'OpenRouter', count: stats?.by_source?.openrouter || 0, color: 'bg-indigo-500' },
                  { label: 'Civitai', count: stats?.by_source?.civitai || 0, color: 'bg-pink-500' },
                  { label: 'Novita', count: stats?.by_source?.novita || 0, color: 'bg-cyan-500' },
                ].map((item, idx) => {
                  const percentage = stats?.total_models ? (item.count / stats.total_models) * 100 : 0;
                  return (
                    <div key={item.label} className="space-y-2">
                      <div className="flex justify-between text-sm font-medium">
                        <span className="text-slate-300">{item.label}</span>
                        <span className="text-white">{item.count} <span className="text-slate-500 text-xs">models</span></span>
                      </div>
                      <div className="h-4 bg-white/5 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${percentage}%` }}
                          transition={{ duration: 1, delay: 0.8 + (idx * 0.1) }}
                          className={`h-full ${item.color} shadow-[0_0_15px_currentColor]`}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>

              <div className="mt-auto pt-6 flex gap-4">
                <Link href="/llm-explorer" className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm font-medium transition-colors border border-white/5 hover:border-white/10">Browse LLMs</Link>
                <Link href="/image-explorer" className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm font-medium transition-colors border border-white/5 hover:border-white/10">Browse Images</Link>
              </div>
            </BentoCard>

            {/* Tier Stats & Quick Actions */}
            <div className="grid grid-rows-2 gap-6">
              <BentoCard delay={0.6}>
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Zap className="text-amber-400" size={18} /> Tier Breakdown
                </h3>
                <div className="flex justify-between items-end h-full px-2 gap-2">
                  {[
                    { label: 'FREE', count: stats?.by_tier?.free, height: '40%', color: 'bg-emerald-500' },
                    { label: 'PRO', count: stats?.by_tier?.pro, height: '60%', color: 'bg-violet-500' },
                    { label: 'ADMIN', count: stats?.by_tier?.admin, height: '80%', color: 'bg-amber-500' },
                  ].map((bar, idx) => (
                    <div key={bar.label} className="flex flex-col items-center gap-2 w-full">
                      <span className="text-xs font-bold text-white mb-1">{bar.count || 0}</span>
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: bar.height }}
                        className={`w-full rounded-t-lg opacity-80 ${bar.color}`}
                        transition={{ delay: 1 + (idx * 0.1) }}
                      />
                      <span className="text-[10px] font-bold text-slate-500 tracking-wider">{bar.label}</span>
                    </div>
                  ))}
                </div>
              </BentoCard>

              <BentoCard delay={0.7} className="justify-center">
                <h3 className="text-lg font-semibold text-white mb-4">Quick Shortcuts</h3>
                <div className="grid grid-cols-2 gap-3">
                  <Link href="/benchmarks" className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors group">
                    <BarChart3 className="text-emerald-400 mb-2 group-hover:scale-110 transition-transform" />
                    <p className="text-xs font-medium text-emerald-300">Benchmarks</p>
                  </Link>
                  <Link href="/cost-simulator" className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 transition-colors group">
                    <DollarSign className="text-amber-400 mb-2 group-hover:scale-110 transition-transform" />
                    <p className="text-xs font-medium text-amber-300">Cost Sim</p>
                  </Link>
                </div>
              </BentoCard>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
