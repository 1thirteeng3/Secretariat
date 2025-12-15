import React, { createContext, useContext, useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';

interface ThemeContextType {
    isHackerMode: boolean;
    toggleHackerMode: () => void;
    reloadTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType>({
    isHackerMode: true,
    toggleHackerMode: () => { },
    reloadTheme: () => { },
});

export const useTheme = () => useContext(ThemeContext);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [isHackerMode, setIsHackerMode] = useState(true);
    const [customCSS, setCustomCSS] = useState("");

    const loadTheme = async () => {
        try {
            const css = await invoke<string>('get_app_theme');
            if (typeof css === 'string') {
                setCustomCSS(css);
            }
        } catch (e) {
            console.error("Failed to load hack.css:", e);
        }
    };

    useEffect(() => {
        // Initial load
        loadTheme();

        // Safety: Global Shortcut (Ctrl+Shift+R) to kill custom theme
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'R') {
                setIsHackerMode(false);
                console.warn("System Override: KILL SWITCH ACTIVATED. Safe Mode Engaged.");
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    useEffect(() => {
        // Inject or Remove CSS
        const styleId = 'system-override-style';
        let styleEl = document.getElementById(styleId);

        if (isHackerMode && customCSS) {
            if (!styleEl) {
                styleEl = document.createElement('style');
                styleEl.id = styleId;
                document.head.appendChild(styleEl);
            }
            styleEl.textContent = customCSS;
        } else {
            if (styleEl) {
                styleEl.remove();
            }
        }
    }, [isHackerMode, customCSS]);

    return (
        <ThemeContext.Provider value={{
            isHackerMode,
            toggleHackerMode: () => setIsHackerMode(prev => !prev),
            reloadTheme: loadTheme
        }}>
            {children}
        </ThemeContext.Provider>
    );
}
