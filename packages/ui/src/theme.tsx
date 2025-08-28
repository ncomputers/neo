import React, { createContext, useContext, useEffect } from 'react';

export interface ThemeTokens {
  primary: string;
  accent: string;
  logoURL?: string;
}

const defaultTheme: ThemeTokens = {
  primary: '#2563eb',
  accent: '#64748b',
  logoURL: undefined
};

const ThemeContext = createContext<ThemeTokens>(defaultTheme);

export function tokensFromOutlet(outlet: any): ThemeTokens {
  return {
    primary: outlet?.theme?.primary || defaultTheme.primary,
    accent: outlet?.theme?.accent || defaultTheme.accent,
    logoURL: outlet?.theme?.logoURL || defaultTheme.logoURL
  };
}

export function ThemeProvider({ theme, children }: { theme: ThemeTokens; children: React.ReactNode }) {
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--color-primary', theme.primary);
    root.style.setProperty('--color-accent', theme.accent);
  }, [theme.primary, theme.accent]);
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}

