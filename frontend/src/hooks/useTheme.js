import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "ehr-explorer-theme";

export function useTheme() {
  const [theme, setThemeState] = useState(() => {
    if (typeof window === "undefined") return "light";
    return localStorage.getItem(STORAGE_KEY) || "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const setTheme = useCallback((next) => {
    setThemeState(next);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  return { theme, setTheme, toggleTheme, isDark: theme === "dark" };
}
