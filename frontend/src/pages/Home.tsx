import { useState } from 'react';
import type { Dashboard } from '../types';
import { ApiError } from '../lib/api';
import { openBot, telegram } from '../lib/telegram';
import { Icon } from '../components/Icon';
import { WeeklyChart } from '../components/WeeklyChart';
import { TopicProgress } from '../components/TopicProgress';
import { Leaderboard } from '../components/Leaderboard';
import { ErrorState, Loading } from '../components/States';
import { Sheet } from '../components/Sheet';

export function Home({ data, loading, error, retry, onSettings }: { data: Dashboard | null; loading: boolean; error: Error | null; retry: () => void; onSettings: () => void }) {
  const [balanceOpen, setBalanceOpen] = useState(false);
  if (loading && !data) return <Loading label="Загружаем ваш прогресс…" />;
  if (error instanceof ApiError && error.status === 404) return <div className="empty-state"><Icon name="person" /><h1>Прывітанне!</h1><p>Создайте профиль через /start в боте. Здесь появится ваш прогресс.</p><button className="primary" onClick={() => telegram()?.close()}>Вернуться в бот</button><button className="text-button" onClick={retry}>Профиль уже создан</button></div>;
  if (error) return <ErrorState error={error} retry={retry} />;
  if (!data) return null;
  const profile = data.profile;
  const initials = profile?.name.split(/\s+/).filter(Boolean).slice(0, 2).map(word => Array.from(word)[0]).join('').toUpperCase();
  return <>
    <header className="topbar">
      <div className="topbar-left"><button className="icon-button settings-button" onClick={onSettings} aria-label="Настройки"><Icon name="settings" /></button>
        <button className="balance-pill" onClick={() => setBalanceOpen(true)} aria-label={profile ? `Баланс: ${profile.balance} бульбенов` : 'Бульбены: войдите через Telegram'}><span aria-hidden="true">🥔</span><strong>{profile?.balance.toLocaleString('ru-RU') ?? '—'}</strong></button>
      </div>
      <div className="topbar-right"><div className="streak" aria-label={`Серия: ${profile?.streak ?? 0} дней`}><strong>{profile?.streak ?? '—'}</strong><span aria-hidden="true">🔥</span></div>
        <button className="avatar" onClick={onSettings} aria-label="Мой профиль">{profile?.photoUrl ? <img src={profile.photoUrl} alt="" referrerPolicy="no-referrer" onError={event => { event.currentTarget.hidden = true; }} /> : null}<span>{initials || <Icon name="person" />}</span></button>
      </div>
    </header>
    <h1 className="greeting">Прывітанне{profile ? ',\n' : '!'}{profile && <span>{profile.name}!</span>}</h1>
    {data.preview && <button className="preview-note" onClick={() => openBot(data.botUsername)}><span>Откройте в Telegram,<br />чтобы видеть свой прогресс</span><Icon name="arrow" /></button>}
    <WeeklyChart week={data.week} />
    <TopicProgress topics={data.topics} onOpen={data.botUsername ? key => openBot(data.botUsername, `study_${key}`) : undefined} />
    <Leaderboard leaders={data.leaders} />
    <Sheet open={balanceOpen} onClose={() => setBalanceOpen(false)} title={profile ? 'Ваши бульбены' : 'Бульбены'}>
      <div className="balance-large">{profile?.balance.toLocaleString('ru-RU') ?? '—'} <span>🥔</span></div><p>Бульбены — награда за игры с друзьями. Правильный ответ приносит 1 🥔, победа — ещё 30 🥔.</p>
      <button className="primary full-width" onClick={() => openBot(data.botUsername, 'play')}>Играть с друзьями<Icon name="arrow" /></button>
    </Sheet>
  </>;
}
