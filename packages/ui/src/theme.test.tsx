import { describe, expect, test } from 'vitest'
import React from 'react'
import { createRoot } from 'react-dom/client'
import { act } from 'react-dom/test-utils'
import { ThemeProvider, ThemeTokens } from './theme'

function render(theme: ThemeTokens) {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  act(() => {
    root.render(<ThemeProvider theme={theme}><div /></ThemeProvider>)
  })
  return root
}

describe('ThemeProvider', () => {
  test('updates css vars on theme change', () => {
    const rootEl = document.documentElement
    const root = render({ primary: 'red', accent: 'blue', logoURL: 'a.png' })
    expect(rootEl.style.getPropertyValue('--color-primary')).toBe('red')
    expect(rootEl.style.getPropertyValue('--color-accent')).toBe('blue')
    expect(rootEl.style.getPropertyValue('--logo-url')).toBe('url(a.png)')
    act(() => {
      root.render(<ThemeProvider theme={{ primary: 'green', accent: 'orange', logoURL: 'b.png' }}><div /></ThemeProvider>)
    })
    expect(rootEl.style.getPropertyValue('--color-primary')).toBe('green')
    expect(rootEl.style.getPropertyValue('--color-accent')).toBe('orange')
    expect(rootEl.style.getPropertyValue('--logo-url')).toBe('url(b.png)')
  })
})
