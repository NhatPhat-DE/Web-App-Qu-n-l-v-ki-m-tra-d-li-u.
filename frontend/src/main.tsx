import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import SessionApp from './SessionApp'
import { ThemeProvider } from './theme/ThemeContext'
import './workspace/design.css'
import './workspace/demoReference.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <SessionApp />
    </ThemeProvider>
  </StrictMode>
)
