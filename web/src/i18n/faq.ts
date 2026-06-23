import type { Locale } from "./types";

export type FaqItem = { id: string; q: string; a: string };

const EN: FaqItem[] = [
  {
    id: "cloud_vs_keys",
    q: "Cloud vs my own API keys?",
    a: "Cloud subscription includes AI — no Gemini/Anthropic keys. Local mode (Settings) uses your own keys and quota is only on your machine.",
  },
  {
    id: "subscribe",
    q: "How do I subscribe?",
    a: "Settings → Subscribe. CIS: 899 ₽/mo via ЮKassa. International pricing opens when Stripe/Paddle is enabled. Checkout opens in your browser.",
  },
  {
    id: "quota",
    q: "Beat limits and trial?",
    a: "3 trial beats, then 30 beats per 30 days (3/day cap). Daily and monthly counters reset automatically. Grace period if payment fails.",
  },
  {
    id: "fl_studio",
    q: "Where is my beat / FL Studio?",
    a: "After Create beat, open the project folder (Help → Open project). Install FL Scripts in Settings, then Open in FL Studio from Home or Session.",
  },
  {
    id: "samples",
    q: "Who owns samples and beats?",
    a: "You own your beats. Bundled starter sounds are royalty-free for PLG output. Imported kits — check the pack license before release.",
  },
  {
    id: "password",
    q: "Forgot password?",
    a: "On the login screen tap Forgot password — reset link is sent by email (check spam). SLA for support: 24–48 hours.",
  },
  {
    id: "refund",
    q: "Refunds and cancel?",
    a: "Cancel anytime in the payment provider portal. Refund policy is in Help → Legal. Contact support@pluginflp.app with your receipt.",
  },
  {
    id: "status",
    q: "Is the service down?",
    a: "Check status.pluginflp.app or our Telegram updates channel. Generation may be degraded when AI providers are overloaded.",
  },
];

const RU: FaqItem[] = [
  {
    id: "cloud_vs_keys",
    q: "Облако или свои API-ключи?",
    a: "Подписка Cloud — AI уже включён, ключи не нужны. Локальный режим — свои ключи Gemini/Anthropic в Настройках, квота только на этом ПК.",
  },
  {
    id: "subscribe",
    q: "Как оформить подписку?",
    a: "Настройки → Подписаться. СНГ: 899 ₽/мес через ЮKassa. Оплата открывается в браузере.",
  },
  {
    id: "quota",
    q: "Лимиты и триал?",
    a: "3 пробных бита, затем 30 битов за 30 дней (макс. 3 в день). Счётчики сбрасываются автоматически. Grace при сбое оплаты.",
  },
  {
    id: "fl_studio",
    q: "Где бит и FL Studio?",
    a: "После Create beat открой папку проекта (Справка). Установи FL Scripts в Настройках, затем Open in FL Studio.",
  },
  {
    id: "samples",
    q: "Права на сэмплы и биты?",
    a: "Биты — твои. Стартовые звуки PLG — royalty-free для выхода из приложения. Импортированные киты — смотри лицензию пака.",
  },
  {
    id: "password",
    q: "Забыл пароль?",
    a: "На экране входа — «Забыли пароль?». Ссылка на почту (проверь спам). Саппорт отвечает за 24–48 ч.",
  },
  {
    id: "refund",
    q: "Возврат и отмена?",
    a: "Отмена в любой момент в кабинете платёжки. Политика возврата — Справка → Legal. Пиши support@pluginflp.app с чеком.",
  },
  {
    id: "status",
    q: "Сервис лежит?",
    a: "Смотри status.pluginflp.app или Telegram-канал обновлений. Генерация может тормозить при перегрузке AI-провайдеров.",
  },
];

const ES: FaqItem[] = [
  { id: "cloud_vs_keys", q: "¿Nube o mis propias API keys?", a: "La suscripción Cloud incluye IA. El modo local usa tus claves en Ajustes." },
  { id: "subscribe", q: "¿Cómo me suscribo?", a: "Ajustes → Suscribirse. El pago se abre en el navegador." },
  { id: "quota", q: "¿Límites y prueba?", a: "3 beats de prueba, luego 30 cada 30 días (máx. 3/día)." },
  { id: "fl_studio", q: "¿Dónde está mi beat?", a: "Tras crear el beat, abre la carpeta del proyecto en Ayuda e instala los scripts de FL." },
  { id: "samples", q: "¿Derechos de samples?", a: "Los beats son tuyos. Revisa la licencia de kits importados antes de publicar." },
  { id: "password", q: "¿Olvidé la contraseña?", a: "En inicio de sesión: ¿Olvidaste la contraseña? Revisa spam. Soporte: 24–48 h." },
  { id: "refund", q: "¿Reembolsos?", a: "Cancela cuando quieras. Política en Ayuda → Legal." },
  { id: "status", q: "¿Caída del servicio?", a: "Consulta status.pluginflp.app o el canal de Telegram." },
];

const PT: FaqItem[] = [
  { id: "cloud_vs_keys", q: "Nuvem ou minhas API keys?", a: "A assinatura Cloud inclui IA. O modo local usa suas chaves em Configurações." },
  { id: "subscribe", q: "Como assinar?", a: "Configurações → Assinar. Pagamento abre no navegador." },
  { id: "quota", q: "Limites e trial?", a: "3 beats de teste, depois 30 a cada 30 dias (máx. 3/dia)." },
  { id: "fl_studio", q: "Onde está o beat?", a: "Após criar, abra a pasta do projeto em Ajuda e instale os scripts do FL." },
  { id: "samples", q: "Direitos dos samples?", a: "Os beats são seus. Verifique a licença dos kits importados." },
  { id: "password", q: "Esqueci a senha?", a: "Na tela de login: Esqueci a senha. Suporte em 24–48 h." },
  { id: "refund", q: "Reembolso?", a: "Cancele quando quiser. Política em Ajuda → Legal." },
  { id: "status", q: "Serviço fora?", a: "Veja status.pluginflp.app ou o canal no Telegram." },
];

const ZH: FaqItem[] = [
  { id: "cloud_vs_keys", q: "云订阅还是自己的 API？", a: "云订阅包含 AI。本地模式在设置中使用你自己的密钥。" },
  { id: "subscribe", q: "如何订阅？", a: "设置 → 订阅，在浏览器中完成支付。" },
  { id: "quota", q: "额度与试用？", a: "3 次试用，之后每 30 天 30 首（每天最多 3 首）。" },
  { id: "fl_studio", q: "节拍在哪里？", a: "创建后在帮助中打开项目文件夹，并安装 FL 脚本。" },
  { id: "samples", q: "采样版权？", a: "节拍归你所有。导入套件请查看许可证。" },
  { id: "password", q: "忘记密码？", a: "登录页点击忘记密码，检查垃圾邮件。支持 24–48 小时回复。" },
  { id: "refund", q: "退款？", a: "随时取消。政策见帮助 → 法律文件。" },
  { id: "status", q: "服务故障？", a: "查看 status.pluginflp.app 或 Telegram 更新频道。" },
];

const JA: FaqItem[] = [
  { id: "cloud_vs_keys", q: "クラウドと自分の API キー？", a: "クラウド契約に AI 込み。ローカルは設定で自分のキーを使用。" },
  { id: "subscribe", q: "購読方法は？", a: "設定 → 購読。ブラウザで決済。" },
  { id: "quota", q: "制限とトライアル？", a: "試用 3 ビート、その後 30 日で 30 ビート（1 日 3 まで）。" },
  { id: "fl_studio", q: "ビートの場所は？", a: "作成後、ヘルプからプロジェクトフォルダを開き FL スクリプトをインストール。" },
  { id: "samples", q: "サンプルの権利？", a: "ビートはあなたのもの。インポートキットのライセンスを確認。" },
  { id: "password", q: "パスワードを忘れた？", a: "ログイン画面からリセット。サポート 24–48 時間。" },
  { id: "refund", q: "返金は？", a: "いつでも解約。ポリシーはヘルプ → 法務。" },
  { id: "status", q: "障害情報は？", a: "status.pluginflp.app または Telegram を確認。" },
];

const FR: FaqItem[] = [
  { id: "cloud_vs_keys", q: "Cloud ou mes clés API ?", a: "L'abonnement Cloud inclut l'IA. Le mode local utilise vos clés dans Réglages." },
  { id: "subscribe", q: "Comment s'abonner ?", a: "Réglages → S'abonner. Paiement dans le navigateur." },
  { id: "quota", q: "Limites et essai ?", a: "3 beats d'essai, puis 30 par 30 jours (max 3/jour)." },
  { id: "fl_studio", q: "Où est mon beat ?", a: "Après création, ouvrez le dossier projet dans Aide et installez les scripts FL." },
  { id: "samples", q: "Droits sur les samples ?", a: "Les beats vous appartiennent. Vérifiez la licence des kits importés." },
  { id: "password", q: "Mot de passe oublié ?", a: "Écran de connexion → Mot de passe oublié. Support sous 24–48 h." },
  { id: "refund", q: "Remboursement ?", a: "Annulez à tout moment. Politique dans Aide → Légal." },
  { id: "status", q: "Panne de service ?", a: "Consultez status.pluginflp.app ou Telegram." },
];

const DE: FaqItem[] = [
  { id: "cloud_vs_keys", q: "Cloud oder eigene API-Keys?", a: "Cloud-Abo enthält KI. Lokaler Modus nutzt deine Keys in Einstellungen." },
  { id: "subscribe", q: "Wie abonnieren?", a: "Einstellungen → Abonnieren. Zahlung im Browser." },
  { id: "quota", q: "Limits und Test?", a: "3 Test-Beats, dann 30 pro 30 Tage (max. 3/Tag)." },
  { id: "fl_studio", q: "Wo ist mein Beat?", a: "Nach Erstellung Projektordner in Hilfe öffnen und FL-Skripte installieren." },
  { id: "samples", q: "Sample-Rechte?", a: "Beats gehören dir. Lizenz importierter Kits prüfen." },
  { id: "password", q: "Passwort vergessen?", a: "Login → Passwort vergessen. Support in 24–48 h." },
  { id: "refund", q: "Erstattung?", a: "Jederzeit kündbar. Richtlinie unter Hilfe → Rechtliches." },
  { id: "status", q: "Ausfall?", a: "status.pluginflp.app oder Telegram-Kanal prüfen." },
];

const AR: FaqItem[] = [
  { id: "cloud_vs_keys", q: "السحابة أم مفاتيح API الخاصة؟", a: "اشتراك السحابة يشمل الذكاء الاصطناعي. الوضع المحلي يستخدم مفاتيحك في الإعدادات." },
  { id: "subscribe", q: "كيف أشترك؟", a: "الإعدادات → اشتراك. الدفع في المتصفح." },
  { id: "quota", q: "الحدود والتجربة؟", a: "3 إيقاعات تجريبية، ثم 30 كل 30 يومًا (حد أقصى 3/يوم)." },
  { id: "fl_studio", q: "أين الإيقاع؟", a: "بعد الإنشاء افتح مجلد المشروع من المساعدة وثبّت سكربتات FL." },
  { id: "samples", q: "حقوق العينات؟", a: "الإيقاعات ملكك. راجع ترخيص الحزم المستوردة." },
  { id: "password", q: "نسيت كلمة المرور؟", a: "من شاشة الدخول — نسيت كلمة المرور. الدعم خلال 24–48 ساعة." },
  { id: "refund", q: "استرداد؟", a: "إلغاء في أي وقت. السياسة في المساعدة → قانوني." },
  { id: "status", q: "انقطاع الخدمة؟", a: "راجع status.pluginflp.app أو قناة Telegram." },
];

export const FAQ_BY_LOCALE: Record<Locale, FaqItem[]> = {
  en: EN,
  ru: RU,
  es: ES,
  pt: PT,
  zh: ZH,
  ja: JA,
  fr: FR,
  de: DE,
  ar: AR,
};

export function faqForLocale(locale: Locale): FaqItem[] {
  return FAQ_BY_LOCALE[locale] ?? EN;
}
