import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

export type ThemePreference = 'system' | 'light' | 'dark' | 'soft'
export type ResolvedTheme = 'light' | 'dark' | 'soft'

export interface ThemeContextValue {
  themePreference: ThemePreference
  resolvedTheme: ResolvedTheme
  setTheme: (theme: ThemePreference) => void
}

const STORAGE_KEY = 'dataguard-theme'

const ThemeContext = createContext<ThemeContextValue | null>(null)

function resolveTheme(pref: ThemePreference): ResolvedTheme {
  if (pref === 'system') {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'light'
  }
  return pref
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themePreference, setThemePreference] = useState<ThemePreference>(() => {
    if (typeof window === 'undefined') return 'system'
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored === 'system' || stored === 'light' || stored === 'dark' || stored === 'soft') {
        return stored
      }
    } catch {
      // Ignore storage access errors
    }
    return 'system'
  })

  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => resolveTheme(themePreference))

  // Synchronize document attributes and listen to system preference changes
  useEffect(() => {
    const active = resolveTheme(themePreference)
    setResolvedTheme(active)

    document.documentElement.setAttribute('data-theme', active)
    document.documentElement.setAttribute('data-theme-preference', themePreference)
    document.documentElement.style.colorScheme = active === 'dark' ? 'dark' : 'light'

    if (themePreference !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const nextResolved = mediaQuery.matches ? 'dark' : 'light'
      setResolvedTheme(nextResolved)
      document.documentElement.setAttribute('data-theme', nextResolved)
      document.documentElement.style.colorScheme = nextResolved === 'dark' ? 'dark' : 'light'
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [themePreference])

  const setTheme = (next: ThemePreference) => {
    setThemePreference(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Ignore storage access errors
    }
  }

  return (
    <ThemeContext.Provider value={{ themePreference, resolvedTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

