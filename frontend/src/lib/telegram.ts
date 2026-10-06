import { useEffect, useRef } from 'react';
import { haptic } from './haptics';
import { registerTelegramBack } from './nativeBack';

export const telegram = () => window.Telegram?.WebApp;
export const isTelegram = () => Boolean(telegram()?.initData);

export function initializeTelegram() {
  const tg = telegram();
  const preference = matchMedia('(prefers-color-scheme: dark)');
  const update = () => {
    const dark = isTelegram() ? tg?.colorScheme === 'dark' : preference.matches;
    const theme = isTelegram() ? tg?.themeParams ?? {} : {};
    const fallback = dark
      ? { bg: '#111418', secondary: '#1b2026', surface: '#1b2026', text: '#f2f4f7', hint: '#a1abb9', accent: '#75b2ff', button: '#64a7fa', buttonText: '#0b1728', line: '#303943' }
      : { bg: '#ffffff', secondary: '#f3f5f8', surface: '#f3f5f8', text: '#151a21', hint: '#737e8e', accent: '#1682f8', button: '#1682f8', buttonText: '#ffffff', line: '#e8ecf1' };
    const colors: Record<string, string> = {
      'bg': theme.bg_color || fallback.bg,
      'surface': theme.section_bg_color && theme.section_bg_color.toLowerCase() !== (theme.bg_color || fallback.bg).toLowerCase() ? theme.section_bg_color : theme.secondary_bg_color || fallback.surface,
      'secondary': theme.secondary_bg_color || fallback.secondary,
      'text': theme.text_color || fallback.text,
      'hint': theme.hint_color || theme.subtitle_text_color || fallback.hint,
      'accent': theme.accent_text_color || theme.link_color || theme.button_color || fallback.accent,
      'button': theme.button_color || fallback.button,
      'button-text': theme.button_text_color || fallback.buttonText,
      'line': theme.section_separator_color || fallback.line,
      'bottom': theme.bottom_bar_bg_color || theme.bg_color || fallback.bg,
    };
    for (const [key, value] of Object.entries(colors)) document.documentElement.style.setProperty(`--${key}`, value);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', colors.bg);
    if (isTelegram() && tg) {
      for (const edge of ['top', 'bottom', 'left', 'right'] as const) {
        document.documentElement.style.setProperty(`--safe-${edge}`, `${(tg.safeAreaInset?.[edge] ?? 0) + (tg.contentSafeAreaInset?.[edge] ?? 0)}px`);
      }
      if (tg.isVersionAtLeast('6.1')) {
        tg.setHeaderColor('bg_color');
        tg.setBackgroundColor(colors.bg);
      }
      if (tg.isVersionAtLeast('7.10')) tg.setBottomBarColor?.(colors.bottom);
    }
  };
  update();
  preference.addEventListener('change', update);
  if (tg && isTelegram()) {
    tg.ready(); tg.expand();
    for (const event of ['themeChanged', 'safeAreaChanged', 'contentSafeAreaChanged', 'viewportChanged']) tg.onEvent(event, update);
  }
  return () => {
    preference.removeEventListener('change', update);
    if (tg && isTelegram()) for (const event of ['themeChanged', 'safeAreaChanged', 'contentSafeAreaChanged', 'viewportChanged']) tg.offEvent(event, update);
  };
}

export function openBot(username: string, payload = '') {
  if (!username) return;
  const url = `https://t.me/${encodeURIComponent(username)}${payload ? `?start=${encodeURIComponent(payload)}` : ''}`;
  if (isTelegram()) telegram()?.openTelegramLink(url);
  else window.open(url, '_blank', 'noopener,noreferrer');
}

export function useTelegramBack(enabled: boolean, onBack: () => void, priority = 0) {
  const callback = useRef(onBack);
  callback.current = onBack;
  useEffect(() => {
    if (!enabled) return;
    return registerTelegramBack(() => callback.current(), priority);
  }, [enabled, priority]);
}

export function useTelegramSettings(onOpen: () => void) {
  const callback = useRef(onOpen);
  callback.current = onOpen;
  useEffect(() => {
    const tg = telegram();
    if (!tg || !isTelegram() || !tg.isVersionAtLeast('7.0') || !tg.SettingsButton) return;
    const open = () => { haptic('tap'); callback.current(); };
    tg.SettingsButton.onClick(open); tg.SettingsButton.show();
    return () => { tg.SettingsButton?.offClick(open); tg.SettingsButton?.hide(); };
  }, []);
}
