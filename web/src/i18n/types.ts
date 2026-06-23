export type Locale = "en" | "ru" | "es" | "pt" | "zh" | "ja" | "fr" | "de" | "ar";

export type PromptCard = {
  title: string;
  subtitle: string;
  prompt: string;
};

export type Messages = {
  nav: {
    home: string;
    session: string;
    library: string;
    tools: string;
    help: string;
    settings: string;
  };
  fl: { online: string; offline: string };
  quota: {
    label: string;
    remaining: string;
    used: string;
    daysReset: string;
  };
  common: {
    loading: string;
    save: string;
    saving: string;
    open: string;
    openExplorer: string;
    files: string;
    version: string;
    updated: string;
    error: string;
    dash: string;
  };
  status: {
    loading: string;
    needApiKey: string;
    readyOpenFl: string;
    readyDescribe: string;
    starting: string;
    generating: string;
    checkNetwork: string;
    baked: string;
    error: string;
    openingFl: string;
    flError: string;
    flOpened: string;
    generationFailed: string;
  };
  offline: {
    title: string;
    desc: string;
    generationFailed: string;
    retry: string;
  };
  regenerate: {
    button: string;
    confirm: string;
    minusOne: string;
  };
  flOnboard: {
    noFlTitle: string;
    noFlDesc: string;
    scriptsTitle: string;
    scriptsDesc: string;
    detected: string;
    compatibility: string;
    getFl: string;
    openFailed: string;
  };
  updates: {
    title: string;
    check: string;
    checking: string;
    available: string;
    upToDate: string;
    download: string;
    apply: string;
    failed: string;
  };
  home: {
    eyebrow: string;
    title: string;
    desc: string;
    samplesInLibrary: string;
    createBeat: string;
    generating: string;
    openInFl: string;
    yourPrompt: string;
    promptPlaceholder: string;
    inspiration: string;
    quickPrompts: string;
    noResults: string;
  };
  session: {
    title: string;
    desc: string;
    beatReady: string;
    generating: string;
    noBeat: string;
    prompt: string;
    provider: string;
    connected: string;
    offline: string;
    bpm: string;
    style: string;
    sampleChop: string;
    chopDetail: string;
    stemExport: string;
    mixBlueprint: string;
    openStems: string;
    openMixGuide: string;
    matchedKit: string;
    openInFl: string;
    newBeat: string;
  };
  library: {
    title: string;
    desc: string;
    folder: string;
    scan: string;
    scanning: string;
    importKit: string;
    importing: string;
    stats: string;
    audio: string;
    totalFiles: string;
    howToImport: string;
    howToImportDesc: string;
    scanDone: string;
    scanFailed: string;
    importFailed: string;
    pickFailed: string;
  };
  tools: {
    title: string;
    desc: string;
    stemSplit: string;
    stemSplitDesc: string;
    demucsReady: string;
    demucsOffline: string;
    noFile: string;
    pickAudio: string;
    splitStems: string;
    splitting: string;
    flBridge: string;
    flBridgeDesc: string;
    installScripts: string;
    sessionLibrary: string;
    rebake: string;
    scanLibrary: string;
    importKit: string;
    rebakeHint: string;
    libraryCount: string;
  };
  help: {
    title: string;
    desc: string;
    quickFlow: string;
    documents: string;
    about: string;
    openProject: string;
    docsMissing: string;
    openDocFailed: string;
    legal: string;
    legalDesc: string;
    support: string;
    supportDesc: string;
    supportSla: string;
    faq: string;
    statusPage: string;
    updatesChannel: string;
    steps: string[];
    docs: Record<string, { title: string; desc: string }>;
  };
  settings: {
    title: string;
    desc: string;
    language: string;
    accountQuota: string;
    aiProvider: string;
    provider: string;
    geminiKey: string;
    anthropicKey: string;
    flStudio: string;
    flNotFound: string;
    autoOpenFl: string;
    installing: string;
    sampleLibrary: string;
    libraryFolder: string;
    starterSounds: string;
    starterDesc: string;
    bundledPool: string;
    starterKit: string;
    incomingDrops: string;
    about: string;
    saved: string;
    saveFailed: string;
    installFailed: string;
    scriptsInstalled: string;
    subscription: string;
    subscriptionDesc: string;
    subscribe: string;
    subscribing: string;
    subscriptionActive: string;
    subscriptionTrial: string;
    subscriptionGrace: string;
    subscriptionExpired: string;
    trialRemaining: string;
    graceRemaining: string;
    terms: string;
    privacy: string;
    refund: string;
    deleteAccount: string;
    deleteConfirm: string;
    deleteFailed: string;
    aiDisclaimer: string;
    feedback: string;
    feedbackDesc: string;
    feedbackCategory: string;
    feedbackMessage: string;
    feedbackAttachLog: string;
    feedbackSend: string;
    feedbackSending: string;
    feedbackSent: string;
    feedbackFailed: string;
    feedbackCatBug: string;
    feedbackCatBilling: string;
    feedbackCatFeature: string;
    feedbackCatGeneral: string;
  };
  player: {
    working: string;
    openInFl: string;
    createBeat: string;
    describeBeat: string;
    hint: string;
  };
  topbar: {
    placeholder: string;
  };
  kit: {
    title: string;
    matching: string;
    fromLibrary: string;
    starter: string;
    roles: Record<string, string>;
  };
  console: {
    title: string;
    filthBanner: string;
    bake: string;
    flip: string;
    chaos: string;
    filthOn: string;
    filthRoute: string;
    applying: string;
    needBeat: string;
  };
  blueprint: {
    title: string;
  };
  auth: {
    title: string;
    desc: string;
    email: string;
    password: string;
    login: string;
    signup: string;
    loggingIn: string;
    signingUp: string;
    forgot: string;
    resetSent: string;
    logout: string;
    haveAccount: string;
    newAccount: string;
    acceptTerms: string;
    confirmAge: string;
    legalRequired: string;
    aiDisclaimer: string;
  };
  prompts: {
    darkTrap: PromptCard;
    rageMelody: PromptCard;
    pluggnb: PromptCard;
    detroit: PromptCard;
    melodic: PromptCard;
  };
};

/** Locale files may omit keys merged from `en` at runtime. */
export type LocalePack = Omit<
  Messages,
  "help" | "settings" | "auth" | "offline" | "regenerate" | "flOnboard" | "updates"
> & {
  auth?: Partial<Messages["auth"]>;
  help?: Partial<Messages["help"]>;
  settings?: Partial<Messages["settings"]>;
  offline?: Partial<Messages["offline"]>;
  regenerate?: Partial<Messages["regenerate"]>;
  flOnboard?: Partial<Messages["flOnboard"]>;
  updates?: Partial<Messages["updates"]>;
};

export const LOCALE_OPTIONS: { id: Locale; label: string }[] = [
  { id: "en", label: "English" },
  { id: "ru", label: "Русский" },
  { id: "es", label: "Español" },
  { id: "pt", label: "Português" },
  { id: "zh", label: "中文" },
  { id: "ja", label: "日本語" },
  { id: "fr", label: "Français" },
  { id: "de", label: "Deutsch" },
  { id: "ar", label: "العربية" },
];

export const RTL_LOCALES: Locale[] = ["ar"];
