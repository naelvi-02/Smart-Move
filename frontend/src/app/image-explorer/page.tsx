'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Image as ImageIcon,
    CheckCircle,
    AlertOctagon,
    Download,
    Heart,
    Palette,
    ChevronLeft,
    ChevronRight
} from 'lucide-react';
import { modelsApi, Model, ImageModelDetails } from '@/lib/api';
import { cn, formatNumber } from '@/lib/utils';

const IMAGE_SKELETON_KEYS = ['image-skeleton-1', 'image-skeleton-2', 'image-skeleton-3', 'image-skeleton-4', 'image-skeleton-5', 'image-skeleton-6'];

export default function ImageExplorer() {
    const [models, setModels] = useState<Model[]>([]);
    const [loading, setLoading] = useState(true);
    const [source, setSource] = useState('');
    const [styleBucket, setStyleBucket] = useState('');
    const [sortBy, setSortBy] = useState('popular');
    const [availableOnly, setAvailableOnly] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalModels, setTotalModels] = useState(0);
    const [expandedModel, setExpandedModel] = useState<string | null>(null);
    const [detailCache, setDetailCache] = useState<Record<string, ImageModelDetails>>({});
    const [detailLoadingKey, setDetailLoadingKey] = useState<string | null>(null);
    const itemsPerPage = 50;

    const getDetailKey = useCallback((model: Model) => `${model.source}:${model.model_id}`, []);

    const loadModels = useCallback(async () => {
        try {
            setLoading(true);
            const skip = (currentPage - 1) * itemsPerPage;
            const params: Record<string, string> = {
                type: 'image',
                skip: skip.toString(),
                limit: itemsPerPage.toString(),
                sort_by: sortBy,
            };
            if (source) params.source = source;
            if (styleBucket) params.style_bucket = styleBucket;
            if (availableOnly) params.available_in_novita = 'true';

            const response = await modelsApi.listImage(params);
            const data = response as { models?: Model[]; total?: number } | Model[];
            const nextModels = Array.isArray(data) ? data : (data.models || []);
            setModels(nextModels);
            setTotalModels(Array.isArray(data) ? data.length : (data.total || nextModels.length));
        } catch (err) {
            console.error('Failed to load models:', err);
        } finally {
            setLoading(false);
        }
    }, [availableOnly, currentPage, sortBy, source, styleBucket]);

    useEffect(() => {
        loadModels();
    }, [loadModels]);

    const categories = [
        { id: '', label: 'All', icon: Palette },
        { id: 'realistic_human', label: 'Realistic', icon: ImageIcon },
        { id: 'anime_2d', label: 'Anime 2D', icon: Heart },
        { id: 'anime_3d', label: '3D/CGI', icon: CheckCircle },
        { id: 'other', label: 'Others', icon: AlertOctagon },
    ];

    const toggleExpandedModel = useCallback(async (model: Model) => {
        const detailKey = getDetailKey(model);
        const nextExpandedModel = expandedModel === model.id ? null : model.id;
        setExpandedModel(nextExpandedModel);

        if (!nextExpandedModel || detailCache[detailKey] || detailLoadingKey === detailKey) {
            return;
        }

        try {
            setDetailLoadingKey(detailKey);
            const details = await modelsApi.getImageDetails(model.source, model.model_id);
            setDetailCache((prev) => ({ ...prev, [detailKey]: details }));
        } catch (error) {
            console.error('Failed to load image model details:', error);
        } finally {
            setDetailLoadingKey(null);
        }
    }, [detailCache, detailLoadingKey, expandedModel, getDetailKey]);

    const totalPages = Math.max(1, Math.ceil(totalModels / itemsPerPage));

    return (
        <div className="min-h-screen pb-20">
            <div className="flex items-end justify-between mb-8">
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
                    <h1 className="text-3xl font-bold text-white mb-2">Image Models</h1>
                    <p className="text-slate-400">Generative art models from Civitai and Novita.</p>
                </motion.div>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8"
            >
                {categories.map((cat, i) => (
                    <motion.button
                        key={cat.id || 'all'}
                        type="button"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        onClick={() => {
                            setStyleBucket(cat.id);
                            setCurrentPage(1);
                        }}
                        className={cn(
                            'relative p-4 rounded-xl border flex flex-col items-center gap-3 transition-all duration-300 overflow-hidden group',
                            styleBucket === cat.id
                                ? 'bg-white/10 border-indigo-500/50 shadow-[0_0_20px_rgba(99,102,241,0.15)]'
                                : 'bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10'
                        )}
                    >
                        <div className={cn(
                            'p-2 rounded-lg transition-colors',
                            styleBucket === cat.id ? 'bg-indigo-500 text-white' : 'bg-white/5 text-slate-400 group-hover:text-white'
                        )}>
                            <cat.icon size={20} />
                        </div>
                        <span className={cn('text-xs font-semibold uppercase tracking-wider', styleBucket === cat.id ? 'text-white' : 'text-slate-400')}>
                            {cat.label}
                        </span>
                        {styleBucket === cat.id && (
                            <motion.div layoutId="activeBucket" className="absolute inset-0 border-2 border-indigo-500 rounded-xl" />
                        )}
                    </motion.button>
                ))}
            </motion.div>

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="glass-panel rounded-2xl overflow-hidden"
            >
                <div className="p-4 border-b border-white/5 flex justify-between items-center">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-3">
                            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-2">Source:</span>
                            <select
                                value={source}
                                onChange={(e) => {
                                    setSource(e.target.value);
                                    setCurrentPage(1);
                                }}
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
                                onChange={(e) => {
                                    setSortBy(e.target.value);
                                    setCurrentPage(1);
                                }}
                                className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                            >
                                <option value="popular">Best Overall</option>
                                <option value="downloads">Most Downloaded</option>
                                <option value="likes">Most Liked</option>
                                <option value="newest">Newest Synced</option>
                            </select>
                        </div>

                        <div className="flex items-center gap-3 pl-4 border-l border-white/10">
                            <label className="flex items-center gap-2 cursor-pointer group">
                                <div className="relative">
                                    <input
                                        type="checkbox"
                                        checked={availableOnly}
                                        onChange={(e) => {
                                            setAvailableOnly(e.target.checked);
                                            setCurrentPage(1);
                                        }}
                                        className="sr-only"
                                    />
                                    <div className={cn(
                                        'w-10 h-5 rounded-full transition-colors duration-300',
                                        availableOnly ? 'bg-emerald-500/20 border-emerald-500/50' : 'bg-white/5 border-white/10 border'
                                    )} />
                                    <div className={cn(
                                        'absolute top-1 left-1 w-3 h-3 rounded-full transition-transform duration-300',
                                        availableOnly ? 'translate-x-5 bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-slate-400'
                                    )} />
                                </div>
                                <span className={cn(
                                    'text-xs font-medium transition-colors',
                                    availableOnly ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-300'
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
                                IMAGE_SKELETON_KEYS.map((key) => (
                                    <tr key={key} className="animate-pulse">
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
                                models.map((model) => {
                                    const detailKey = getDetailKey(model);
                                    const details = detailCache[detailKey];
                                    const galleryImages = details?.gallery_images?.length
                                        ? details.gallery_images
                                        : model.preview_image_url
                                            ? [model.preview_image_url]
                                            : [];
                                    const modelName = details?.name || model.name || model.model_id;
                                    const modelDescription = details?.description || model.description;
                                    const modelTags = details?.tags || model.tags || [];
                                    const modelBase = details?.base_model || model.base_model;

                                    return (
                                        <React.Fragment key={model.id}>
                                            <tr
                                                className="group hover:bg-white/[0.02] transition-colors cursor-pointer"
                                                onClick={() => {
                                                    void toggleExpandedModel(model);
                                                }}
                                            >
                                                <td className="p-4 pl-6">
                                                    <div className="flex items-center gap-4">
                                                        {model.preview_image_url ? (
                                                            <div className="w-12 h-12 rounded-lg overflow-hidden shrink-0 border border-white/10 bg-black/20">
                                                                <img
                                                                    src={model.preview_image_url}
                                                                    alt={modelName}
                                                                    className="w-full h-full object-cover"
                                                                    loading="lazy"
                                                                />
                                                            </div>
                                                        ) : (
                                                            <div className={cn(
                                                                'w-12 h-12 rounded-lg flex items-center justify-center shrink-0 border',
                                                                model.source === 'civitai' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' : 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400'
                                                            )}>
                                                                <ImageIcon size={20} />
                                                            </div>
                                                        )}
                                                        <div>
                                                            <h3 className="font-semibold text-white text-sm truncate max-w-[240px] group-hover:text-blue-300 transition-colors">{modelName}</h3>
                                                            <div className="flex items-center gap-2 mt-0.5">
                                                                <span className="text-[10px] text-slate-500 uppercase tracking-wider">{model.source}</span>
                                                                <span className="text-[10px] text-slate-600">•</span>
                                                                <span className="text-[10px] text-slate-500 truncate max-w-[150px]">{modelBase}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="p-4 text-center">
                                                    {model.style_bucket ? (
                                                        <span className={cn(
                                                            'px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border',
                                                            model.style_bucket.includes('anime') ? 'bg-pink-500/10 text-pink-400 border-pink-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'
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
                                            {expandedModel === model.id && (
                                                <tr className="bg-gradient-to-b from-white/[0.02] to-transparent">
                                                    <td colSpan={5} className="p-6">
                                                        <motion.div
                                                            initial={{ opacity: 0, height: 0 }}
                                                            animate={{ opacity: 1, height: 'auto' }}
                                                            exit={{ opacity: 0, height: 0 }}
                                                            className="flex gap-6"
                                                        >
                                                            <div className="w-80 rounded-xl overflow-hidden border border-white/10 shadow-2xl bg-black/20 min-h-[260px] p-3">
                                                                {detailLoadingKey === detailKey ? (
                                                                    <div className="h-full min-h-[236px] rounded-lg bg-white/5 animate-pulse" />
                                                                ) : galleryImages.length > 0 ? (
                                                                    <div className={cn('grid gap-3', galleryImages.length > 1 ? 'grid-cols-2' : 'grid-cols-1')}>
                                                                        {galleryImages.slice(0, 4).map((imageUrl) => (
                                                                            <div
                                                                                key={`${detailKey}-${imageUrl}`}
                                                                                className={cn(
                                                                                    'rounded-lg overflow-hidden border border-white/10 bg-black/30',
                                                                                    imageUrl === galleryImages[0] && galleryImages.length === 3 ? 'col-span-2' : ''
                                                                                )}
                                                                            >
                                                                                <img
                                                                                    src={imageUrl}
                                                                                    alt={modelName}
                                                                                    className="w-full h-40 object-cover"
                                                                                    loading="lazy"
                                                                                />
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                ) : (
                                                                    <div className="flex flex-col items-center justify-center gap-3 text-slate-500 p-8 text-center min-h-[236px]">
                                                                        <ImageIcon size={36} />
                                                                        <p className="text-sm">No preview image available yet.</p>
                                                                    </div>
                                                                )}
                                                            </div>
                                                            <div className="flex-1 space-y-4">
                                                                <div>
                                                                    <h4 className="text-lg font-bold text-white">{modelName}</h4>
                                                                    <p className="text-sm text-slate-400 mt-1">Source: {model.source} • Base: {modelBase || 'Unknown'}</p>
                                                                </div>
                                                                <div className="flex flex-wrap gap-2">
                                                                    {modelTags.slice(0, 8).map((tag) => (
                                                                        <span key={`${model.id}-${tag}`} className="px-2 py-1 rounded bg-white/5 text-xs text-slate-400 border border-white/10">
                                                                            {tag}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                                <p className="text-xs text-slate-500 leading-relaxed">
                                                                    {modelDescription || 'No description available.'}
                                                                </p>
                                                            </div>
                                                        </motion.div>
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                {!loading && models.length > 0 && (
                    <div className="p-4 border-t border-white/5 flex items-center justify-between">
                        <div className="text-xs text-slate-500">
                            Page {currentPage} of {totalPages} • {totalModels.toLocaleString()} total models
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                className="p-2 rounded-lg bg-white/5 border border-white/10 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
                            >
                                <ChevronLeft size={16} className="text-white" />
                            </button>

                            <div className="flex items-center gap-1">
                                {[...Array(Math.min(7, totalPages))].map((_, i) => {
                                    const pageNum = currentPage <= 4 ? i + 1 : currentPage + i - 3;
                                    if (pageNum < 1 || pageNum > totalPages) return null;

                                    return (
                                        <button
                                            type="button"
                                            key={pageNum}
                                            onClick={() => setCurrentPage(pageNum)}
                                            className={cn(
                                                'w-8 h-8 rounded-lg text-xs font-medium transition-all',
                                                currentPage === pageNum
                                                    ? 'bg-indigo-600 text-white shadow-lg'
                                                    : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white'
                                            )}
                                        >
                                            {pageNum}
                                        </button>
                                    );
                                })}
                            </div>

                            <button
                                type="button"
                                onClick={() => setCurrentPage((p) => p + 1)}
                                disabled={models.length < itemsPerPage}
                                className="p-2 rounded-lg bg-white/5 border border-white/10 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
                            >
                                <ChevronRight size={16} className="text-white" />
                            </button>
                        </div>
                    </div>
                )}
            </motion.div>
        </div>
    );
}
