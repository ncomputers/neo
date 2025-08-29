import { PropsWithChildren, useEffect } from 'react'

import { colors } from './tokens'

export interface ThemeTokens {
  primary: string
  accent: string
  logoURL: string
}

export function tokensFromOutlet(outlet: any): ThemeTokens {
  const theme = outlet?.theme ?? {}
  return {
    primary: theme.primary ?? colors.primary,
    accent: theme.accent ?? colors.secondary,
    logoURL: theme.logoURL ?? ''
  }
}

export function ThemeProvider({ theme, children }: PropsWithChildren<{ theme: ThemeTokens }>) {
  useEffect(() => {
    const root = document.documentElement
    root.style.setProperty('--color-primary', theme.primary)
    root.style.setProperty('--color-accent', theme.accent)
    root.style.setProperty('--color-secondary', theme.accent)
    root.style.setProperty('--logo-url', theme.logoURL ? `url(${theme.logoURL})` : '')
  }, [theme])

  return <>{children}</>
}
