'use client'

import { useEffect } from 'react'

/**
 * SoftrHero Component
 * 
 * Displays a Softr embedded hero section for non-authenticated users.
 * Uses iframe-resizer to automatically adjust iframe height based on content.
 */
export default function SoftrHero() {
  useEffect(() => {
    // Dynamically load iframe-resizer script
    const script = document.createElement('script')
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/iframe-resizer/4.2.11/iframeResizer.min.js'
    script.async = true
    
    script.onload = () => {
      // Initialize iFrameResize after script loads
      if (typeof window !== 'undefined' && (window as any).iFrameResize) {
        (window as any).iFrameResize(
          { 
            checkOrigin: false, 
            log: true 
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
  }, [])

  return (
    <div className="w-full">
      <iframe
        id="softr-594e1786-4514-4322-984e-9376ef328935-hero-public"
        src="https://codecraft-tobias14981.softr.app/embed/pages/594e1786-4514-4322-984e-9376ef328935/blocks/hero-public"
        width="100%"
        height="1000"
        scrolling="no"
        frameBorder="0"
        style={{ border: 'none' }}
        title="Softr Hero Section"
      />
    </div>
  )
}
