type Feedback = 'tap' | 'selection' | 'success' | 'error';
let lastInteraction = -Infinity;

export function haptic(feedback: Feedback) {
  const tg = window.Telegram?.WebApp;
  if (!tg?.initData || !tg.isVersionAtLeast('6.1') || !tg.HapticFeedback) return;
  const notification = feedback === 'success' || feedback === 'error';
  const now = performance.now();
  if (!notification && now - lastInteraction < 70) return;
  try {
    if (notification) tg.HapticFeedback.notificationOccurred(feedback);
    else if (feedback === 'selection') tg.HapticFeedback.selectionChanged();
    else tg.HapticFeedback.impactOccurred('soft');
    if (!notification) lastInteraction = now;
  } catch {}
}

export function installInteractionHaptics() {
  const click = (event: MouseEvent) => {
    if (!(event.target instanceof Element)) return;
    const control = event.target.closest<HTMLButtonElement | HTMLAnchorElement>('button, a');
    if (!control || control.matches(':disabled, [aria-disabled="true"], [data-no-haptic]')) return;
    if (control.getAttribute('aria-current') === 'page' || control.getAttribute('aria-pressed') === 'true') return;
    haptic(control.hasAttribute('aria-pressed') || control.dataset.haptic === 'selection' ? 'selection' : 'tap');
  };
  const change = (event: Event) => {
    const target = event.target;
    if (target instanceof HTMLSelectElement || target instanceof HTMLInputElement && ['radio', 'checkbox'].includes(target.type)) haptic('selection');
  };
  document.addEventListener('click', click, true);
  document.addEventListener('change', change);
  return () => { document.removeEventListener('click', click, true); document.removeEventListener('change', change); };
}
