export type View = "home" | "session" | "settings";

export type QuickPrompt = {
  title: string;
  subtitle: string;
  prompt: string;
  tone: "blue" | "violet" | "rose" | "amber" | "mint";
};

export const QUICK_PROMPTS: QuickPrompt[] = [
  {
    title: "Dark trap",
    subtitle: "hard 808s · eerie bells",
    prompt: "dark trap beat, hard 808s, eerie bell melody, 140 bpm, opium vibe",
    tone: "violet",
  },
  {
    title: "Rage melody",
    subtitle: "distorted lead · fast hats",
    prompt: "rage beat, distorted lead melody, fast hi-hats, heavy kick, 150 bpm",
    tone: "rose",
  },
  {
    title: "Pluggnb",
    subtitle: "airy pads · soft drums",
    prompt: "pluggnb beat, airy pads, soft drums, dreamy chords, 150 bpm",
    tone: "blue",
  },
  {
    title: "Detroit",
    subtitle: "donk bass · minimal",
    prompt: "detroit type beat, donk bass, minimal drums, dark atmosphere, 140 bpm",
    tone: "amber",
  },
  {
    title: "Melodic",
    subtitle: "guitar loop · bounce",
    prompt: "melodic trap, guitar loop, bouncy 808s, emotional, 145 bpm",
    tone: "mint",
  },
];
