'use client';

import {
    LayoutDashboard,
    BrainCircuit,
    Image as ImageIcon,
    BarChart3,
    Calculator,
    Zap,
    Settings,
    Menu
} from 'lucide-react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useState } from 'react';

const menuItems = [
    { href: '/', icon: LayoutDashboard, label: 'Dashboard', color: 'text-blue-400' },
    { href: '/llm-explorer', icon: BrainCircuit, label: 'LLM Explorer', color: 'text-violet-400' },
    { href: '/image-explorer', icon: ImageIcon, label: 'Image Models', color: 'text-pink-400' },
    { href: '/benchmarks', icon: BarChart3, label: 'Benchmarks', color: 'text-emerald-400' },
    { href: '/cost-simulator', icon: Calculator, label: 'Cost Simulator', color: 'text-amber-400' },
];

export default function Sidebar() {
    const pathname = usePathname();
    const [isCollapsed, setIsCollapsed] = useState(false);

    return (
        <motion.aside
            initial={false}
            animate={{ width: isCollapsed ? 80 : 280 }}
            className="fixed left-0 top-0 h-screen z-50 flex flex-col border-r border-[#ffffff0a] bg-[#030305]/95 backdrop-blur-xl"
        >
            {/* Brand Header */}
            <div className="h-20 flex items-center px-6 border-b border-[#ffffff05]">
                <div className="flex items-center gap-3 overflow-hidden">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(99,102,241,0.5)]">
                        <Zap className="w-5 h-5 text-white fill-white" />
                    </div>
                    {!isCollapsed && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="whitespace-nowrap"
                        >
                            <h1 className="font-bold text-lg text-white tracking-tight">Smart Move</h1>
                            <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Intelligence</p>
                        </motion.div>
                    )}
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-6 px-3 space-y-1">
                {!isCollapsed && (
                    <p className="text-[10px] font-semibold text-slate-600 uppercase tracking-widest px-4 mb-2">
                        Main Menu
                    </p>
                )}

                {menuItems.map((item) => {
                    const isActive = pathname === item.href;

                    return (
                        <Link key={item.href} href={item.href} className="block group">
                            <div
                                className={cn(
                                    "relative flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-300 mx-1",
                                    isActive
                                        ? "bg-white/[0.03] text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.05)]"
                                        : "text-slate-400 hover:text-white hover:bg-white/[0.02]"
                                )}
                            >
                                {/* Active Glow Indicator */}
                                {isActive && (
                                    <motion.div
                                        layoutId="activeTab"
                                        className="absolute inset-0 bg-gradient-to-r from-indigo-500/10 to-transparent rounded-xl"
                                        initial={false}
                                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                    />
                                )}

                                {isActive && (
                                    <div className="absolute left-0 w-1 h-8 bg-indigo-500 rounded-r-full shadow-[0_0_10px_#6366f1]" />
                                )}

                                <div className={cn("relative z-10 w-9 h-9 flex items-center justify-center rounded-lg transition-colors", isActive ? "bg-[#ffffff05]" : "")}>
                                    <item.icon className={cn("w-5 h-5 transition-colors", isActive ? item.color : "group-hover:text-white")} strokeWidth={isActive ? 2.5 : 2} />
                                </div>

                                {!isCollapsed && (
                                    <motion.span
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className={cn("relative z-10 text-sm font-medium", isActive ? "text-white" : "")}
                                    >
                                        {item.label}
                                    </motion.span>
                                )}
                            </div>
                        </Link>
                    );
                })}
            </nav>

            {/* Footer / System Status */}
            <div className="p-4 border-t border-[#ffffff05]">
                <div className={cn(
                    "rounded-xl bg-emerald-500/5 border border-emerald-500/10 flex items-center gap-3 overflow-hidden transition-all",
                    isCollapsed ? "p-2 justify-center" : "p-3"
                )}>
                    <div className="relative shrink-0">
                        <div className="w-2 h-2 bg-emerald-500 rounded-full" />
                        <div className="absolute inset-0 bg-emerald-500 rounded-full animate-ping opacity-75" />
                    </div>

                    {!isCollapsed && (
                        <div className="overflow-hidden">
                            <p className="text-xs font-medium text-emerald-400">System Online</p>
                            <p className="text-[10px] text-emerald-500/60 truncate">v1.2.0 • Stable</p>
                        </div>
                    )}
                </div>
            </div>
        </motion.aside>
    );
}
