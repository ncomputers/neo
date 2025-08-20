import { createContext, useContext, useEffect, useState } from 'react'

const ThemeContext = createContext()

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState({
    logo: '',
    colors: { primary: '#0ea5e9' },
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme.colors?.primary) {
      root.style.setProperty('--color-primary', theme.colors.primary)
    }
  }, [theme])

  return (
    <ThemeContext.Provider value={{ ...theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
