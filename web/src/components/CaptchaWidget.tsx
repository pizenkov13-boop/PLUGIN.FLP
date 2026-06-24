import { useEffect, useRef } from "react";

declare global {
  interface Window {
    turnstile?: {
      render: (el: HTMLElement, opts: Record<string, unknown>) => string;
      remove: (id: string) => void;
    };
  }
}

type Props = {
  provider: string;
  siteKey: string;
  onToken: (token: string | null) => void;
};

export default function CaptchaWidget({ provider, siteKey, onToken }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);

  useEffect(() => {
    onToken(null);
    if (provider !== "turnstile" || !siteKey) return;

    function cleanup() {
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
      onToken(null);
    }

    function render() {
      if (!containerRef.current || !window.turnstile) return;
      cleanup();
      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        callback: (token: string) => onToken(token),
        "expired-callback": () => onToken(null),
        "error-callback": () => onToken(null),
      });
    }

    if (window.turnstile) {
      render();
      return cleanup;
    }

    const existing = document.querySelector('script[src*="turnstile"]') as HTMLScriptElement | null;
    const script = existing ?? document.createElement("script");
    if (!existing) {
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      document.head.appendChild(script);
    }

    script.addEventListener("load", render);
    return () => {
      script.removeEventListener("load", render);
      cleanup();
    };
  }, [provider, siteKey, onToken]);

  if (provider !== "turnstile" || !siteKey) return null;
  return <div ref={containerRef} className="auth__captcha" />;
}
