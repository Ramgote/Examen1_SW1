import { useEffect, useRef, useState } from 'react'
import { createSpeechPlayer } from './speechPlayer'

export function useAssistantSpeech(visible) {
  const [enabled, setEnabled] = useState(false)
  const enabledRef = useRef(false)
  const [speaking, setSpeaking] = useState(false)
  const [error, setError] = useState('')
  const supported = typeof window.speechSynthesis !== 'undefined' && typeof window.SpeechSynthesisUtterance !== 'undefined'
  const [player] = useState(() => createSpeechPlayer(window.speechSynthesis, window.SpeechSynthesisUtterance, setSpeaking, setError))
  useEffect(() => () => player.stop(), [player, visible])
  function speak(text) {
    if (enabledRef.current && visible) { setError(''); player.speak(text) }
  }
  function enable(text) {
    enabledRef.current = true
    setEnabled(true)
    setError('')
    if (visible) player.speak(text)
  }
  function disable() {
    enabledRef.current = false
    setEnabled(false)
    player.stop()
  }
  return { enabled, speaking, error, supported, speak, enable, disable, stop: player.stop }
}
