import { useCallback, useEffect, useState } from "react";

import type { ApiResult } from "../types";

import { cloudLogin, cloudResetPassword, cloudSignup, getAuthStatus } from "../api";

import { useI18n } from "../i18n";
import { apiErrorMessage } from "../errors";
import CaptchaWidget from "./CaptchaWidget";
import PlgLogo from "./PlgLogo";
import "./AuthView.css";

type Props = {
  onAuthed: () => void;
};

export default function AuthView({ onAuthed }: Props) {
  const { t } = useI18n();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [honeypot, setHoneypot] = useState("");
  const [inviteRequired, setInviteRequired] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [confirmAge, setConfirmAge] = useState(false);
  const [captchaRequired, setCaptchaRequired] = useState(false);
  const [captchaProvider, setCaptchaProvider] = useState("none");
  const [captchaSiteKey, setCaptchaSiteKey] = useState<string | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const onCaptchaToken = useCallback((token: string | null) => {
    setCaptchaToken(token);
  }, []);

  useEffect(() => {
    getAuthStatus().then((s) => {
      setInviteRequired(Boolean(s.invite_required));
      setCaptchaRequired(Boolean(s.captcha_required));
      setCaptchaProvider(s.captcha_provider ?? "none");
      setCaptchaSiteKey(s.captcha_site_key ?? null);
      if (s.signed_in) onAuthed();
    });
    // Only on mount — onAuthed is stable enough for session restore.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onSubmit() {
    if (busy || !email.trim() || !password || honeypot.trim()) return;
    if (mode === "signup" && (!acceptTerms || !confirmAge)) {
      setError(t("auth.legalRequired"));
      return;
    }
    if (mode === "signup" && captchaRequired && !captchaToken) {
      setError(t("auth.captchaRequired"));
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);

    const result =
      mode === "login"
        ? await cloudLogin(email.trim(), password)
        : await cloudSignup(
            email.trim(),
            password,
            captchaToken,
            inviteCode.trim() || null,
            acceptTerms,
            confirmAge,
          );

    setBusy(false);

    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      setCaptchaToken(null);
      return;
    }

    if (mode === "signup") {
      const sess = (result as ApiResult & { session?: { access_token?: string } }).session;
      const needsLogin = Boolean((result as ApiResult & { needs_login?: boolean }).needs_login);
      if (!sess?.access_token || needsLogin) {
        setMessage(t("auth.signupLogin"));
        setMode("login");
        setCaptchaToken(null);
        return;
      }
    }

    onAuthed();
  }

  async function onForgot() {
    if (!email.trim() || busy) return;
    setBusy(true);
    setError(null);
    const result = await cloudResetPassword(email.trim());
    setBusy(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    setMessage(result.message?.toString() ?? t("auth.resetSent"));
  }

  return (
    <div className="auth">
      <div className="auth__card">
        <PlgLogo className="auth__logo" />
        <h1>{t("auth.title")}</h1>
        <p>{t("auth.desc")}</p>

        <input
          type="text"
          name="website"
          value={honeypot}
          onChange={(e) => setHoneypot(e.target.value)}
          tabIndex={-1}
          autoComplete="off"
          className="auth__honeypot"
          aria-hidden="true"
        />

        <label className="auth__field">
          <span>{t("auth.email")}</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </label>

        <label className="auth__field">
          <span>{t("auth.password")}</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        </label>

        {mode === "signup" && inviteRequired && (
          <>
            <label className="auth__field">
              <span>{t("auth.inviteCode")}</span>
              <input
                type="text"
                value={inviteCode}
                onChange={(e) => setInviteCode(e.target.value)}
                autoComplete="off"
                spellCheck={false}
              />
            </label>
            <p className="auth__hint">
              {t("auth.inviteHint")}{" "}
              <a href="https://pluginflp.app/#beta" target="_blank" rel="noopener noreferrer">
                {t("auth.waitlistLink")}
              </a>
            </p>
          </>
        )}

        {mode === "signup" && (
          <>
            <label className="settings__check">
              <input
                type="checkbox"
                checked={acceptTerms}
                onChange={(e) => setAcceptTerms(e.target.checked)}
              />
              <span>{t("auth.acceptTerms")}</span>
            </label>
            <label className="settings__check">
              <input
                type="checkbox"
                checked={confirmAge}
                onChange={(e) => setConfirmAge(e.target.checked)}
              />
              <span>{t("auth.confirmAge")}</span>
            </label>
            <p className="auth__hint">{t("auth.aiDisclaimer")}</p>
          </>
        )}

        {mode === "signup" && captchaRequired && captchaSiteKey && (
          <CaptchaWidget
            provider={captchaProvider}
            siteKey={captchaSiteKey}
            onToken={onCaptchaToken}
          />
        )}

        {error && <p className="auth__error">{error}</p>}
        {message && <p className="auth__success">{message}</p>}

        <button type="button" className="auth__btn" onClick={onSubmit} disabled={busy}>
          {busy
            ? mode === "login"
              ? t("auth.loggingIn")
              : t("auth.signingUp")
            : mode === "login"
              ? t("auth.login")
              : t("auth.signup")}
        </button>

        <button type="button" className="auth__link" onClick={onForgot} disabled={busy}>
          {t("auth.forgot")}
        </button>

        <button
          type="button"
          className="auth__link"
          onClick={() => {
            setMode(mode === "login" ? "signup" : "login");
            setError(null);
            setMessage(null);
            setCaptchaToken(null);
          }}
        >
          {mode === "login" ? t("auth.newAccount") : t("auth.haveAccount")}
        </button>
      </div>
    </div>
  );
}
