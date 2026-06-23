from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

patch_help = """    legal: "Legal",
    legalDesc: "Terms, privacy, refunds. AI outputs are tools.",
"""
patch_docs = """      terms: { title: "Terms of Service", desc: "Subscription, beat ownership, age 16+." },
      privacy: { title: "Privacy Policy", desc: "GDPR, retention 90d, account deletion." },
      refund: { title: "Refund Policy", desc: "Cancel anytime; refunds via support." },
"""
patch_settings = """    terms: "Terms",
    privacy: "Privacy",
    refund: "Refunds",
    deleteAccount: "Delete account",
    deleteConfirm: "Delete your account permanently?",
    deleteFailed: "Could not delete account.",
    aiDisclaimer: "AI-assisted output. You own your beats.",
"""
patch_auth = """    acceptTerms: "I accept Terms and Privacy Policy",
    confirmAge: "I am at least 16 years old",
    legalRequired: "Accept terms and confirm age.",
    aiDisclaimer: "Beats are AI-generated.",
"""

for loc in ("es", "pt", "zh", "ja", "fr", "de", "ar"):
    p = ROOT / f"web/src/i18n/locales/{loc}.ts"
    t = p.read_text(encoding="utf-8")
    if "legal:" not in t:
        t = t.replace("    openDocFailed:", patch_help + "    openDocFailed:", 1)
    if "terms: { title" not in t:
        t = t.replace("      fl_workflows:", patch_docs + "      fl_workflows:", 1)
    if "deleteAccount:" not in t:
        t = t.replace("    graceRemaining:", patch_settings + "    graceRemaining:", 1)
    if "acceptTerms:" not in t:
        t = t.replace("    newAccount:", patch_auth + "    newAccount:", 1)
    p.write_text(t, encoding="utf-8")

print("patched")
