'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Search,
    Cpu,
    CheckCircle,
    ShieldCheck,
    ChevronDown,
    Globe,
    Sparkles,
    Eye,
    Flame,
    Languages
} from 'lucide-react';
import { modelsApi, Model } from '@/lib/api';
import { cn } from '@/lib/utils';

type SourceFilter = 'all' | 'openrouter' | 'novita';

export default function LlmExplorer() {
    const [models, setModels] = useState<Model[]>([]);
    const [loading, setLoading] = useState(true);

    // Filters
    const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');
    const [minContext, setMinContext] = useState('');
    const [maxPrice, setMaxPrice] = useState('');
    const [moderation, setModeration] = useState('');
    const [tier, setTier] = useState('');
    const [search, setSearch] = useState('');
    // NSFW Research Filters
    const [textOnly, setTextOnly] = useState(true); // Default: exclude VLMs
    const [minNsfwScore, setMinNsfwScore] = useState('');

    useEffect(() => {
        loadModels();
    }, [sourceFilter, minContext, maxPrice, moderation, tier, search, textOnly, minNsfwScore]);

    const loadModels = async () => {
        try {
            setLoading(true);
            const params: Record<string, string> = { type: 'llm' };
            if (sourceFilter !== 'all') params.source = sourceFilter;
            if (minContext) params.min_context_length = minContext;
            if (maxPrice) params.max_price_1m = maxPrice;
            if (moderation) params.is_moderated = moderation;
            if (tier) params.tier = tier;
            if (search) params.search = search;
            // NSFW Research filters
            if (textOnly) params.is_vlm = 'false'; // Exclude VLMs
            if (minNsfwScore) params.min_nsfw_score = minNsfwScore;

            const data = await modelsApi.listLlm(params);
            setModels(data);
        } catch (err) {
            console.error('Failed to load models:', err);
        } finally {
            setLoading(false);
        }
    };

    const formatPrice = (price: number | null) => {
        if (price === null || price === undefined) return '-';
        if (price === 0) return 'Free';
        if (price < 0.01) return `$${price.toFixed(4)}`;
        return `$${price.toFixed(2)}`;
    };

    const formatContext = (length: number | null) => {
        if (!length) return '-';
        if (length >= 1000000) return `${(length / 1000000).toFixed(1)}M`;
        if (length >= 1000) return `${(length / 1000).toFixed(0)}K`;
        return length.toString();
    };

    const ScoreBar = ({ score, color = "indigo" }: { score: number | null, color?: string }) => {
        let barColor = "bg-slate-600";
        if (score) {
            if (color === "rose") {
                barColor = score >= 50 ? "bg-rose-500 shadow-[0_0_10px_#f43f5e]" : "bg-rose-500/50";
            } else if (color === "cyan") {
                barColor = score >= 50 ? "bg-cyan-500 shadow-[0_0_10px_#06b6d4]" : "bg-cyan-500/50";
            } else {
                if (score >= 80) barColor = "bg-emerald-500 shadow-[0_0_10px_#10b981]";
                else if (score >= 60) barColor = "bg-indigo-500 shadow-[0_0_10px_#6366f1]";
                else if (score >= 40) barColor = "bg-amber-500 shadow-[0_0_10px_#f59e0b]";
                else barColor = "bg-rose-500 shadow-[0_0_10px_#ef4444]";
            }
        }

        return (
            <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${score || 0}%` }}
                        className={cn("h-full rounded-full transition-all duration-1000 ease-out", barColor)}
                    />
                </div>
                <span className={cn("text-[10px] font-mono font-bold w-5 text-right", score ? "text-white" : "text-slate-600")}>
                    {score?.toFixed(0) || '-'}
                </span>
            </div>
        )
    }

    const SourceBadge = ({ source }: { source: string }) => {
        const isOpenRouter = source === 'openrouter';
        return (
            <span className={cn(
                "text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full border",
                isOpenRouter
                    ? "bg-blue-500/10 text-blue-400 border-blue-500/30"
                    : "bg-purple-500/10 text-purple-400 border-purple-500/30"
            )}>
                {isOpenRouter ? 'OpenRouter' : 'Novita'}
            </span>
        )
    }

    return (
        <div className="min-h-screen pb-20">
            {/* Header */}
            <div className="flex items-end justify-between mb-8">
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                    <h1 className="text-3xl font-bold text-white mb-2">LLM Explorer</h1>
                    <p className="text-slate-400">Find the best NSFW + Indonesian capable LLMs.</p>
                </motion.div>
            </div>

            {/* Source Toggle Buttons */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-2 mb-4"
            >
                {[
                    { value: 'all', label: 'All Models', icon: Sparkles },
                    { value: 'openrouter', label: 'OpenRouter', icon: Globe },
                    { value: 'novita', label: 'Novita AI', icon: Cpu },
                ].map(({ value, label, icon: Icon }) => (
                    <button
                        key={value}
                        onClick={() => setSourceFilter(value as SourceFilter)}
                        className={cn(
                            "px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-all border",
                            sourceFilter === value
                                ? "bg-indigo-500/20 text-indigo-400 border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.2)]"
                                : "bg-white/5 text-slate-400 border-white/10 hover:bg-white/10"
                        )}
                    >
                        <Icon size={16} />
                        {label}
                    </button>
                ))}

                {/* Text Only Toggle */}
                <div className="ml-auto flex items-center gap-2">
                    <button
                        onClick={() => setTextOnly(!textOnly)}
                        className={cn(
                            "px-3 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-all border",
                            textOnly
                                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                                : "bg-white/5 text-slate-400 border-white/10 hover:bg-white/10"
                        )}
                    >
                        <Eye size={16} />
                        Text Only
                    </button>
                </div>
            </motion.div>

            {/* Filter Bar */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="sticky top-0 z-20 glass-panel p-4 rounded-xl mb-6 flex flex-wrap gap-4 items-center shadow-lg"
            >
                <div className="flex-1 min-w-[200px] relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
                    <input
                        type="text"
                        placeholder="Search models... (e.g. dolphin, grok, mythomax)"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="w-full bg-[#030305] border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                    />
                </div>

                <div className="h-8 w-px bg-white/10 mx-2 hidden md:block" />

                <div className="flex gap-3 flex-wrap">
                    <div className="relative group">
                        <select
                            value={minContext}
                            onChange={e => setMinContext(e.target.value)}
                            className="appearance-none bg-white/5 border border-white/10 rounded-lg px-4 py-2 pr-10 text-sm text-slate-300 focus:outline-none hover:bg-white/10 transition-colors cursor-pointer min-w-[140px]"
                        >
                            <option value="">Context: Any</option>
                            <option value="8192">8K+</option>
                            <option value="32768">32K+</option>
                            <option value="65536">64K+</option>
                            <option value="131072">128K+</option>
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4 pointer-events-none" />
                    </div>

                    <div className="relative group">
                        <select
                            value={tier}
                            onChange={e => setTier(e.target.value)}
                            className="appearance-none bg-white/5 border border-white/10 rounded-lg px-4 py-2 pr-10 text-sm text-slate-300 focus:outline-none hover:bg-white/10 transition-colors cursor-pointer min-w-[120px]"
                        >
                            <option value="">Tier: Any</option>
                            <option value="free">Free ($0-$0.3)</option>
                            <option value="pro">Pro ($0.3-$0.7)</option>
                            <option value="admin">Admin (Premium)</option>
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4 pointer-events-none" />
                    </div>

                    <div className="relative group">
                        <select
                            value={moderation}
                            onChange={e => setModeration(e.target.value)}
                            className="appearance-none bg-white/5 border border-white/10 rounded-lg px-4 py-2 pr-10 text-sm text-slate-300 focus:outline-none hover:bg-white/10 transition-colors cursor-pointer min-w-[140px]"
                        >
                            <option value="">Safety: Any</option>
                            <option value="true">Moderated</option>
                            <option value="false">Unfiltered (NSFW)</option>
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4 pointer-events-none" />
                    </div>

                    <div className="relative group">
                        <select
                            value={minNsfwScore}
                            onChange={e => setMinNsfwScore(e.target.value)}
                            className="appearance-none bg-rose-500/10 border border-rose-500/20 rounded-lg px-4 py-2 pr-10 text-sm text-rose-300 focus:outline-none hover:bg-rose-500/20 transition-colors cursor-pointer min-w-[140px]"
                        >
                            <option value="">🔥 NSFW: Any</option>
                            <option value="30">NSFW 30+</option>
                            <option value="50">NSFW 50+</option>
                            <option value="70">NSFW 70+</option>
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-rose-400 w-4 h-4 pointer-events-none" />
                    </div>
                </div>
            </motion.div>

            {/* Table Section */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="glass-panel rounded-2xl overflow-hidden"
            >
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-white/5 bg-white/[0.02]">
                                <th className="p-4 pl-6 text-xs font-bold text-slate-500 uppercase tracking-widest w-[30%]">Model</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Source</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Stats</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Safety</th>
                                <th className="p-4 text-xs font-bold text-rose-400 uppercase tracking-widest w-[10%] text-center">🔥 NSFW</th>
                                <th className="p-4 text-xs font-bold text-cyan-400 uppercase tracking-widest w-[10%] text-center">🇮🇩 Indo</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest w-[12%] text-center">Score</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Tier</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {loading ? (
                                [...Array(6)].map((_, i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td className="p-4 pl-6"><div className="h-6 w-48 bg-white/5 rounded" /></td>
                                        <td className="p-4"><div className="h-6 w-16 bg-white/5 rounded mx-auto" /></td>
                                        <td className="p-4"><div className="h-6 w-20 bg-white/5 rounded mx-auto" /></td>
                                        <td className="p-4"><div className="h-6 w-8 bg-white/5 rounded mx-auto" /></td>
                                        <td className="p-4"><div className="h-6 w-14 bg-white/5 rounded mx-auto" /></td>
                                        <td className="p-4"><div className="h-6 w-14 bg-white/5 rounded mx-auto" /></td>
                                        <td className="p-4"><div className="h-6 w-full bg-white/5 rounded" /></td>
                                        <td className="p-4"><div className="h-6 w-16 bg-white/5 rounded mx-auto" /></td>
                                    </tr>
                                ))
                            ) : models.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="p-12 text-center text-slate-500">
                                        <Search className="w-12 h-12 mx-auto mb-4 opacity-20" />
                                        No models found matching your criteria.
                                    </td>
                                </tr>
                            ) : (
                                models.map((model) => (
                                    <tr key={model.id} className="group hover:bg-white/[0.02] transition-colors">
                                        <td className="p-4 pl-6">
                                            <div className="flex items-center gap-4">
                                                <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0 group-hover:bg-indigo-500/20 transition-colors">
                                                    {model.is_vlm ? (
                                                        <Eye className="w-5 h-5 text-purple-400" />
                                                    ) : (
                                                        <Cpu className="w-5 h-5 text-indigo-400" />
                                                    )}
                                                </div>
                                                <div>
                                                    <h3 className="font-semibold text-white text-sm truncate max-w-[220px] group-hover:text-indigo-300 transition-colors">
                                                        {model.name || model.model_id}
                                                    </h3>
                                                    <div className="flex items-center gap-2 mt-0.5">
                                                        <span className="text-[10px] text-slate-500 px-1.5 py-0.5 rounded bg-white/5 border border-white/5 font-mono">{model.provider}</span>
                                                        {model.is_vlm && (
                                                            <span className="text-[9px] text-purple-400 px-1 py-0.5 rounded bg-purple-500/10 border border-purple-500/20">VLM</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="p-4 text-center">
                                            <SourceBadge source={model.source} />
                                        </td>
                                        <td className="p-4 text-center">
                                            <div className="flex flex-col gap-1 items-center">
                                                <span className="text-xs font-mono text-slate-300 px-2 py-0.5 rounded-full bg-slate-500/10 border border-slate-500/20">
                                                    {formatContext(model.context_length)} ctx
                                                </span>
                                                <span className={cn(
                                                    "text-xs font-mono",
                                                    model.effective_price_1m !== null && model.effective_price_1m <= 0.3 ? "text-emerald-400" : "text-slate-400"
                                                )}>
                                                    {formatPrice(model.effective_price_1m)}/M
                                                </span>
                                            </div>
                                        </td>
                                        <td className="p-4 text-center">
                                            {model.is_moderated ? (
                                                <div className="inline-flex p-1.5 rounded-lg bg-amber-500/10 text-amber-500" title="Moderated">
                                                    <ShieldCheck className="w-4 h-4" />
                                                </div>
                                            ) : (
                                                <div className="inline-flex p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500" title="Unfiltered (NSFW Capable)">
                                                    <CheckCircle className="w-4 h-4" />
                                                </div>
                                            )}
                                        </td>
                                        <td className="p-4">
                                            <ScoreBar score={model.nsfw_score ?? null} color="rose" />
                                        </td>
                                        <td className="p-4">
                                            <ScoreBar score={model.indonesian_score ?? null} color="cyan" />
                                        </td>
                                        <td className="p-4">
                                            <ScoreBar score={model.final_score} />
                                        </td>
                                        <td className="p-4 text-center">
                                            {model.tier_recommendation ? (
                                                <span className={cn(
                                                    "px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border",
                                                    model.tier_recommendation === 'free' && "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
                                                    model.tier_recommendation === 'pro' && "bg-violet-500/10 text-violet-400 border-violet-500/20",
                                                    model.tier_recommendation === 'admin' && "bg-amber-500/10 text-amber-400 border-amber-500/20",
                                                )}>
                                                    {model.tier_recommendation}
                                                </span>
                                            ) : (
                                                <span className="text-slate-700">-</span>
                                            )}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </motion.div>
        </div>
    );
}
