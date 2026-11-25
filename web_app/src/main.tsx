import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { uebungBasis, sperreEinrichten } from './uebung.ts'

// kaiscribe-uebung-n1: im Übungsmodus VOR dem ersten Render alle Ausgänge sperren (Zwischenablage, fremde Ziele …)
const uebung = uebungBasis(window.location.href)
if (uebung) sperreEinrichten(window as unknown as Record<string, unknown>, uebung)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
