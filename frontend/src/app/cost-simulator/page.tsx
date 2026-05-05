'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    Calculator,
    Settings2,
    TrendingUp,
    TrendingDown,
    DollarSign,
    Crown
} from 'lucide-react';
import { costApi } from '@/lib/api';
import { cn, formatCurrency } from '@/lib/utils';

// Types (You might want to move these to a separate types file eventually)
interface ModelCost {
    model_id: string;
    model_name: string | null;
    effective_price_1m: number;
    cost_per_request: number;
    tiers: Array<{ tier: string; daily_cost: number; monthly_cost: number; }>;
    nsfw_score?: number;
    indonesian_score?: number;
    final_score?: number;
}

type SortOption = 'price' | 'nsfw' | 'indonesian' | 'quality';

interface SavedSimulation {
    id: string;
    timestamp: number;
    inputs: typeof defaultInputs;
    result: SimulationResult;
}

const defaultInputs = {
    avg_input_tokens: 500,
    avg_output_tokens: 1000,
    daily_requests_free: 50,
    daily_requests_pro: 500,
    daily_requests_admin: 2000,
    daily_images_free: 0,
    daily_images_pro: 20,
    daily_images_admin: 100,
    cost_per_image: 0.002,
};

const STORAGE_KEY = 'cost_simulator_history';

interface SimulationResult {
    summary: {
        total_models_analyzed: number;
        tokens_per_request: number;
        cheapest_cost_per_request: number;
        most_expensive_cost_per_request: number;
        cheapest_model: string | null;
        most_expensive_model: string | null;
    };
    models: ModelCost[];
}

const SummaryCard = ({ title, value, subtext, icon: Icon, color, delay }: any) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay }}
        className="glass-card p-6 rounded-2xl relative overflow-hidden"
    >
        <div className={`absolute top-0 right-0 p-3 opacity-10 ${color}`}>
            <Icon size={100} />
        </div>
        <div className="relative z-10">
            <p className="text-sm font-medium text-slate-400 mb-1">{title}</p>
            <h3 className="text-2xl font-bold text-white tracking-tight">{value}</h3>
            {subtext && <p className="text-xs text-slate-500 mt-2 truncate w-[90%]">{subtext}</p>}
        </div>
    </motion.div>
);

export default function CostSimulator() {
    const [inputs, setInputs] = useState(defaultInputs);
    const [result, setResult] = useState<SimulationResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [sortBy, setSortBy] = useState<SortOption>('price');
    const [history, setHistory] = useState<SavedSimulation[]>([]);
    const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null);

    // Load history from localStorage on mount
    useEffect(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const parsed = JSON.parse(saved) as SavedSimulation[];
                setHistory(parsed);
                // Load most recent if available
                if (parsed.length > 0) {
                    const recent = parsed[0];
                    setInputs(recent.inputs);
                    setResult(recent.result);
                    setActiveHistoryId(recent.id);
                }
            } catch (e) {
                console.error('Failed to parse saved simulations', e);
            }
        }
    }, []);

    // Save to localStorage when history changes
    useEffect(() => {
        if (history.length > 0) {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(history.slice(0, 10))); // Keep last 10
        }
    }, [history]);

    const runSimulation = async () => {
        try {
            setLoading(true);
            const data = await costApi.simulate({
                avg_input_tokens: inputs.avg_input_tokens,
                avg_output_tokens: inputs.avg_output_tokens,
                daily_requests_free: inputs.daily_requests_free,
                daily_requests_pro: inputs.daily_requests_pro,
                daily_requests_admin: inputs.daily_requests_admin,
            });
            const simResult = data as SimulationResult;
            setResult(simResult);

            // Save to history
            const newSim: SavedSimulation = {
                id: Date.now().toString(),
                timestamp: Date.now(),
                inputs: { ...inputs },
                result: simResult,
            };
            setHistory(prev => [newSim, ...prev.filter(s => s.id !== newSim.id)]);
            setActiveHistoryId(newSim.id);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const loadFromHistory = (sim: SavedSimulation) => {
        setInputs(sim.inputs);
        setResult(sim.result);
        setActiveHistoryId(sim.id);
    };

    const startNewSimulation = () => {
        setInputs(defaultInputs);
        setResult(null);
        setActiveHistoryId(null);
    };

    // Calculate Image Costs
    const imageCostFree = inputs.daily_images_free * inputs.cost_per_image * 30;
    const imageCostPro = inputs.daily_images_pro * inputs.cost_per_image * 30;
    const imageCostAdmin = inputs.daily_images_admin * inputs.cost_per_image * 30;

    // Sorting Logic
    const sortedModels = result?.models ? [...result.models].sort((a, b) => {
        switch (sortBy) {
            case 'nsfw':
                return (b.nsfw_score || 0) - (a.nsfw_score || 0); // High NSFW first
            case 'indonesian':
                return (b.indonesian_score || 0) - (a.indonesian_score || 0); // High Indo first
            case 'quality':
                // Combined score: Quality + NSFW capability + Indonesian proficiency
                const aCombo = (a.final_score || 0) + (a.nsfw_score || 0) + (a.indonesian_score || 0);
                const bCombo = (b.final_score || 0) + (b.nsfw_score || 0) + (b.indonesian_score || 0);
                return bCombo - aCombo; // Highest combined score first
            case 'price':
            default:
                return a.cost_per_request - b.cost_per_request; // Low Price first
        }
    }) : [];

    return (
        <div className="min-h-screen pb-20">
            <div className="mb-8">
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                    <h1 className="text-3xl font-bold text-white mb-2">Cost Simulator</h1>
                    <p className="text-slate-400">Project operational costs including LLM and Image generation.</p>
                </motion.div>
            </div>

            {/* History Tabs */}
            {history.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-6 flex items-center gap-2 overflow-x-auto pb-2"
                >
                    <button
                        onClick={startNewSimulation}
                        className={cn(
                            "px-4 py-2 rounded-lg text-sm font-medium transition-all shrink-0 flex items-center gap-2",
                            activeHistoryId === null
                                ? "bg-indigo-600 text-white shadow-lg"
                                : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
                        )}
                    >
                        <Calculator size={14} /> New Simulation
                    </button>
                    <div className="w-px h-6 bg-white/10 shrink-0" />
                    {history.slice(0, 5).map((sim) => (
                        <button
                            key={sim.id}
                            onClick={() => loadFromHistory(sim)}
                            className={cn(
                                "px-4 py-2 rounded-lg text-sm font-medium transition-all shrink-0",
                                activeHistoryId === sim.id
                                    ? "bg-violet-600 text-white shadow-lg"
                                    : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
                            )}
                        >
                            <span className="text-xs opacity-70">
                                {new Date(sim.timestamp).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            <span className="ml-2">{sim.result.summary.total_models_analyzed} Models</span>
                        </button>
                    ))}
                </motion.div>
            )}

            {/* Configuration Panel */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel p-8 rounded-3xl mb-8 relative overflow-hidden"
            >
                <div className="absolute top-0 right-0 p-10 opacity-5 pointer-events-none">
                    <Calculator size={300} />
                </div>

                <div className="relative z-10">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                        {/* LLM Settings */}
                        <div>
                            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                                <Settings2 className="text-indigo-400 w-5 h-5" /> LLM Chat Parameters
                            </h3>
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Avg Input Tokens</label>
                                    <input type="number" value={inputs.avg_input_tokens} onChange={e => setInputs({ ...inputs, avg_input_tokens: parseInt(e.target.value) || 0 })} className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-indigo-500 transition-all font-mono" />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Avg Output Tokens</label>
                                    <input type="number" value={inputs.avg_output_tokens} onChange={e => setInputs({ ...inputs, avg_output_tokens: parseInt(e.target.value) || 0 })} className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-indigo-500 transition-all font-mono" />
                                </div>
                            </div>
                            <div className="space-y-3">
                                <div className="flex items-center gap-4">
                                    <label className="text-xs font-bold uppercase tracking-wider text-emerald-400 w-24">Free Chats/Day</label>
                                    <input type="number" value={inputs.daily_requests_free} onChange={e => setInputs({ ...inputs, daily_requests_free: parseInt(e.target.value) || 0 })} className="flex-1 bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-emerald-500 transition-all font-mono" />
                                </div>
                                <div className="flex items-center gap-4">
                                    <label className="text-xs font-bold uppercase tracking-wider text-violet-400 w-24">Pro Chats/Day</label>
                                    <input type="number" value={inputs.daily_requests_pro} onChange={e => setInputs({ ...inputs, daily_requests_pro: parseInt(e.target.value) || 0 })} className="flex-1 bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-violet-500 transition-all font-mono" />
                                </div>
                                <div className="flex items-center gap-4">
                                    <label className="text-xs font-bold uppercase tracking-wider text-amber-400 w-24">Admin Chats/Day</label>
                                    <input type="number" value={inputs.daily_requests_admin} onChange={e => setInputs({ ...inputs, daily_requests_admin: parseInt(e.target.value) || 0 })} className="flex-1 bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-amber-500 transition-all font-mono" />
                                </div>
                            </div>
                        </div>

                        {/* Image Gen Settings */}
                        <div>
                            <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                                <Settings2 className="text-rose-400 w-5 h-5" /> Image Parameters
                            </h3>
                            <div className="mb-4">
                                <div className="space-y-2">
                                    <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex justify-between">
                                        <span>Cost Per Image ($)</span>
                                        <span className="text-slate-500 lowercase font-normal">e.g. 0.002 for dezgo</span>
                                    </label>
                                    <input type="number" step="0.0001" value={inputs.cost_per_image} onChange={e => setInputs({ ...inputs, cost_per_image: parseFloat(e.target.value) || 0 })} className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-rose-500 transition-all font-mono" />
                                </div>
                            </div>
                            <div className="space-y-3">
                                <div className="flex items-center gap-4">
                                    <label className="text-xs font-bold uppercase tracking-wider text-emerald-400 w-24">Free Imgs/Day</label>
                                    <input type="number" value={inputs.daily_images_free} onChange={e => setInputs({ ...inputs, daily_images_free: parseInt(e.target.value) || 0 })} className="flex-1 bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-emerald-500 transition-all font-mono" />
                                </div>
                                <div className="flex items-center gap-4">
                                    <label className="text-xs font-bold uppercase tracking-wider text-violet-400 w-24">Pro Imgs/Day</label>
                                    <input type="number" value={inputs.daily_images_pro} onChange={e => setInputs({ ...inputs, daily_images_pro: parseInt(e.target.value) || 0 })} className="flex-1 bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-violet-500 transition-all font-mono" />
                                </div>
                                <div className="flex items-center gap-4">
                                    <label className="text-xs font-bold uppercase tracking-wider text-amber-400 w-24">Admin Imgs/Day</label>
                                    <input type="number" value={inputs.daily_images_admin} onChange={e => setInputs({ ...inputs, daily_images_admin: parseInt(e.target.value) || 0 })} className="flex-1 bg-black/20 border border-white/10 rounded-xl px-4 py-2 text-white text-sm focus:border-amber-500 transition-all font-mono" />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="mt-8 flex justify-end">
                        <button
                            onClick={runSimulation}
                            disabled={loading}
                            className="px-8 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold shadow-[0_0_20px_rgba(99,102,241,0.4)] transition-all flex items-center gap-2 disabled:opacity-50"
                        >
                            {loading ? <Settings2 className="animate-spin" /> : <Calculator />}
                            Calculate Projections
                        </button>
                    </div>
                </div>
            </motion.div>

            {/* Results */}
            {result && (
                <div className="space-y-8 animate-fade-in">
                    {/* Summary Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <SummaryCard
                            title="Analysis Scope"
                            value={`${result.summary.total_models_analyzed} LLMs`}
                            icon={Settings2}
                            color="text-blue-400"
                            delay={0.1}
                        />
                        <SummaryCard
                            title="Image Gen Cost"
                            value={formatCurrency(imageCostPro)} // Showing Pro monthly as benchmark
                            subtext={`Pro Tier (${inputs.daily_images_pro}/day)`}
                            icon={Calculator}
                            color="text-rose-400"
                            delay={0.2}
                        />
                        <SummaryCard
                            title="Lowest LLM Cost"
                            value={formatCurrency(result.summary.cheapest_cost_per_request)}
                            subtext={result.summary.cheapest_model}
                            icon={TrendingDown}
                            color="text-emerald-400"
                            delay={0.3}
                        />
                        <SummaryCard
                            title="Highest LLM Cost"
                            value={formatCurrency(result.summary.most_expensive_cost_per_request)}
                            subtext={result.summary.most_expensive_model}
                            icon={TrendingUp}
                            color="text-amber-400"
                            delay={0.4}
                        />
                    </div>

                    {/* Detailed Table */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="glass-panel rounded-2xl overflow-hidden"
                    >
                        <div className="p-6 border-b border-white/5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                            <div className="flex flex-col gap-1">
                                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                    <DollarSign className="text-indigo-400" /> Total Cost Breakdown (LLM Chat + Image Gen)
                                </h3>
                                <div className="text-xs text-slate-500 flex gap-4">
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Free Img: {formatCurrency(imageCostFree)}/mo</span>
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-violet-500"></span> Pro Img: {formatCurrency(imageCostPro)}/mo</span>
                                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"></span> Admin Img: {formatCurrency(imageCostAdmin)}/mo</span>
                                </div>
                            </div>

                            {/* Sorting Controls */}
                            <div className="flex bg-black/20 p-1 rounded-lg">
                                {['price', 'nsfw', 'indonesian', 'quality'].map((opt) => (
                                    <button
                                        key={opt}
                                        onClick={() => setSortBy(opt as SortOption)}
                                        className={cn(
                                            "px-4 py-1.5 rounded-md text-xs font-bold uppercase transition-all",
                                            sortBy === opt
                                                ? "bg-indigo-600 text-white shadow-lg"
                                                : "text-slate-400 hover:text-white hover:bg-white/5"
                                        )}
                                    >
                                        {opt === 'price' ? 'Lowest Price' : opt === 'quality' ? 'Best Quality' : `${opt} Score`}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-white/5 text-xs font-bold text-slate-400 uppercase tracking-widest">
                                    <tr>
                                        <th className="p-4 pl-6">Model Rank</th>
                                        <th className="p-4 text-center">LLM Unit Cost</th>
                                        <th className="p-4 text-center text-emerald-400">
                                            <div>Free (Total)</div>
                                            <div className="text-[9px] opacity-60">LLM + {formatCurrency(imageCostFree)} Img</div>
                                        </th>
                                        <th className="p-4 text-center text-violet-400">
                                            <div>Pro (Total)</div>
                                            <div className="text-[9px] opacity-60">LLM + {formatCurrency(imageCostPro)} Img</div>
                                        </th>
                                        <th className="p-4 text-center text-amber-400">
                                            <div>Admin (Total)</div>
                                            <div className="text-[9px] opacity-60">LLM + {formatCurrency(imageCostAdmin)} Img</div>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5 text-sm">
                                    {sortedModels.slice(0, 50).map((model, idx) => {
                                        const llmCost = (tier: string) => model.tiers.find(t => t.tier === tier)?.monthly_cost || 0;

                                        const totalFree = llmCost('free') + imageCostFree;
                                        const totalPro = llmCost('pro') + imageCostPro;
                                        const totalAdmin = llmCost('admin') + imageCostAdmin;

                                        return (
                                            <tr key={idx} className="hover:bg-white/[0.02] transition-colors group">
                                                <td className="p-4 pl-6">
                                                    <div className="flex items-center gap-4">
                                                        <div className={cn(
                                                            "w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0",
                                                            idx === 0 ? "bg-amber-400 text-black shadow-[0_0_15px_#fbbf24]" :
                                                                idx === 1 ? "bg-slate-300 text-black shadow-[0_0_15px_#cbd5e1]" :
                                                                    idx === 2 ? "bg-orange-400 text-black shadow-[0_0_15px_#fb923c]" :
                                                                        "bg-white/5 text-slate-500"
                                                        )}>
                                                            {idx < 3 ? <Crown size={14} /> : `#${idx + 1}`}
                                                        </div>
                                                        <div>
                                                            <p className="font-semibold text-white group-hover:text-indigo-400 transition-colors">{model.model_name || model.model_id}</p>
                                                            <div className="flex items-center gap-2 mt-1">
                                                                {/* Score Badges */}
                                                                {model.nsfw_score && model.nsfw_score > 50 && (
                                                                    <span className="text-[9px] bg-rose-500/20 text-rose-400 px-1.5 py-0.5 rounded border border-rose-500/30">
                                                                        🔥 {model.nsfw_score?.toFixed(0)}
                                                                    </span>
                                                                )}
                                                                {model.indonesian_score && model.indonesian_score > 50 && (
                                                                    <span className="text-[9px] bg-cyan-500/20 text-cyan-400 px-1.5 py-0.5 rounded border border-cyan-500/30">
                                                                        🇮🇩 {model.indonesian_score?.toFixed(0)}
                                                                    </span>
                                                                )}
                                                                {sortBy === 'quality' && (
                                                                    <span className="text-[9px] bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded border border-indigo-500/30">
                                                                        ⭐ {model.final_score?.toFixed(0)}
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <p className="text-[10px] text-slate-500 font-mono">{formatCurrency(model.effective_price_1m)} / 1M</p>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="p-4 text-center font-mono text-slate-300 bg-white/[0.01]">
                                                    {formatCurrency(model.cost_per_request)}
                                                </td>
                                                <td className="p-4 text-center font-mono text-emerald-400/80 font-medium">
                                                    {formatCurrency(totalFree)}
                                                </td>
                                                <td className="p-4 text-center font-mono text-violet-400/80 font-medium">
                                                    {formatCurrency(totalPro)}
                                                </td>
                                                <td className="p-4 text-center font-mono text-amber-400/80 font-medium">
                                                    {formatCurrency(totalAdmin)}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    );
}
