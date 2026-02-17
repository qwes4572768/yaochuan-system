import { useEffect, useState, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'
import { authApi } from '../api'
import { ParticleLogo } from '../components/ParticleLogo'
import { TechBackground } from '../components/TechBackground'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, isAuthenticated } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [glitchActive, setGlitchActive] = useState(false)
  const glitchRef = useRef<number>(0)

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/'

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, from])

  useEffect(() => {
    const t = setTimeout(() => {
      const trigger = () => {
        setGlitchActive(true)
        glitchRef.current = window.setTimeout(() => setGlitchActive(false), 120)
      }
      const id = window.setInterval(trigger, 2200)
      return () => {
        clearInterval(id)
        if (glitchRef.current) clearTimeout(glitchRef.current)
      }
    }, 2500)
    return () => clearTimeout(t)
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await authApi.login(username, password)
      const token = data.access_token
      if (!token) {
        throw new Error('Login failed: no token returned')
      }
      localStorage.setItem('access_token', token)
      login(token)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : '登入失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-bg-wrap">
        <TechBackground className="login-bg-canvas" />
      </div>

      <div className="login-content">
        <div className="login-logo-wrap">
          <ParticleLogo width={760} height={280} className="login-particle-logo" />
        </div>
        <p className={`login-secure-hint ${glitchActive ? 'login-glitch-text' : ''}`} aria-hidden>
          SECURE ACCESS / AUTH REQUIRED
        </p>

        <div className="login-card">
          <div className="login-card-glow" />
          <h1 className="login-title">系統登入</h1>
          <p className="login-subtitle">請輸入管理員憑證</p>

          <form onSubmit={handleSubmit} className="login-form">
            <label className="login-label">
              <span className="login-label-text">帳號</span>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="login-input"
                placeholder="username"
                autoComplete="username"
                autoFocus
              />
            </label>
            <label className="login-label">
              <span className="login-label-text">密碼</span>
              <div className="login-input-wrap">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="login-input"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="login-password-toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  title={showPassword ? '隱藏密碼' : '顯示密碼'}
                  aria-label={showPassword ? '隱藏密碼' : '顯示密碼'}
                >
                  {showPassword ? (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" /><line x1="1" y1="1" x2="23" y2="23" /></svg>
                  ) : (
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></svg>
                  )}
                </button>
              </div>
            </label>
            {error && (
              <p className="login-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="login-btn" disabled={loading}>
              {loading ? '驗證中…' : '登入'}
            </button>
          </form>
        </div>
      </div>

      <style>{`
        .login-page {
          min-height: 100vh;
          background: #04060e;
          color: #e2e8f2;
          font-family: 'Noto Sans TC', system-ui, sans-serif;
          position: relative;
          overflow: hidden;
        }
        .login-bg-wrap {
          position: fixed;
          inset: 0;
          z-index: 0;
        }
        .login-bg-canvas {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
        }
        .login-content {
          position: relative;
          z-index: 1;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 2rem 1rem;
        }
        .login-logo-wrap {
          width: min(92vw, 900px);
          margin: 0 auto 0.75rem;
          display: flex;
          justify-content: center;
        }
        .login-particle-logo {
          margin: 0 auto;
          width: 100%;
          height: auto;
          min-height: clamp(180px, 26vw, 280px);
        }
        .login-secure-hint {
          font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
          font-size: 0.7rem;
          letter-spacing: 0.15em;
          color: rgba(0, 255, 170, 0.5);
          margin: 0 0 1.5rem;
          transition: opacity 0.15s;
        }
        .login-glitch-text {
          animation: login-glitch-shift 0.1s ease-out;
          text-shadow: 1px 0 rgba(255,80,120,0.4), -1px 0 rgba(0,255,200,0.4);
        }
        @keyframes login-glitch-shift {
          0% { transform: translate(0); }
          25% { transform: translate(-1px, 1px); }
          50% { transform: translate(1px, -1px); }
          75% { transform: translate(-1px, -1px); }
          100% { transform: translate(0); }
        }
        .login-card {
          position: relative;
          width: 100%;
          max-width: 380px;
          padding: 2rem;
          background: rgba(12, 18, 28, 0.6);
          border: 1px solid rgba(0, 255, 170, 0.18);
          border-radius: 14px;
          box-shadow:
            0 0 50px rgba(0, 255, 170, 0.06),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
        }
        .login-card-glow {
          position: absolute;
          inset: -1px;
          border-radius: 14px;
          background: linear-gradient(135deg,
            rgba(0, 255, 170, 0.12) 0%,
            transparent 45%,
            transparent 55%,
            rgba(100, 150, 255, 0.08) 100%);
          filter: blur(16px);
          opacity: 0.7;
          z-index: -1;
          pointer-events: none;
        }
        .login-title {
          margin: 0 0 0.25rem;
          font-size: 1.35rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          color: #e8eef4;
        }
        .login-subtitle {
          margin: 0 0 1.5rem;
          font-size: 0.8rem;
          font-family: 'JetBrains Mono', Consolas, monospace;
          color: rgba(180, 210, 255, 0.7);
          letter-spacing: 0.05em;
        }
        .login-form {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .login-label {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }
        .login-label-text {
          font-size: 0.75rem;
          font-family: 'JetBrains Mono', Consolas, monospace;
          color: rgba(0, 255, 170, 0.85);
          letter-spacing: 0.06em;
        }
        .login-input-wrap {
          position: relative;
        }
        .login-input {
          width: 100%;
          padding: 0.7rem 2.5rem 0.7rem 0.9rem;
          font-family: inherit;
          font-size: 0.95rem;
          color: #e2e8f2;
          background: rgba(6, 12, 22, 0.75);
          border: 1px solid rgba(0, 255, 170, 0.22);
          border-radius: 8px;
          outline: none;
          transition: border-color 0.2s, box-shadow 0.2s;
        }
        .login-input-wrap .login-input {
          padding-right: 2.5rem;
        }
        .login-input::placeholder {
          color: rgba(160, 190, 220, 0.4);
        }
        .login-input:focus {
          border-color: rgba(0, 255, 170, 0.5);
          box-shadow: 0 0 0 2px rgba(0, 255, 170, 0.12);
        }
        .login-password-toggle {
          position: absolute;
          right: 0.5rem;
          top: 50%;
          transform: translateY(-50%);
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: none;
          border: none;
          color: rgba(180, 210, 255, 0.5);
          cursor: pointer;
          border-radius: 6px;
          transition: color 0.2s, background 0.2s;
        }
        .login-password-toggle:hover {
          color: rgba(0, 255, 170, 0.8);
          background: rgba(255, 255, 255, 0.05);
        }
        .login-error {
          margin: 0;
          font-size: 0.8rem;
          color: rgba(220, 140, 140, 0.95);
          background: rgba(180, 80, 80, 0.12);
          padding: 0.5rem 0.75rem;
          border-radius: 6px;
          border: 1px solid rgba(200, 100, 100, 0.2);
        }
        .login-btn {
          margin-top: 0.5rem;
          padding: 0.8rem 1.25rem;
          font-family: inherit;
          font-size: 0.95rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          color: #050a12;
          background: linear-gradient(135deg, #00ffaa 0%, #00cc88 100%);
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: transform 0.15s, box-shadow 0.2s, opacity 0.2s;
          box-shadow: 0 0 24px rgba(0, 255, 170, 0.25);
        }
        .login-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 0 32px rgba(0, 255, 170, 0.4);
        }
        .login-btn:active:not(:disabled) {
          transform: translateY(0);
        }
        .login-btn:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  )
}
