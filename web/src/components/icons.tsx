/* Sidebar + UI icons — consistent 24×24, 1.75 stroke, rounded caps. */

const S = {
  width: 20,
  height: 20,
  viewBox: "0 0 24 24",
  fill: "none" as const,
  "aria-hidden": true,
};

const stroke = {
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function IconHome() {
  return (
    <svg {...S}>
      <path
        {...stroke}
        d="M5 10.5 12 5l7 5.5V19a1.25 1.25 0 0 1-1.25 1.25H6.25A1.25 1.25 0 0 1 5 19v-8.5Z"
      />
      <path {...stroke} d="M10 20.25V14h4v6.25" />
    </svg>
  );
}

export function IconSettings() {
  return (
    <svg {...S}>
      <circle {...stroke} cx="12" cy="12" r="2.75" />
      <path
        {...stroke}
        strokeLinejoin="miter"
        d="M12 3.5v2.1M12 18.4v2.1M4.6 4.6l1.5 1.5M17.9 17.9l1.5 1.5M3.5 12h2.1M18.4 12h2.1M4.6 19.4l1.5-1.5M17.9 6.1l1.5-1.5"
      />
    </svg>
  );
}

export function IconRegenerate() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M4 12a8 8 0 0 1 13.7-5.6M20 7V4m0 0h-3m3 0 5.2 5.2M20 12a8 8 0 0 1-13.7 5.6M4 17v3m0 0h3m-3 0-5.2-5.2"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function IconWave() {
  return (
    <svg {...S}>
      <path
        {...stroke}
        d="M3 10v4M7 8v8M11 6v12M15 9v6M19 7v10M23 10v4"
      />
    </svg>
  );
}

export function IconPlay() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M8 5.5v13l11-6.5-11-6.5Z" />
    </svg>
  );
}

export function IconFl() {
  return (
    <svg {...S}>
      <rect {...stroke} x="4.5" y="4.5" width="15" height="15" rx="3.5" />
      <path {...stroke} d="M8.5 9h7M8.5 12h5.5M8.5 15h4" />
    </svg>
  );
}

export function IconFolder() {
  return (
    <svg {...S}>
      <path
        {...stroke}
        d="M4.5 8.5h5.2l1.8 2h9a1.5 1.5 0 0 1 1.5 1.5v7a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 4.5 18.5v-10Z"
      />
    </svg>
  );
}

/** Sample library — stacked wave slots. */
export function IconLibrary() {
  return (
    <svg {...S}>
      <rect {...stroke} x="4" y="5" width="6" height="14" rx="1.25" />
      <path {...stroke} d="M13 9v10M17 7v12M21 10v9" />
    </svg>
  );
}

/** Producer tools — horizontal sliders. */
export function IconTools() {
  return (
    <svg {...S}>
      <path {...stroke} d="M4 8h16M4 12h10M4 16h14" />
      <circle fill="currentColor" cx="16" cy="8" r="1.75" />
      <circle fill="currentColor" cx="10" cy="12" r="1.75" />
      <circle fill="currentColor" cx="18" cy="16" r="1.75" />
    </svg>
  );
}

export function IconHelp() {
  return (
    <svg {...S}>
      <circle {...stroke} cx="12" cy="12" r="8.25" />
      <path
        {...stroke}
        d="M9.75 9.25a2.35 2.35 0 0 1 4.1 1.45c0 1.45-2.35 1.75-2.35 3.3M12 16.75h.01"
      />
    </svg>
  );
}

export function IconAccount() {
  return (
    <svg {...S}>
      <circle {...stroke} cx="12" cy="8.25" r="3.25" />
      <path
        {...stroke}
        d="M5.5 19.5a6.5 6.5 0 0 1 13 0"
      />
    </svg>
  );
}

export function IconGrid() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="6" cy="6" r="1.6" fill="currentColor" />
      <circle cx="12" cy="6" r="1.6" fill="currentColor" />
      <circle cx="18" cy="6" r="1.6" fill="currentColor" />
      <circle cx="6" cy="12" r="1.6" fill="currentColor" />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" />
      <circle cx="18" cy="12" r="1.6" fill="currentColor" />
      <circle cx="6" cy="18" r="1.6" fill="currentColor" />
      <circle cx="12" cy="18" r="1.6" fill="currentColor" />
      <circle cx="18" cy="18" r="1.6" fill="currentColor" />
    </svg>
  );
}

export function IconSearch() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.75" />
      <path d="M16 16l4 4" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
    </svg>
  );
}
