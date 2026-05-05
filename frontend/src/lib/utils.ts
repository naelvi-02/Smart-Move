import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export function formatNumber(num: number | null | undefined) {
    if (!num) return "0";
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
}

export function formatCurrency(amount: number | null | undefined) {
    if (!amount) return "$0.00";
    if (amount < 0.01) return `$${amount.toFixed(6)}`;
    if (amount < 1) return `$${amount.toFixed(4)}`;
    return `$${amount.toFixed(2)}`;
}
