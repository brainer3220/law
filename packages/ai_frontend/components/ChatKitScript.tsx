'use client';

import Script from 'next/script';

export default function ChatKitScript() {
  const handleLoad = () => {
    console.log('✅ ChatKit script loaded successfully');
    window.dispatchEvent(new CustomEvent('chatkit-script-loaded'));
  };

  const handleError = (e: Error) => {
    console.error('❌ ChatKit script failed to load:', e);
    window.dispatchEvent(new CustomEvent('chatkit-script-error', { detail: e }));
  };

  return (
    <Script
      src="https://cdn.platform.openai.com/deployments/chatkit/chatkit.js"
      strategy="beforeInteractive"
      onLoad={handleLoad}
      onError={handleError}
    />
  );
}
