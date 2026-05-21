'use client'

import { useEffect, useRef, useState } from 'react'

// Type definition for iframe-resizer library
interface IFrameResizerOptions {
  checkOrigin: boolean
  log: boolean
  warningTimeout?: number
}

interface WindowWithIFrameResize extends Window {
  iFrameResize?: (options: IFrameResizerOptions, selector: string) => void
}

/**
 * SoftrHero Component
 * 
 * Displays a Softr embedded hero section for non-authenticated users.
 * Uses iframe-resizer to automatically adjust iframe height based on content.
 */
export default function SoftrHero() {
  const hostRef = useRef<HTMLDivElement | null>(null)
  const [shouldLoad, setShouldLoad] = useState(false)

  useEffect(() => {
    const host = hostRef.current
    if (!host) {
      return
    }
    if (!('IntersectionObserver' in window)) {
      setShouldLoad(true)
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setShouldLoad(true)
          observer.disconnect()
        }
      },
      { rootMargin: '320px' }
    )
    observer.observe(host)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!shouldLoad) {
      return
    }
    const script = document.createElement('script')
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/iframe-resizer/4.2.11/iframeResizer.min.js'
    script.async = true
    
    script.onload = () => {
      // Initialize iFrameResize after script loads
      const win = window as WindowWithIFrameResize
      if (typeof window !== 'undefined' && win.iFrameResize) {
        win.iFrameResize(
          { 
            checkOrigin: false, 
            log: false,
            warningTimeout: 0,
          }, 
          '#softr-594e1786-4514-4322-984e-9376ef328935-hero-public'
        )
      }
    }

    document.body.appendChild(script)

    // Cleanup
    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script)
      }
    }
  }, [shouldLoad])

  return (
    <div ref={hostRef} className="w-full">
      {shouldLoad ? (
        <iframe
          id="softr-594e1786-4514-4322-984e-9376ef328935-hero-public"
          src="https://codecraft-tobias14981.softr.app/embed/pages/594e1786-4514-4322-984e-9376ef328935/blocks/hero-public"
          width="100%"
          height="1000"
          loading="lazy"
          scrolling="no"
          frameBorder="0"
          style={{ border: 'none' }}
          title="Softr Hero Section"
        />
      ) : (
        <div className="min-h-[640px]" aria-hidden="true" />
      )}
    </div>
  )
}
