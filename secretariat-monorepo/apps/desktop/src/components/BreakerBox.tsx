import { Zap, RefreshCw } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

export function BreakerBox() {
    const { isHackerMode, toggleHackerMode, reloadTheme } = useTheme();

    return (
        <div className="fixed bottom-4 left-4 z-50 group">
            <div className="bg-slate-900 border border-slate-700 p-2 rounded-lg shadow-2xl flex items-center space-x-2 transition-all opacity-50 hover:opacity-100">
                <div className="p-2 bg-slate-950 border border-slate-800 rounded">
                    <Zap className={`w-4 h-4 ${isHackerMode ? "text-green-500" : "text-slate-600"}`} />
                </div>

                <div className="hidden group-hover:flex items-center space-x-2 animate-in slide-in-from-left-2">
                    <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">System Override</span>

                    <button
                        onClick={toggleHackerMode}
                        className={`w-8 h-4 rounded-full transition-colors flex items-center ${isHackerMode ? "bg-green-900" : "bg-slate-700"}`}
                    >
                        <div className={`w-3 h-3 rounded-full bg-white shadow-sm transform transition-transform ${isHackerMode ? "translate-x-4 bg-green-400" : "translate-x-1"}`} />
                    </button>

                    <button onClick={reloadTheme} className="p-1 hover:bg-slate-800 rounded">
                        <RefreshCw className="w-3 h-3 text-slate-500" />
                    </button>
                </div>

                {isHackerMode && (
                    <div className="absolute -top-2 -right-2 w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                )}
            </div>
        </div>
    );
}
