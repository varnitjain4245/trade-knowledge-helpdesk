/**
 * i18n bootstrap. Per-locale chunks, loaded on demand — a Tamil user must not download
 * Bengali strings, and the same applies to the font subsets these locales imply.
 */

import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'
import type { Iso3 } from './languages'

const loaders: Record<Iso3, () => Promise<{ default: Record<string, string> }>> = {
  eng: () => import('./locales/eng.json'),
  hin: () => import('./locales/hin.json'),
  ben: () => import('./locales/ben.json'),
  tam: () => import('./locales/tam.json'),
  tel: () => import('./locales/tel.json'),
  mar: () => import('./locales/mar.json'),
}

export async function loadLocale(code: Iso3): Promise<void> {
  if (i18next.hasResourceBundle(code, 'translation')) return
  const mod = await loaders[code]()
  i18next.addResourceBundle(code, 'translation', mod.default)
}

export async function initI18n(initial: Iso3 = 'eng'): Promise<void> {
  await i18next.use(initReactI18next).init({
    lng: initial,
    fallbackLng: 'eng',
    interpolation: { escapeValue: false },
    resources: {},
  })
  await loadLocale(initial)
}
