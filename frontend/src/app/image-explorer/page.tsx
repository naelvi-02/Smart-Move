'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Search,
    Image as ImageIcon,
    CheckCircle,
    AlertOctagon,
    Download,
    Heart,
    Palette,
    ChevronDown,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';
import { modelsApi, Model } from '@/lib/api';
import { cn, formatNumber } from '@/lib/utils';

const StyleBucketCard = ({ bucket, icon: Icon, label, active, onClick, color }: any) => (
    <button
        onClick={onClick}
        className={cn(
            "flex flex-col items-center justify-center p-4 rounded-xl border transition-all duration-300 group",
            active
                ? `bg-${color}-500/10 border-${color}-500/50 shadow-[0_0_20px_rgba(var(--color-${color}),0.2)]`
                : "bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10"
        )}
    >
        <Icon className={cn("w-6 h-6 mb-2 transition-colors", active ? `text-${color}-400` : "text-slate-400 group-hover:text-white")} />
        <span className={cn("text-xs font-medium", active ? "text-white" : "text-slate-400")}>{label}</span>
    </button>
);

export default function ImageExplorer() {
    const [models, setModels] = useState<Model[]>([]);
    const [loading, setLoading] = useState(true);
    const [source, setSource] = useState('');
    const [styleBucket, setStyleBucket] = useState('');
    const [sortBy, setSortBy] = useState('popular');
    const [availableOnly, setAvailableOnly] = useState(true);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalModels, setTotalModels] = useState(0);
    const [expandedModel, setExpandedModel] = useState<string | null>(null);
    const itemsPerPage = 50;

    useEffect(() => {
        setCurrentPage(1); // Reset to page 1 when filters change
    }, [source, styleBucket, sortBy, availableOnly]);

    useEffect(() => {
        loadModels();
    }, [source, styleBucket, sortBy, availableOnly, currentPage]);

    const loadModels = async () => {
        try {
            setLoading(true);
            const skip = (currentPage - 1) * itemsPerPage;
            const params: Record<string, string> = {
                type: 'image',
                skip: skip.toString(),
                limit: itemsPerPage.toString(),
                sort_by: sortBy
            };
            if (source) params.source = source;
            if (styleBucket) params.style_bucket = styleBucket;
            if (availableOnly) params.available_in_novita = 'true';

            const response = await modelsApi.listImage(params);
            // Response now has { models: [...], total: number } or is Model[]
            const data = response as any;
            setModels(data.models || data);
            setTotalModels(data.total || (data.models || data).length);
        } catch (err) {
            console.error('Failed to load models:', err);
        } finally {
            setLoading(false);
        }
    };

    const categories = [
        { id: '', label: 'All', icon: Palette, color: 'blue' },
        { id: 'realistic_human', label: 'Realistic', icon: ImageIcon, color: 'indigo' },
        { id: 'anime_2d', label: 'Anime 2D', icon: Heart, color: 'pink' },
        { id: 'anime_3d', label: '3D/CGI', icon: CheckCircle, color: 'violet' },
        { id: 'other', label: 'Others', icon: AlertOctagon, color: 'amber' },
    ];

    return (
        <div className="min-h-screen pb-20">
            <div className="flex items-end justify-between mb-8">
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                    <h1 className="text-3xl font-bold text-white mb-2">Image Models</h1>
                    <p className="text-slate-400">Generative art models from Civitai and Novita.</p>
                </motion.div>
            </div>

            {/* Style Buckets */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8"
            >
                {categories.map((cat, i) => (
                    <motion.button
                        key={cat.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        onClick={() => setStyleBucket(cat.id)}
                        className={cn(
                            "relative p-4 rounded-xl border flex flex-col items-center gap-3 transition-all duration-300 overflow-hidden group",
                            styleBucket === cat.id
                                ? "bg-white/10 border-indigo-500/50 shadow-[0_0_20px_rgba(99,102,241,0.15)]"
                                : "bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10"
                        )}
                    >
                        <div className={cn(
                            "p-2 rounded-lg transition-colors",
                            styleBucket === cat.id ? "bg-indigo-500 text-white" : "bg-white/5 text-slate-400 group-hover:text-white"
                        )}>
                            <cat.icon size={20} />
                        </div>
                        <span className={cn("text-xs font-semibold uppercase tracking-wider", styleBucket === cat.id ? "text-white" : "text-slate-400")}>
                            {cat.label}
                        </span>
                        {styleBucket === cat.id && (
                            <motion.div layoutId="activeBucket" className="absolute inset-0 border-2 border-indigo-500 rounded-xl" />
                        )}
                    </motion.button>
                ))}
            </motion.div>

            {/* Table Section */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="glass-panel rounded-2xl overflow-hidden"
            >
                {/* Simple Toolbar */}
                <div className="p-4 border-b border-white/5 flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-3">
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-2">Source:</span>
                            <select
                                value={source}
                                onChange={e => setSource(e.target.value)}
                                className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                            >
                                <option value="">All Sources</option>
                                <option value="civitai">Civitai</option>
                                <option value="novita">Novita</option>
                            </select>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Sort:</span>
                            <select
                                value={sortBy}
                                onChange={e => setSortBy(e.target.value)}
                                className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                            >
                                <option value="popular">Highest Rated</option>
                                <option value="downloads">Most Downloaded</option>
                                <option value="likes">Most Liked</option>
                            </select>
                        </div>

                        {/* Availability Toggle */}
                        <div className="flex items-center gap-3 pl-4 border-l border-white/10">
                            <label className="flex items-center gap-2 cursor-pointer group">
                                <div className="relative">
                                    <input
                                        type="checkbox"
                                        checked={availableOnly}
                                        onChange={e => setAvailableOnly(e.target.checked)}
                                        className="sr-only"
                                    />
                                    <div className={cn(
                                        "w-10 h-5 rounded-full transition-colors duration-300",
                                        availableOnly ? "bg-emerald-500/20 border-emerald-500/50" : "bg-white/5 border-white/10 border"
                                    )}></div>
                                    <div className={cn(
                                        "absolute top-1 left-1 w-3 h-3 rounded-full transition-transform duration-300",
                                        availableOnly ? "translate-x-5 bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]" : "bg-slate-400"
                                    )}></div>
                                </div>
                                <span className={cn(
                                    "text-xs font-medium transition-colors",
                                    availableOnly ? "text-emerald-400" : "text-slate-400 group-hover:text-slate-300"
                                )}>
                                    Available in Novita
                                </span>
                            </label>
                        </div>
                    </div>
                    <span className="text-xs text-slate-500 font-mono">Found {totalModels.toLocaleString()} Models</span>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-white/[0.02]">
                                <th className="p-4 pl-6 text-xs font-bold text-slate-500 uppercase tracking-widest w-[40%]">Model Info</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Style</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Engagement</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Size</th>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Content</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {loading ? (
                                [...Array(6)].map((_, i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td className="p-4 pl-6"><div className="h-6 w-48 bg-white/5 rounded" /></td>
                                        <td className="p-4"><div className="h-6 w-20 bg-white/5 rounded mx-auto" /></td>
                                        <td className="p-4"><div className="h-6 w-20 bg-white/5 rounded mx-auto" /></td>
                                        <td className="p-4"><div className="h-6 w-12 bg-white/5 rounded mx-auto" /></td>
                                        <td className="p-4"><div className="h-6 w-8 bg-white/5 rounded mx-auto" /></td>
                                    </tr>
                                ))
                            ) : models.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="p-12 text-center text-slate-500">
                                        No image models found. Sync database?
                                    </td>
                                </tr>
                            ) : (
                                models.map((model) => (
                                    <React.Fragment key={model.id}>
                                        <tr
                                            className="group hover:bg-white/[0.02] transition-colors cursor-pointer"
                                            onClick={() => setExpandedModel(expandedModel === model.id ? null : model.id)}
                                        >
                                            <td className="p-4 pl-6">
                                                <div className="flex items-center gap-4">
                                                    {model.preview_image_url ? (
                                                        <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 border border-white/10 bg-black/20">
                                                            <img
                                                                src={model.preview_image_url}
                                                                alt={model.name || 'Preview'}
                                                                className="w-full h-full object-cover"
                                                                loading="lazy"
                                                            />
                                                        </div>
                                                    ) : (
                                                        <div className={cn(
                                                            "w-12 h-12 rounded-lg flex items-center justify-center shrink-0 border",
                                                            model.source === 'civitai' ? "bg-blue-500/10 border-blue-500/20 text-blue-400" : "bg-cyan-500/10 border-cyan-500/20 text-cyan-400"
                                                        )}>
                                                            <ImageIcon size={20} />
                                                        </div>
                                                    )}
                                                    <div>
                                                        <h3 className="font-semibold text-white text-sm truncate max-w-[240px] group-hover:text-blue-300 transition-colors">{model.name || model.model_id}</h3>
                                                        <div className="flex items-center gap-2 mt-0.5">
                                                            <span className="text-[10px] text-slate-500 uppercase tracking-wider">{model.source}</span>
                                                            <span className="text-[10px] text-slate-600">•</span>
                                                            <span className="text-[10px] text-slate-500 truncate max-w-[150px]">{model.base_model}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="p-4 text-center">
                                                {model.style_bucket ? (
                                                    <span className={cn(
                                                        "px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border",
                                                        model.style_bucket.includes('anime') ? "bg-pink-500/10 text-pink-400 border-pink-500/20" : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                                                    )}>
                                                        {model.style_bucket.replace('_', ' ')}
                                                    </span>
                                                ) : <span className="text-slate-700">-</span>}
                                            </td>
                                            <td className="p-4">
                                                <div className="flex justify-center gap-4">
                                                    <div className="flex items-center gap-1.5 text-xs text-slate-400" title="Downloads">
                                                        <Download size={14} />
                                                        {formatNumber(model.download_count)}
                                                    </div>
                                                    <div className="flex items-center gap-1.5 text-xs text-slate-400" title="Favorites">
                                                        <Heart size={14} />
                                                        {formatNumber(model.favorite_count)}
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="p-4 text-center font-mono text-xs text-slate-400">
                                                {model.size_gb ? `${model.size_gb.toFixed(1)} GB` : '-'}
                                            </td>
                                            <td className="p-4 text-center">
                                                {model.nsfw_flag ? (
                                                    <span className="inline-flex p-1.5 rounded-lg bg-rose-500/10 text-rose-500 border border-rose-500/20" title="NSFW Content">
                                                        <AlertOctagon size={16} />
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" title="Safe">
                                                        <CheckCircle size={16} />
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                        {/* Expanded Preview Card Row */}
                                        {expandedModel === model.id && model.preview_image_url && (
                                            <tr className="bg-gradient-to-b from-white/[0.02] to-transparent">
                                                <td colSpan={5} className="p-6">
                                                    <motion.div
                                                        initial={{ opacity: 0, height: 0 }}
                                                        animate={{ opacity: 1, height: 'auto' }}
                                                        exit={{ opacity: 0, height: 0 }}
                                                        className="flex gap-6"
                                                    >
                                                        <div className="w-80 h-auto rounded-xl overflow-hidden border border-white/10 shadow-2xl">
                                                            <img
                                                                src={model.preview_image_url}
                                                                alt={model.name || 'Preview'}
                                                                className="w-full h-auto object-contain bg-black"
                                                            />
                                                        </div>
                                                        <div className="flex-1 space-y-4">
                                                            <div>
                                                                <h4 className="text-lg font-bold text-white">{model.name}</h4>
                                                                <p className="text-sm text-slate-400 mt-1">Source: {model.source} • Base: {model.base_model || 'Unknown'}</p>
                                                            </div>
                                                            <div className="flex flex-wrap gap-2">
                                                                {model.tags?.slice(0, 8).map((tag, i) => (
                                                                    <span key={i} className="px-2 py-1 rounded bg-white/5 text-xs text-slate-400 border border-white/10">
                                                                        {tag}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                            <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">
                                                                {model.description || 'No description available.'}
                                                            </p>
                                                        </div>
                                                    </motion.div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {
                    !loading && models.length > 0 && (
                        <div className="p-4 border-t border-white/5 flex items-center justify-between">
                            <div className="text-xs text-slate-500">
                                Page {currentPage} of {Math.ceil(totalModels / itemsPerPage)} • {totalModels.toLocaleString()} total models
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                    className="p-2 rounded-lg bg-white/5 border border-white/10 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
                                >
                                    <ChevronLeft size={16} className="text-white" />
                                </button>

                                {/* Page Numbers */}
                                <div className="flex items-center gap-1">
                                    {[...Array(Math.min(7, Math.ceil(totalModels / itemsPerPage)))].map((_, i) => {
                                        const pageNum = currentPage <= 4
                                            ? i + 1
                                            : currentPage + i - 3;

                                        if (pageNum < 1 || pageNum > Math.ceil(totalModels / itemsPerPage)) return null;

                                        return (
                                            <button
                                                key={pageNum}
                                                onClick={() => setCurrentPage(pageNum)}
                                                className={cn(
                                                    "w-8 h-8 rounded-lg text-xs font-medium transition-all",
                                                    currentPage === pageNum
                                                        ? "bg-indigo-600 text-white shadow-lg"
                                                        : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white"
                                                )}
                                            >
                                                {pageNum}
                                            </button>
                                        );
                                    })}
                                </div>

                                <button
                                    onClick={() => setCurrentPage(p => p + 1)}
                                    disabled={models.length < itemsPerPage}
                                    className="p-2 rounded-lg bg-white/5 border border-white/10 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
                                >
                                    <ChevronRight size={16} className="text-white" />
                                </button>
                            </div>
                        </div>
                    )
                }
            </motion.div >
        </div >
    );
}
