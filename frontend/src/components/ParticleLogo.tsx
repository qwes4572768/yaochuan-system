import { useRef, useEffect, useState, useCallback } from 'react'

const LOGO_SRC = '/logo.png'
const SAMPLE_STEP = 3
const ALPHA_THRESHOLD = 150
const FLY_DURATION_MS = 1000
const BREATH_AMP = 0.28
const MOUSE_RADIUS = 46
const MOUSE_STRENGTH = 10
const PARTICLE_RADIUS = 2
const PARTICLE_ALPHA = 1
const TARGET_FPS = 60

type Particle = {
  tx: number
  ty: number
  sx: number
  sy: number
  x: number
  y: number
  r: number
  r0: number
  g: number
  b: number
  a: number
  flyPhase: number
  seed: number
}

export function ParticleLogo({ className, width = 760, height = 280 }: { className?: string; width?: number; height?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const imgLoadedRef = useRef(false)
  const startTimeRef = useRef<number>(0)
  const lastFrameTimeRef = useRef(0)
  const [mouse, setMouse] = useState<{ x: number; y: number } | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const initParticles = useCallback((img: HTMLImageElement) => {
    const w = img.naturalWidth
    const h = img.naturalHeight
    const off = document.createElement('canvas')
    off.width = w
    off.height = h
    const ctx = off.getContext('2d')
    if (!ctx) return
    ctx.drawImage(img, 0, 0)
    const data = ctx.getImageData(0, 0, w, h).data
    const out: Particle[] = []
    const logoAspect = w / h
    const boxAspect = width / height
    const drawW = logoAspect > boxAspect ? width : height * logoAspect
    const drawH = logoAspect > boxAspect ? width / logoAspect : height
    const offsetX = (width - drawW) * 0.5
    const offsetY = (height - drawH) * 0.5
    for (let y = 0; y < h; y += SAMPLE_STEP) {
      for (let x = 0; x < w; x += SAMPLE_STEP) {
        const i = (y * w + x) * 4
        const a = data[i + 3]
        if (a < ALPHA_THRESHOLD) continue
        const tx = offsetX + (x / w) * drawW
        const ty = offsetY + (y / h) * drawH
        const angle = Math.random() * Math.PI * 2
        const dist = 30 + Math.random() * Math.max(drawW, drawH) * 0.48
        const sx = width / 2 + Math.cos(angle) * dist
        const sy = height / 2 + Math.sin(angle) * dist
        out.push({
          tx,
          ty,
          sx,
          sy,
          x: sx,
          y: sy,
          r: PARTICLE_RADIUS,
          r0: data[i] / 255,
          g: data[i + 1] / 255,
          b: data[i + 2] / 255,
          a: PARTICLE_ALPHA,
          flyPhase: Math.random(),
          seed: Math.random() * Math.PI * 2,
        })
      }
    }
    particlesRef.current = out
    console.info(`[ParticleLogo] particles: ${out.length}`)
  }, [width, height])

  useEffect(() => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      initParticles(img)
      imgLoadedRef.current = true
      startTimeRef.current = performance.now()
    }
    img.onerror = () => {
      imgLoadedRef.current = true
      startTimeRef.current = performance.now()
    }
    img.src = LOGO_SRC
  }, [initParticles])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    const handleResize = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1)
      canvas.width = Math.floor(width * dpr)
      canvas.height = Math.floor(height * dpr)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const getLocalMouse = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      if (rect.width === 0) return { x: 0, y: 0 }
      const scaleX = width / rect.width
      const scaleY = height / rect.height
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY,
      }
    }

    const onMouseMove = (e: MouseEvent) => setMouse(getLocalMouse(e))
    const onMouseLeave = () => setMouse(null)

    container.addEventListener('mousemove', onMouseMove)
    container.addEventListener('mouseleave', onMouseLeave)
    handleResize()
    window.addEventListener('resize', handleResize)

    const draw = (now: number) => {
      const frameInterval = 1000 / TARGET_FPS
      if (now - lastFrameTimeRef.current < frameInterval) {
        raf = requestAnimationFrame(draw)
        return
      }
      lastFrameTimeRef.current = now
      const t = (now - startTimeRef.current) / 1000
      const elapsed = now - startTimeRef.current
      const flyProgress = Math.min(1, elapsed / FLY_DURATION_MS)
      const ease = 1 - Math.pow(1 - flyProgress, 2)

      ctx.clearRect(0, 0, width, height)
      const particles = particlesRef.current
      if (!particles.length) {
        raf = requestAnimationFrame(draw)
        return
      }

      const mx = mouse?.x ?? -9999
      const my = mouse?.y ?? -9999

      particles.forEach((p) => {
        const distToMouse = Math.hypot(p.x - mx, p.y - my)
        const inRange = distToMouse < MOUSE_RADIUS && mouse !== null

        if (flyProgress < 1) {
          p.x = p.sx + (p.tx - p.sx) * ease
          p.y = p.sy + (p.ty - p.sy) * ease
        } else {
          if (inRange) {
            const angle = Math.atan2(p.y - my, p.x - mx)
            const force = (1 - distToMouse / MOUSE_RADIUS) * MOUSE_STRENGTH
            p.x += Math.cos(angle) * force
            p.y += Math.sin(angle) * force
          } else {
            const breathX = Math.sin(t * 1.2 + p.seed) * BREATH_AMP
            const breathY = Math.sin(t * 0.9 + p.seed * 2) * BREATH_AMP * 0.5
            const targetX = p.tx + breathX
            const targetY = p.ty + breathY
            p.x += (targetX - p.x) * 0.22
            p.y += (targetY - p.y) * 0.22
          }
        }

        ctx.fillStyle = `rgba(${Math.round(p.r0 * 255)}, ${Math.round(p.g * 255)}, ${Math.round(p.b * 255)}, ${p.a})`
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fill()
      })

      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)

    return () => {
      container.removeEventListener('mousemove', onMouseMove)
      container.removeEventListener('mouseleave', onMouseLeave)
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(raf)
    }
  }, [mouse, width, height])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: '100%', maxWidth: width, aspectRatio: `${width} / ${height}`, position: 'relative' }}
      aria-hidden
    >
      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%', display: 'block' }}
        width={width}
        height={height}
      />
    </div>
  )
}
