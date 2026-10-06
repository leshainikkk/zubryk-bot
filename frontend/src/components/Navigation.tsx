import type { Tab } from '../types';
import { Icon } from './Icon';

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: 'home', label: 'Главная', icon: 'home' },
  { id: 'tests', label: 'Тесты', icon: 'tests' },
  { id: 'grammar', label: 'Грамматика', icon: 'book' },
];
export function Navigation({ active, onChange }: { active: Tab; onChange: (tab: Tab) => void }) {
  return <nav className="navigation" aria-label="Разделы приложения">
    {tabs.map(tab => <button key={tab.id} data-haptic="selection" className={`nav-item ${active === tab.id ? 'selected' : ''}`} aria-current={active === tab.id ? 'page' : undefined} onClick={() => onChange(tab.id)}>
      <Icon name={active === 'home' && tab.id === 'home' ? 'home-filled' : tab.icon} /><span>{tab.label}</span>
    </button>)}
  </nav>;
}
