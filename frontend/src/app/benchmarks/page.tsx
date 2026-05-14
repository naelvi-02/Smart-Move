'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Play,
    RotateCw,
    CheckCircle2,
    AlertTriangle,
    XCircle,
    ListChecks,
    Zap,
    Clock,
    Terminal,
    Flame,
    Code,
    Sparkles,
    TrendingUp,
    AlertCircle
} from 'lucide-react';
import { benchmarksApi, modelsApi, Model, BenchmarkJobStatus, BenchmarkResult } from '@/lib/api';
import { cn } from '@/lib/utils';

type PriorityFilter = 'all' | 'nsfw' | 'coding' | 'popular' | 'unscored';
const MAX_BENCHMARK_MODELS = 10;
const DEFAULT_BENCHMARK_COUNT = 6;
const EST_TOKENS_PER_BENCHMARK = 1800;

const NSFW_KEYWORDS = ['dolphin', 'cydonia', 'venice', 'grok', 'abliterated', 'uncensor', 'nsfw', 'mistral-nemo'];
const CODING_KEYWORDS = ['code', 'coder', 'codestral', 'deepseek', 'qwen2.5-coder', 'starcoder', 'wizard', 'magicoder'];
const MODEL_SKELETON_KEYS = ['model-skeleton-1', 'model-skeleton-2', 'model-skeleton-3', 'model-skeleton-4', 'model-skeleton-5'];
const BENCHMARK_JOB_STORAGE_KEY = 'smart-move-benchmark-job';

const ResultCard = ({ result, delay }: any) => {
    const getStatusConfig = (status: string) => {
        switch (status) {
            case 'success': return { color: 'emerald', icon: CheckCircle2, bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' };
            case 'partial': return { color: 'amber', icon: AlertTriangle, bg: 'bg-amber-500/10', border: 'border-amber-500/20' };
            case 'refusal': return { color: 'rose', icon: XCircle, bg: 'bg-rose-500/10', border: 'border-rose-500/20' };
            default: return { color: 'slate', icon: Clock, bg: 'bg-slate-500/10', border: 'border-slate-500/20' };
        }
    };

    const config = getStatusConfig(result.status);
    const Icon = config.icon;

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay }}
            className={cn(
                "p-4 rounded-xl border mb-3 flex items-start gap-4 transition-all hover:bg-white/[0.02]",
                config.bg, config.border
            )}
        >
            <div className={cn("mt-1 p-1 rounded-full", `text-${config.color}-500`)}>
                <Icon size={20} />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start mb-1">
                    <h4 className="font-semibold text-white truncate">{result.model_id}</h4>
                    <span className={cn("text-xs font-mono font-bold px-2 py-0.5 rounded", `bg-${config.color}-500/20 text-${config.color}-400`)}>
                        {result.score ? `${(result.score * 100).toFixed(0)}%` : '-'}
                    </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-400 mb-2">
                    <span className="flex items-center gap-1">
                        <Terminal size={12} /> {result.benchmark_type}
                    </span>
                    <span className="flex items-center gap-1">
                        <Clock size={12} /> {result.latency_ms?.toFixed(0)}ms
                    </span>
                </div>
                {result.notes && (
                    <p className="text-xs text-slate-500 italic border-l-2 border-slate-700 pl-2">
                        {result.notes}
                    </p>
                )}
            </div>
        </motion.div>
    );
};

export default function Benchmarks() {
    const [models, setModels] = useState<Model[]>([]);
    const [results, setResults] = useState<BenchmarkResult[]>([]);
    const [selectedModels, setSelectedModels] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [running, setRunning] = useState(false);
    const [updatingScores, setUpdatingScores] = useState(false);
    const [activeJob, setActiveJob] = useState<BenchmarkJobStatus | null>(null);
    const [benchmarkTypes, setBenchmarkTypes] = useState<Array<{ id: string; type: string; language: string; description: string }>>([]);
    const [priorityFilter, setPriorityFilter] = useState<PriorityFilter>('all');
    const [search, setSearch] = useState('');

    const persistBenchmarkJob = useCallback((job: BenchmarkJobStatus | null, isRunning: boolean) => {
        if (typeof window === 'undefined') return;

        if (!job) {
            window.localStorage.removeItem(BENCHMARK_JOB_STORAGE_KEY);
            return;
        }

        window.localStorage.setItem(BENCHMARK_JOB_STORAGE_KEY, JSON.stringify({
            job,
            running: isRunning,
            savedAt: Date.now(),
        }));
    }, []);

    const loadData = useCallback(async (mode: 'initial' | 'refresh' = 'refresh') => {
        try {
            if (mode === 'initial') {
                setLoading(true);
            } else {
                setRefreshing(true);
            }
            const [modelsData, resultsData, typesData] = await Promise.all([
                modelsApi.listLlm({ limit: '500' }),
                benchmarksApi.list({ limit: '100' }),
                benchmarksApi.getTypes(),
            ]);
            setModels(modelsData);
            setResults(resultsData);
            setBenchmarkTypes(typesData);
        } catch (err) {
            console.error('Failed to load data:', err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadData('initial');
    }, [loadData]);

    useEffect(() => {
        if (typeof window === 'undefined') return;

        try {
            const raw = window.localStorage.getItem(BENCHMARK_JOB_STORAGE_KEY);
            if (!raw) return;

            const parsed = JSON.parse(raw) as { job?: BenchmarkJobStatus; running?: boolean; savedAt?: number };
            if (!parsed.job) return;

            const isRecent = typeof parsed.savedAt === 'number' && Date.now() - parsed.savedAt < 1000 * 60 * 60;
            if (!isRecent) {
                window.localStorage.removeItem(BENCHMARK_JOB_STORAGE_KEY);
                return;
            }

            setActiveJob(parsed.job);
            setRunning(Boolean(parsed.running) && !['completed', 'completed_with_errors', 'failed'].includes(parsed.job.status));
        } catch {
            window.localStorage.removeItem(BENCHMARK_JOB_STORAGE_KEY);
        }
    }, []);

    // Smart filtering based on priority
    const filteredModels = useMemo(() => {
        const benchmarkedIds = new Set(results.map(r => r.model_id));

        return models.filter(model => {
            const idLower = (model.model_id || '').toLowerCase();
            const nameLower = (model.name || '').toLowerCase();
            const combined = idLower + ' ' + nameLower;

            if (search) {
                const searchTerm = search.toLowerCase();
                if (!combined.includes(searchTerm) && !(model.provider || '').toLowerCase().includes(searchTerm)) {
                    return false;
                }
            }

            switch (priorityFilter) {
                case 'nsfw':
                    // NSFW/Unfiltered models (Dolphin, Cydonia, Venice, Grok, etc.)
                    return NSFW_KEYWORDS.some(kw => combined.includes(kw)) || model.is_moderated === false || (model.nsfw_score || 0) >= 40;
                case 'coding':
                    // Coding-focused models
                    return CODING_KEYWORDS.some(kw => combined.includes(kw));
                case 'popular':
                    // Popular providers and well-known models
                    return ['anthropic', 'openai', 'google', 'meta', 'mistral'].some(p =>
                        (model.provider || '').toLowerCase().includes(p)
                    );
                case 'unscored':
                    // Models without benchmark data yet
                    return !benchmarkedIds.has(model.model_id) && !model.final_score;
                default:
                    return true;
            }
        });
    }, [models, results, priorityFilter, search]);

    const toggleModel = (modelId: string) => {
        setSelectedModels(prev =>
            prev.includes(modelId)
                ? prev.filter(id => id !== modelId)
                : prev.length >= MAX_BENCHMARK_MODELS
                    ? prev
                    : [...prev, modelId]
        );
    };

    const selectAll = () => {
        setSelectedModels(filteredModels.slice(0, MAX_BENCHMARK_MODELS).map(m => m.model_id));
    };

    const selectedModelObjects = useMemo(
        () => models.filter(model => selectedModels.includes(model.model_id)),
        [models, selectedModels]
    );

    const estimatedProbeCost = useMemo(() => {
        return selectedModelObjects.reduce((total, model) => {
            const unitPrice = model.effective_price_1m || 0;
            return total + ((unitPrice * EST_TOKENS_PER_BENCHMARK * DEFAULT_BENCHMARK_COUNT) / 1_000_000);
        }, 0);
    }, [selectedModelObjects]);

    const benchmarkProgress = activeJob && activeJob.total_benchmarks > 0
        ? Math.min(100, (activeJob.completed_benchmarks / activeJob.total_benchmarks) * 100)
        : 0;

    const runBenchmarks = async () => {
        if (selectedModels.length === 0) return;
        try {
            setRunning(true);
            const job = await benchmarksApi.run(selectedModels);
            const nextJob = {
                job_id: job.job_id,
                status: job.status,
                model_ids: job.models,
                benchmark_types: job.benchmark_types,
                current_model: null,
                current_benchmark: null,
                completed_models: 0,
                total_models: job.models.length,
                completed_benchmarks: 0,
                total_benchmarks: job.models.length * job.benchmark_types.length,
                last_error: null,
                updated_at: new Date().toISOString(),
            };
            setActiveJob(nextJob);
            persistBenchmarkJob(nextJob, true);
        } catch (err) {
            console.error('Failed to run benchmarks:', err);
            setRunning(false);
        }
    };

    useEffect(() => {
        if (!activeJob?.job_id || !running) return;

        const interval = window.setInterval(async () => {
            try {
                const job = await benchmarksApi.getJob(activeJob.job_id);
                setActiveJob(job);
                const stillRunning = !['completed', 'completed_with_errors', 'failed'].includes(job.status);
                persistBenchmarkJob(job, stillRunning);
                await loadData('refresh');
                if (!stillRunning) {
                    setRunning(false);
                }
            } catch (error) {
                console.error('Failed to poll benchmark job:', error);
                setRunning(false);
            }
        }, 5000);

        return () => window.clearInterval(interval);
    }, [activeJob?.job_id, running, loadData, persistBenchmarkJob]);

    const updateScores = async () => {
        try {
            setUpdatingScores(true);
            await benchmarksApi.updateScores();
            await loadData('refresh');
        } catch (err) {
            console.error('Failed to update scores:', err);
        } finally {
            setUpdatingScores(false);
        }
    };

    const priorityTabs = [
        { value: 'nsfw', label: 'NSFW Priority', icon: Flame, color: 'text-rose-400', description: 'Dolphin, Cydonia, Venice, Grok...' },
        { value: 'coding', label: 'Coding', icon: Code, color: 'text-emerald-400', description: 'DeepSeek, Codestral, Qwen Coder...' },
        { value: 'popular', label: 'Popular', icon: TrendingUp, color: 'text-blue-400', description: 'OpenAI, Anthropic, Google...' },
        { value: 'unscored', label: 'Unscored', icon: AlertCircle, color: 'text-amber-400', description: 'Need benchmark data' },
        { value: 'all', label: 'All Models', icon: Sparkles, color: 'text-slate-400', description: 'Show everything' },
    ];

    return (
        <div className="min-h-screen pb-20">
            <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                    <h1 className="text-3xl font-bold text-white mb-2">Benchmarks</h1>
                    <p className="text-slate-400">Run safe evaluation probes on selected models.</p>
                </motion.div>

                <div className="flex gap-3">
                    <button
                        type="button"
                        onClick={updateScores}
                        disabled={updatingScores}
                        className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 font-medium text-sm flex items-center gap-2 border border-white/5 transition-all"
                    >
                        {updatingScores ? <RotateCw className="animate-spin" size={16} /> : <RotateCw size={16} />} Update Scores
                    </button>
                    <button
                        type="button"
                        onClick={runBenchmarks}
                        disabled={selectedModels.length === 0 || running}
                        className="px-6 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-sm flex items-center gap-2 shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {running ? <RotateCw className="animate-spin" size={16} /> : <Play size={16} fill="currentColor" />}
                        Run Probe ({selectedModels.length})
                    </button>
                </div>
            </div>

            <div className="mb-6 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-xs text-amber-200 flex flex-wrap items-center justify-between gap-3">
                <span>Select up to {MAX_BENCHMARK_MODELS} models per run. `Run Probe` sends real OpenRouter requests and uses credit.</span>
                <span className="font-mono">Est. cost: ${estimatedProbeCost.toFixed(4)} / run</span>
            </div>

            {activeJob && (
                <div className="mb-6 rounded-xl border border-indigo-500/20 bg-indigo-500/10 px-4 py-3 text-xs text-indigo-200 flex flex-wrap items-center justify-between gap-3">
                    <span>
                        Job {activeJob.status}: {activeJob.completed_models}/{activeJob.total_models} models, {activeJob.completed_benchmarks}/{activeJob.total_benchmarks} probes.
                        {activeJob.current_model ? ` Running ${activeJob.current_model}` : ''}
                        {activeJob.current_benchmark ? ` / ${activeJob.current_benchmark}` : ''}
                    </span>
                    {activeJob.last_error && <span className="text-rose-300">Last error: {activeJob.last_error}</span>}
                    <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                        <div className="h-full bg-indigo-400 transition-all" style={{ width: `${benchmarkProgress}%` }} />
                    </div>
                </div>
            )}

            {refreshing && !loading && (
                <div className="mb-6 rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-3 text-xs text-cyan-200">
                    Refreshing benchmark data...
                </div>
            )}

            {/* Priority Filter Tabs */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 flex flex-wrap gap-2"
            >
                {priorityTabs.map(({ value, label, icon: Icon, color, description }) => (
                    <button
                        type="button"
                        key={value}
                        onClick={() => setPriorityFilter(value as PriorityFilter)}
                        className={cn(
                            "px-4 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-all border group",
                            priorityFilter === value
                                ? "bg-white/10 border-white/20 text-white shadow-lg"
                                : "bg-white/5 border-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
                        )}
                    >
                        <Icon size={16} className={priorityFilter === value ? color : ''} />
                        <div className="text-left">
                            <div>{label}</div>
                            {priorityFilter === value && (
                                <div className="text-[10px] text-slate-500 font-normal">{description}</div>
                            )}
                        </div>
                    </button>
                ))}
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left Column: Config */}
                <div className="space-y-6">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="glass-panel p-6 rounded-2xl"
                    >
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <ListChecks className="text-indigo-400" size={20} /> Target Models
                            </h3>
                            <span className="text-xs text-slate-500 font-mono">{filteredModels.length} found</span>
                        </div>

                        <div className="mb-4">
                            <input
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search benchmark models..."
                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                            />
                        </div>

                        {/* Quick Actions */}
                        <div className="flex gap-2 mb-4">
                            <button
                                type="button"
                                onClick={selectAll}
                                className="flex-1 py-2 text-xs bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 rounded-lg border border-indigo-500/20 transition-colors"
                            >
                                Select All ({filteredModels.length})
                            </button>
                            {selectedModels.length > 0 && (
                                <button
                                    type="button"
                                    onClick={() => setSelectedModels([])}
                                    className="flex-1 py-2 text-xs bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 rounded-lg border border-rose-500/20 transition-colors"
                                >
                                    Clear ({selectedModels.length})
                                </button>
                            )}
                        </div>

                        <div className="h-[350px] overflow-y-auto pr-2 space-y-1 custom-scrollbar">
                            {loading ? (
                                MODEL_SKELETON_KEYS.map((key) => <div key={key} className="h-10 bg-white/5 rounded-lg animate-pulse" />)
                            ) : filteredModels.length === 0 ? (
                                <div className="text-center py-10 text-slate-500 space-y-3">
                                    <p>No models match this filter.</p>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setPriorityFilter('all');
                                            setSearch('');
                                        }}
                                        className="px-3 py-2 text-xs bg-white/5 hover:bg-white/10 text-slate-300 rounded-lg border border-white/10"
                                    >
                                        Reset benchmark filters
                                    </button>
                                </div>
                            ) : (
                                filteredModels.map((model) => {
                                    const idLower = (model.model_id || '').toLowerCase();
                                    const nameLower = (model.name || '').toLowerCase();
                                    const combined = idLower + ' ' + nameLower;
                                    const isNsfw = NSFW_KEYWORDS.some(kw => combined.includes(kw)) || !model.is_moderated;
                                    const isCoding = CODING_KEYWORDS.some(kw => combined.includes(kw));

                                    return (
                                        <label
                                            key={model.id}
                                            className={cn(
                                                "flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all border",
                                                selectedModels.includes(model.model_id)
                                                    ? "bg-indigo-500/10 border-indigo-500/30"
                                                    : "bg-transparent border-transparent hover:bg-white/5"
                                            )}
                                        >
                                            <div className="relative flex items-center justify-center w-5 h-5">
                                                <input
                                                    type="checkbox"
                                                    className="peer appearance-none w-5 h-5 rounded border border-slate-600 checked:bg-indigo-500 checked:border-indigo-500 transition-colors"
                                                    checked={selectedModels.includes(model.model_id)}
                                                    onChange={() => toggleModel(model.model_id)}
                                                />
                                                <CheckCircle2 size={12} className="absolute text-white opacity-0 peer-checked:opacity-100 pointer-events-none" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex justify-between items-center gap-2">
                                                    <p className={cn("text-sm font-medium break-words", selectedModels.includes(model.model_id) ? "text-white" : "text-slate-300")}>
                                                        {model.name || model.model_id}
                                                    </p>
                                                    <div className="flex gap-1 shrink-0">
                                                        {isNsfw && <Flame size={12} className="text-rose-400" aria-label="NSFW Capable" />}
                                                        {isCoding && <Code size={12} className="text-emerald-400" aria-label="Coding Model" />}
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <p className="text-[10px] text-slate-600 truncate">{model.provider}</p>
                                                    {model.final_score && <span className="text-[10px] bg-white/5 px-1.5 rounded text-slate-400">{model.final_score.toFixed(0)}</span>}
                                                </div>
                                            </div>
                                        </label>
                                    );
                                })
                            )}
                        </div>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="glass-panel p-6 rounded-2xl"
                    >
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <Zap className="text-amber-400" size={20} /> Probe Types
                        </h3>
                        <div className="space-y-3">
                            {benchmarkTypes.map(type => (
                                <div key={type.id} className="p-3 bg-white/5 rounded-lg border border-white/5">
                                    <div className="flex justify-between items-center mb-1">
                                        <span className="text-sm font-semibold text-white">{type.type}</span>
                                        <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400">{type.language}</span>
                                    </div>
                                    <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2">{type.description}</p>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                </div>

                {/* Right Column: Results */}
                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                    className="lg:col-span-2 glass-panel p-6 rounded-2xl flex flex-col h-[800px]"
                >
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-lg font-bold text-white flex items-center gap-2">
                            <Terminal className="text-emerald-400" size={20} /> Result Log
                        </h3>
                        <span className="text-xs text-slate-500 font-mono">Found {results.length} entries</span>
                    </div>

                    <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                        {results.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center text-slate-600 opacity-50">
                                <Terminal size={64} className="mb-4" />
                                <p>Awaiting probe data...</p>
                            </div>
                        ) : (
                            <AnimatePresence>
                                {results.map((result, i) => (
                                    <ResultCard key={result.id} result={result} delay={i * 0.05} />
                                ))}
                            </AnimatePresence>
                        )}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}
