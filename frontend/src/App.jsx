import { useState } from 'react'
import { AuthForm } from './components/AuthForm'
import { useCallback } from 'react'
import { Projects } from './components/Projects'
import './App.css'

export default function App() {
  const [session, setSession] = useState(null)
  const [hasUnsaved, setHasUnsaved] = useState(false)
  const [isEditing, setIsEditing] = useState(false)

  const logout = useCallback(() => {
    if (hasUnsaved && !window.confirm('Hay cambios sin guardar en el diagrama. ¿Cerrar sesión y descartarlos?')) return
    setHasUnsaved(false)
    setSession(null)
    setIsEditing(false)
  }, [hasUnsaved])

  if (!session) {
    return <AuthForm onLogin={setSession} />
  }

  return (
    <div className={`min-h-screen bg-surface flex flex-col font-sans ${isEditing ? 'h-screen overflow-hidden' : ''}`}>
      {!isEditing && (
        <header className="h-14 px-6 bg-primary-container text-on-primary flex items-center justify-between border-b border-inverse-surface/50 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-secondary text-on-secondary flex items-center justify-center shadow-sm">
              <span className="material-symbols-outlined text-[20px]">account_tree</span>
            </div>
            <div>
              <span className="font-label-caps text-[9px] text-secondary-fixed font-bold tracking-wider block">
                PLATAFORMA CASE
              </span>
              <span className="font-headline-sm text-sm font-bold text-on-primary leading-none">
                UML Studio 2.5
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-high/15 border border-surface-container-high/20 text-xs font-code-sm text-surface-variant">
              <span className="w-2 h-2 rounded-full bg-secondary"></span>
              <span>{session.user.full_name}</span>
            </div>
            <button
              type="button"
              onClick={logout}
              className="px-3 py-1 bg-surface-container-high/10 hover:bg-error hover:text-on-error text-surface-variant rounded text-xs transition-colors flex items-center gap-1 border border-outline-variant/30"
              title="Cerrar sesión"
            >
              <span className="material-symbols-outlined text-[15px]">logout</span>
              <span>Cerrar sesión</span>
            </button>
          </div>
        </header>
      )}
      <main className={isEditing ? 'flex-1 h-full w-full p-0 overflow-hidden' : 'max-w-6xl w-full mx-auto p-6 flex-1'}>
        <Projects
          user={session.user}
          token={session.token}
          onExpired={logout}
          onDirtyChange={setHasUnsaved}
          onEditingChange={setIsEditing}
        />
      </main>
    </div>
  )
}
