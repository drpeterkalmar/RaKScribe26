// useLatest (Umbau Schritt 19, Gutachten P2-15): immer aktueller Wert für Event-Handler außerhalb von React
// (globale Tasten F10/F9, Drag & Drop), ohne die Ref während des Renderns zu beschreiben (react-hooks/refs).
import { useLayoutEffect, useRef } from 'react';

export function useLatest<T>(value: T) {
  const ref = useRef(value);
  useLayoutEffect(() => {
    ref.current = value;
  });
  return ref;
}
