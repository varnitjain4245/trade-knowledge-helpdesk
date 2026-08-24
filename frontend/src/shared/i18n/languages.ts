/**
 * Language mapping (lld.md D-4, amendment §D).
 *
 * The API speaks ISO 639-3 (`tam`); the DOM speaks BCP-47 (`ta`). Both are correct in
 * their own domain — 639-3 is right for stored linguistic data, BCP-47 is what the
 * `lang` attribute requires — and the mapping is **served** by `GET /api/v1/languages`
 * rather than hard-coded twice.
 *
 * `applyDocumentLanguage` is the ONE call site where the conversion happens. Applying it
 * per component is how half the script selectors silently stop matching.
 */

export type Iso3 = 'eng' | 'hin' | 'ben' | 'tam' | 'tel' | 'mar'
export type Script = 'latin' | 'devanagari' | 'bengali' | 'tamil' | 'telugu'

export interface LanguageView {
  code: Iso3
  bcp47: string
  script: Script
  displayName: string
  enabled: boolean
}

/** Fallback used only before the served map arrives; the server remains authoritative. */
export const BOOTSTRAP_LANGUAGES: readonly LanguageView[] = [
  { code: 'eng', bcp47: 'en', script: 'latin', displayName: 'English', enabled: true },
  { code: 'hin', bcp47: 'hi', script: 'devanagari', displayName: 'हिन्दी', enabled: true },
  { code: 'ben', bcp47: 'bn', script: 'bengali', displayName: 'বাংলা', enabled: false },
  { code: 'tam', bcp47: 'ta', script: 'tamil', displayName: 'தமிழ்', enabled: false },
  { code: 'tel', bcp47: 'te', script: 'telugu', displayName: 'తెలుగు', enabled: false },
  { code: 'mar', bcp47: 'mr', script: 'devanagari', displayName: 'मराठी', enabled: false },
] as const

export function toBcp47(code: Iso3, map: readonly LanguageView[]): string {
  return map.find((l) => l.code === code)?.bcp47 ?? 'en'
}

export function scriptOf(code: Iso3, map: readonly LanguageView[]): Script {
  return map.find((l) => l.code === code)?.script ?? 'latin'
}

/**
 * The single call site. Sets `lang` for assistive technology and correct pronunciation,
 * and `data-script` for the type scale — two attributes because they answer two
 * different questions, and conflating them is what the Devanagari pair breaks.
 */
export function applyDocumentLanguage(code: Iso3, map: readonly LanguageView[]): void {
  const root = document.documentElement
  root.setAttribute('lang', toBcp47(code, map))
  root.setAttribute('data-script', scriptOf(code, map))
}
