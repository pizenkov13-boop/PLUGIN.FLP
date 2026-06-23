import { useEffect, useState } from "react";

import type { ApiResult } from "../types";

import { cloudLogin, cloudResetPassword, cloudSignup, getAuthStatus } from "../api";

import { useI18n } from "../i18n";
import { apiErrorMessage } from "../errors";

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

  const [captchaRequired, setCaptchaRequired] = useState(false);
  const [inviteRequired, setInviteRequired] = useState(false);
  const [inviteCode, setInviteCode] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [confirmAge, setConfirmAge] = useState(false);

  const [busy, setBusy] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [message, setMessage] = useState<string | null>(null);



  useEffect(() => {

    getAuthStatus().then((s) => {
      setCaptchaRequired(Boolean(s.captcha_required));
      setInviteRequired(Boolean(s.invite_required));
    });

  }, []);



  async function onSubmit() {
    if (busy || !email.trim() || !password || honeypot.trim()) return;
    if (mode === "signup" && (!acceptTerms || !confirmAge)) {
      setError(t("auth.legalRequired"));
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
            null,
            inviteCode.trim() || null,
            acceptTerms,
            confirmAge,
          );

    setBusy(false);

    if (!result.ok) {

      setError(apiErrorMessage(result, t));

      return;

    }

    if (mode === "signup") {

      const sess = (result as ApiResult & { session?: { access_token?: string } }).session;

      if (!sess?.access_token) {

        setMessage(result.message?.toString() ?? t("auth.resetSent"));

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
          <label className="auth__field">
            <span>Invite code</span>
            <input
              type="text"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              autoComplete="off"
              spellCheck={false}
            />
          </label>
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

        {mode === "signup" && captchaRequired && (

          <p className="auth__hint">CAPTCHA: set Turnstile keys in cloud .env for production.</p>

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

          }}

        >

          {mode === "login" ? t("auth.newAccount") : t("auth.haveAccount")}

        </button>

      </div>

    </div>

  );

}

