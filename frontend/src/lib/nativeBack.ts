import { haptic } from './haptics.ts';

const handlers = new Map<symbol, { priority: number; run: () => void }>();
let bound = false;
const dispatch = () => {
  const handler = [...handlers.values()].sort((a, b) => a.priority - b.priority).at(-1);
  if (handler) { haptic('tap'); handler.run(); }
};

function update() {
  const tg = window.Telegram?.WebApp;
  if (!tg?.initData || !tg.isVersionAtLeast('6.1')) return;
  if (handlers.size) {
    if (!bound) { tg.BackButton.onClick(dispatch); bound = true; }
    tg.BackButton.show();
  } else {
    tg.BackButton.hide();
    if (bound) { tg.BackButton.offClick(dispatch); bound = false; }
  }
}

export function registerTelegramBack(run: () => void, priority = 0) {
  const key = Symbol();
  handlers.set(key, { priority, run });
  update();
  return () => { handlers.delete(key); update(); };
}
