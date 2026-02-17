import { useRef, useEffect } from 'react'

const NET_PARTICLE_COUNT = 55
const NET_CONNECT_DIST = 140
const DATA_STREAM_COUNT = 12
const CHARS = '01ABCDEFabcdef0123456789'

type NetDot = { x: number; y: number; vx: number; vy: number }
type StreamItem = { x: number; y: number; w: number; h: number; speed: number; char: string; opacity: number }

export function TechBackground({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const noiseRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const noiseCanvas = noiseRef.current
    if (!canvas || !noiseCanvas) return

    const ctx = canvas.getContext('2d')
    const noiseCtx = noiseCanvas.getContext('2d')
    if (!ctx || !noiseCtx) return

    const dots: NetDot[] = []
    const streamItems: StreamItem[] = []
    const NOISE_W = 256
    const NOISE_H = 144
    let w = 0
    let h = 0

    const init = () => {
      w = window.innerWidth
      h = window.innerHeight
      dots.length = 0
      for (let i = 0; i < NET_PARTICLE_COUNT; i++) {
        dots.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.4,
          vy: (Math.random() - 0.5) * 0.4,
        })
      }
      streamItems.length = 0
      for (let i = 0; i < DATA_STREAM_COUNT; i++) {
        streamItems.push({
          x: Math.random() * w,
          y: Math.random() * h,
          w: 3 + Math.random() * 4,
          h: 8 + Math.random() * 20,
          speed: 0.3 + Math.random() * 0.5,
          char: CHARS[Math.floor(Math.random() * CHARS.length)],
          opacity: 0.08 + Math.random() * 0.08,
        })
      }
    }

    let raf = 0
    const resize = () => {
      w = window.innerWidth
      h = window.innerHeight
      canvas.width = w
      canvas.height = h
      noiseCanvas.width = NOISE_W
      noiseCanvas.height = NOISE_H
      if (dots.length === 0) init()
    }

    const draw = () => {
      if (!ctx || !canvas) return

      ctx.fillStyle = 'rgba(4, 6, 14, 0.25)'
      ctx.fillRect(0, 0, w, h)

      dots.forEach((d) => {
        d.x += d.vx
        d.y += d.vy
        if (d.x < 0 || d.x > w) d.vx *= -1
        if (d.y < 0 || d.y > h) d.vy *= -1
      })

      ctx.strokeStyle = 'rgba(0, 255, 170, 0.06)'
      ctx.lineWidth = 0.5
      for (let i = 0; i < dots.length; i++) {
        for (let j = i + 1; j < dots.length; j++) {
          const dx = dots[i].x - dots[j].x
          const dy = dots[i].y - dots[j].y
          if (dx * dx + dy * dy < NET_CONNECT_DIST * NET_CONNECT_DIST) {
            ctx.beginPath()
            ctx.moveTo(dots[i].x, dots[i].y)
            ctx.lineTo(dots[j].x, dots[j].y)
            ctx.stroke()
          }
        }
      }

      ctx.fillStyle = 'rgba(0, 255, 170, 0.2)'
      dots.forEach((d) => {
        ctx.beginPath()
        ctx.arc(d.x, d.y, 1.2, 0, Math.PI * 2)
        ctx.fill()
      })

      const t = performance.now() * 0.001
      ctx.fillStyle = 'rgba(100, 200, 255, 0.06)'
      ctx.font = '11px "JetBrains Mono", monospace'
      streamItems.forEach((s) => {
        s.y += s.speed
        if (s.y > h + 20) {
          s.y = -20
          s.x = Math.random() * w
        }
        ctx.globalAlpha = s.opacity * (0.7 + 0.3 * Math.sin(t + s.x * 0.01))
        ctx.fillText(s.char, s.x, s.y)
      })
      ctx.globalAlpha = 1

      raf = requestAnimationFrame(draw)
    }

    const drawNoise = () => {
      if (!noiseCtx || !noiseCanvas) return
      const id = noiseCtx.getImageData(0, 0, NOISE_W, NOISE_H)
      const d = id.data
      for (let i = 0; i < d.length; i += 4) {
        const v = Math.random() * 8
        d[i] = d[i + 1] = d[i + 2] = v
        d[i + 3] = 2
      }
      noiseCtx.putImageData(id, 0, 0)
    }

    resize()
    window.addEventListener('resize', resize)
    draw()
    const noiseInterval = setInterval(drawNoise, 120)

    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(raf)
      clearInterval(noiseInterval)
    }
  }, [])

  return (
    <>
      <canvas
        ref={canvasRef}
        className={className}
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block' }}
        aria-hidden
      />
      <canvas
        ref={noiseRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          display: 'block',
          pointerEvents: 'none',
          opacity: 0.35,
          objectFit: 'cover',
        }}
        aria-hidden
      />
      <div
        className="tech-scanline"
        aria-hidden
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          background: 'repeating-linear-gradient(0deg, transparent 0px, transparent 2px, rgba(0,255,170,0.03) 2px, rgba(0,255,170,0.03) 4px)',
          animation: 'tech-scan 10s linear infinite',
        }}
      />
      <style>{`
        @keyframes tech-scan {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }
      `}</style>
    </>
  )
}
