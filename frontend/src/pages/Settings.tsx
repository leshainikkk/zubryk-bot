import { useEffect, useState } from 'react';
import type { Dashboard } from '../types';
import { api } from '../lib/api';
import { openBot } from '../lib/telegram';
import { Sheet } from '../components/Sheet';
import { Icon } from '../components/Icon';
import { useResource } from '../lib/useResource';
import { haptic } from '../lib/haptics';

export function Settings({ open, onClose, data, onSaved }: { open: boolean; onClose: () => void; data: Dashboard | null; onSaved: (data: Dashboard) => void }) {
  const { data: sources } = useResource<{ source_url?: string; license_url?: string; license?: string }>('/content/sources');
  const [name, setName] = useState('');
  const [time, setTime] = useState('off');
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState('');
  useEffect(() => { if (open) { setName(data?.profile?.name ?? ''); setTime(data?.profile?.dailyTime ?? 'off'); setStatus(''); } }, [open, data?.profile?.name, data?.profile?.dailyTime]);
  async function save(event: React.FormEvent) {
    event.preventDefault(); setSaving(true); setStatus('');
    try {
      const next = await api<Dashboard>('/settings', { method: 'PATCH', body: JSON.stringify({ name: name.trim(), dailyTime: time }) });
      onSaved(next); haptic('success'); onClose();
    } catch (error) { setStatus((error as Error).message); haptic('error'); }
    finally { setSaving(false); }
  }
  return <Sheet open={open} onClose={onClose} title="Настройки">
    {data?.profile ? <form onSubmit={save}>
      <label className="field-label" htmlFor="profile-name">Ваше имя</label><input id="profile-name" className="field" value={name} onChange={event => setName(event.target.value)} maxLength={64} required autoComplete="name" />
      <label className="field-label" htmlFor="daily-time">Ежедневные слова</label><select id="daily-time" className="field" value={time} onChange={event => setTime(event.target.value)}>
        {data.dailyTimeChoices.map(choice => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
      </select><p className="field-hint">Время по {data.timezone}. Настройки общие с ботом.</p>
      {status && <p className="form-error" role="alert">{status}</p>}<button className="primary full-width" type="submit" disabled={saving || !name.trim()}>{saving ? 'Сохраняем…' : 'Сохранить'}</button>
    </form> : <><p>Настройки появятся после создания профиля в Telegram.</p><button className="primary full-width" onClick={() => openBot(data?.botUsername ?? '')}>Открыть бота<Icon name="external" /></button></>}
    <div className="settings-links"><button className="plain-row" onClick={() => openBot(data?.botUsername ?? '', 'support')}><span>Написать в поддержку</span><Icon name="external" /></button>
      {data?.profile && <button className="plain-row muted" onClick={() => openBot(data.botUsername, 'settings')}><span>Управление профилем в боте</span><Icon name="external" /></button>}
    </div>
    {sources?.source_url && <p className="field-hint">Часть словаря — <a href={sources.source_url} target="_blank" rel="noopener noreferrer">Викисловарь</a>. {sources.license_url && <a href={sources.license_url} target="_blank" rel="noopener noreferrer">{sources.license}</a>} · написания сверены с GrammarDB.</p>}
  </Sheet>;
}
