import React from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "danger" | "ghost";
    isLoading?: boolean;
}

export function Button({
    children,
    variant = "primary",
    isLoading,
    className = "",
    ...props
}: ButtonProps) {

    const baseStyles = "px-6 py-3 font-mono text-sm tracking-wider uppercase transition-all active:translate-y-1 active:shadow-none border-2";

    const variants = {
        primary: "bg-[#f97316] text-black border-[#f97316] shadow-[4px_4px_0px_0px_#000] hover:translate-y-[-2px] hover:shadow-[6px_6px_0px_0px_#000]",
        secondary: "bg-slate-800 text-slate-200 border-slate-700 shadow-[4px_4px_0px_0px_#000] hover:bg-slate-700",
        danger: "bg-red-600 text-white border-red-600 shadow-[4px_4px_0px_0px_#000]",
        ghost: "bg-transparent text-slate-400 border-transparent hover:text-white hover:bg-slate-800/50"
    };

    return (
        <button
            disabled={isLoading || props.disabled}
            className={`${baseStyles} ${variants[variant]} ${isLoading ? "opacity-70 cursor-not-allowed" : ""} ${className}`}
            {...props}
        >
            <div className="flex items-center justify-center space-x-2">
                {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>{children}</span>
            </div>
        </button>
    );
}
