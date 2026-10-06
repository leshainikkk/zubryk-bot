import { useEffect, useLayoutEffect, useState } from 'react';
import type { Dashboard, Tab } from './types';
import { useResource } from './lib/useResource';
import { initializeTelegram, isTelegram, telegram, useTelegramSettings } from './lib/telegram';
import { installInteractionHaptics } from './lib/haptics';
import { Navigation } from './components/Navigation';
import { Home } from './pages/Home';
import { Tests } from './pages/Tests';
import { Grammar } from './pages/Grammar';
import { Settings } from './pages/Settings';

const currentTab = (): Tab => ['home', 'tests', 'grammar'].includes(location.hash.slice(1)) ? location.hash.slice(1) as Tab : 'home';

export default function App() {
  const [tab, setTab] = useState<Tab>(currentTab);
  const [settings, setSettings] = useState(false);
  const resource = useResource<Dashboard>(isTelegram() ? '/dashboard' : '/preview/dashboard');
  useLayoutEffect(initializeTelegram, []);
  useEffect(installInteractionHaptics, []);
  useTelegramSettings(() => setSettings(true));
  useEffect(() => {
    let lastRefresh = 0;
    const refresh = () => {
      if (document.visibilityState === 'visible' && performance.now() - lastRefresh > 1500) {
        lastRefresh = performance.now(); resource.retry();
      }
    };
    document.addEventListener('visibilitychange', refresh);
    const tg = telegram();
    const activated = isTelegram() && tg?.isVersionAtLeast('8.0');
    if (activated) tg?.onEvent('activated', refresh);
    return () => { document.removeEventListener('visibilitychange', refresh); if (activated) tg?.offEvent('activated', refresh); };
  }, [resource.retry]);
  useEffect(() => {
    const update = () => { setTab(currentTab()); window.scrollTo(0, 0); };
    window.addEventListener('hashchange', update);
    return () => window.removeEventListener('hashchange', update);
  }, []);
  return <div className="app-shell">
    <main className="main-content"><div hidden={tab !== 'home'} className="page"><Home data={resource.data} loading={resource.loading} error={resource.error} retry={resource.retry} onSettings={() => setSettings(true)} /></div>
      <div hidden={tab !== 'tests'} className="page"><Tests active={tab === 'tests'} /></div><div hidden={tab !== 'grammar'} className="page"><Grammar active={tab === 'grammar'} /></div>
    </main>
    <Navigation active={tab} onChange={next => { setTab(next); if (location.hash !== `#${next}`) location.hash = next; window.scrollTo(0, 0); }} />
    <Settings open={settings} onClose={() => setSettings(false)} data={resource.data} onSaved={resource.setData} />
  </div>;
}
