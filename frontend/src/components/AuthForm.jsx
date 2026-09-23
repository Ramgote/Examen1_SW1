import { useState } from 'react'
import { api } from '../api'

export function AuthForm({ onLogin }) {
  const [register, setRegister] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    const fields = Object.fromEntries(new FormData(event.currentTarget))
    try {
      if (register) await api('/auth/register', { method: 'POST', body: fields })
      const { access_token: token } = await api('/auth/login', { method: 'POST', body: { email: fields.email, password: fields.password } })
      const user = await api('/auth/me', { token })
      onLogin({ token, user })
    } catch (err) {
      setError(err.message || 'Error al autenticar. Por favor verifica tus credenciales.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-center items-center p-4 relative select-none">
      {/* Fondo de micropuntos CASE */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-40" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="auth-grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1" className="fill-surface-tint opacity-30"></circle>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#auth-grid)"></rect>
      </svg>

      <div className="w-full max-w-md bg-surface-container-lowest border border-outline-variant/60 rounded-xl shadow-xl p-8 relative z-10">
        {/* Cabecera del Brand */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-primary-container text-secondary-fixed flex items-center justify-center mb-3 shadow-sm">
            <span className="material-symbols-outlined text-[28px]">account_tree</span>
          </div>
          <span className="font-label-caps text-label-caps text-secondary font-bold tracking-widest uppercase">
            Plataforma Colaborativa CASE
          </span>
          <h1 className="font-headline-lg text-headline-lg text-on-surface font-bold mt-1">
            UML Studio 2.5
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-1 max-w-xs">
            Modelado UML asistido por IA multimodal, intercambio XMI y generación Spring Boot / Flutter
          </p>
        </div>

        {/* Selector de modo Pestañas */}
        <div className="flex rounded-lg bg-surface-container-low p-1 mb-6 border border-outline-variant/40">
          <button
            type="button"
            className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
              !register
                ? 'bg-surface-container-lowest text-on-surface shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
            onClick={() => { setRegister(false); setError('') }}
          >
            Iniciar sesión
          </button>
          <button
            type="button"
            className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
              register
                ? 'bg-surface-container-lowest text-on-surface shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
            onClick={() => { setRegister(true); setError('') }}
          >
            Crear cuenta
          </button>
        </div>

        {/* Mensaje de Error */}
        {error && (
          <div
            role="alert"
            className="mb-5 p-3 rounded-lg bg-error-container text-on-error-container border-l-4 border-error text-xs flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-error text-[18px]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* Formulario */}
        <form onSubmit={submit} className="flex flex-col gap-4">
          {register && (
            <div className="flex flex-col gap-1">
              <label className="font-body-sm text-body-sm font-medium text-on-surface">
                Nombre completo
              </label>
              <div className="relative flex items-center">
                <span className="material-symbols-outlined absolute left-3 text-on-surface-variant text-[18px]">
                  person
                </span>
                <input
                  name="full_name"
                  type="text"
                  autoComplete="name"
                  required
                  maxLength={150}
                  placeholder="Ej. Ramiro Gonzales"
                  className="w-full pl-9 pr-3 py-2 bg-surface-container-low border border-outline-variant/70 rounded-lg text-on-surface text-xs focus:ring-2 focus:ring-secondary focus:bg-surface-container-lowest outline-none transition-all"
                />
              </div>
            </div>
          )}

          <div className="flex flex-col gap-1">
            <label className="font-body-sm text-body-sm font-medium text-on-surface">
              Correo electrónico
            </label>
            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-3 text-on-surface-variant text-[18px]">
                mail
              </span>
              <input
                name="email"
                type="email"
                autoComplete="username"
                required
                maxLength={255}
                placeholder="usuario@ejemplo.com"
                className="w-full pl-9 pr-3 py-2 bg-surface-container-low border border-outline-variant/70 rounded-lg text-on-surface text-xs focus:ring-2 focus:ring-secondary focus:bg-surface-container-lowest outline-none transition-all"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="font-body-sm text-body-sm font-medium text-on-surface">
              Contraseña
            </label>
            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-3 text-on-surface-variant text-[18px]">
                lock
              </span>
              <input
                name="password"
                type="password"
                autoComplete={register ? 'new-password' : 'current-password'}
                required
                minLength={8}
                maxLength={72}
                placeholder="Mínimo 8 caracteres"
                className="w-full pl-9 pr-3 py-2 bg-surface-container-low border border-outline-variant/70 rounded-lg text-on-surface text-xs focus:ring-2 focus:ring-secondary focus:bg-surface-container-lowest outline-none transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full mt-2 py-2.5 bg-secondary hover:bg-secondary-container text-on-secondary font-semibold rounded-lg text-xs shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-wait"
          >
            {busy ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                <span>Procesando…</span>
              </>
            ) : register ? (
              <>
                <span className="material-symbols-outlined text-[18px]">person_add</span>
                <span>Registrar cuenta</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px]">login</span>
                <span>Acceder a la plataforma</span>
              </>
            )}
          </button>
        </form>

        {/* Footer del card */}
        <div className="mt-6 pt-4 border-t border-outline-variant/40 text-center">
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            {register ? '¿Ya tienes una cuenta?' : '¿Aún no tienes cuenta?'}
            <button
              type="button"
              className="ml-1 text-secondary font-semibold hover:underline bg-transparent p-0 inline border-0 cursor-pointer"
              onClick={() => { setRegister(!register); setError('') }}
            >
              {register ? 'Inicia sesión aquí' : 'Crea una gratis'}
            </button>
          </p>
        </div>
      </div>

      {/* Feature tags inferiores */}
      <div className="mt-6 flex flex-wrap justify-center items-center gap-4 text-on-surface-variant text-[11px] font-code-sm text-code-sm relative z-10">
        <span className="flex items-center gap-1">
          <span className="material-symbols-outlined text-secondary text-[14px]">bolt</span>
          Generación Spring Boot
        </span>
        <span>•</span>
        <span className="flex items-center gap-1">
          <span className="material-symbols-outlined text-secondary text-[14px]">group</span>
          Colaboración WebSocket
        </span>
        <span>•</span>
        <span className="flex items-center gap-1">
          <span className="material-symbols-outlined text-secondary text-[14px]">smart_toy</span>
          Asistente Gemini IA
        </span>
        <span>•</span>
        <span className="flex items-center gap-1">
          <span className="material-symbols-outlined text-secondary text-[14px]">sync_alt</span>
          XMI EA 17.0
        </span>
      </div>
    </div>
  )
}
