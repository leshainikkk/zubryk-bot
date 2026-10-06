import { useCallback, useState } from 'react';
import type { ExamTopic } from '../types';
import { useResource } from '../lib/useResource';
import { useTelegramBack } from '../lib/telegram';
import { Icon } from '../components/Icon';
import { Search } from '../components/Search';
import { EmptyState, ErrorState, Loading } from '../components/States';
import { ExamSession } from './ExamSession';

export function Tests({ active }: { active: boolean }) {
  const { data, error, loading, retry } = useResource<{ items: ExamTopic[]; notice: string }>('/exam/topics');
  const [query, setQuery] = useState('');
  const [topic, setTopic] = useState<ExamTopic | null>(null);
  const back = useCallback(() => { setTopic(null); window.scrollTo(0, 0); }, []);
  useTelegramBack(active && !!topic, back);
  if (loading) return <Loading label="Загружаем задания…" />;
  if (error) return <ErrorState error={error} retry={retry} />;
  if (topic) return <ExamSession key={topic.id} topic={topic} onBack={back} />;
  const items = (data?.items ?? []).filter(item => `${item.title} ${item.description}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  return <>
    <h1 className="sr-only">Подготовка к ЦТ / ЦЭ</h1>
    <Search value={query} onChange={setQuery} placeholder="Найти тему" />
    <p className="exam-notice"><Icon name="info" /><span>{data?.notice}</span></p>
    {items.length ? <div className="exam-catalog">{items.map(item => <button className="exam-topic" key={item.id} onClick={() => { setTopic(item); window.scrollTo(0, 0); }}>
      <span className="exam-topic-icon"><Icon name={item.icon} /></span><div><span className="row-title">{item.title}</span><span className="row-description">{item.description}</span><span className="row-footnote">{item.questionCount} заданий · {item.variants.length} варианта</span></div><Icon name="chevron" />
    </button>)}</div> : <EmptyState title="Ничего не нашлось" text="Попробуйте поиск по названию темы" />}
  </>;
}
