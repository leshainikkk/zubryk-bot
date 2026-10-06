import { Icon } from './Icon';

export function Loading({ label = 'Загружаем…' }: { label?: string }) {
  return <div className="loading-state" role="status"><div className="loading-line" /><div className="loading-line short" /><span>{label}</span></div>;
}
export function ErrorState({ error, retry }: { error: Error; retry: () => void }) {
  return <div className="empty-state" role="alert"><Icon name="info" /><h2>Не получилось загрузить</h2><p>{error.message}</p><button className="primary" onClick={retry}>Попробовать ещё раз</button></div>;
}
export function EmptyState({ title, text }: { title: string; text?: string }) {
  return <div className="empty-state"><Icon name="search" /><h2>{title}</h2>{text && <p>{text}</p>}</div>;
}
