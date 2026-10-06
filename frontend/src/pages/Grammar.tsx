import { useCallback, useMemo, useState } from 'react';
import type { Rule } from '../types';
import { useResource } from '../lib/useResource';
import { useTelegramBack } from '../lib/telegram';
import { Icon } from '../components/Icon';
import { Search } from '../components/Search';
import { EmptyState, ErrorState, Loading } from '../components/States';
import { RichText } from '../components/RichText';

export function Grammar({ active }: { active: boolean }) {
  const { data, loading, error, retry } = useResource<{ items: Rule[]; categories: string[] }>('/grammar');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [selected, setSelected] = useState<Rule | null>(null);
  const [scroll, setScroll] = useState(0);
  const back = useCallback(() => { setSelected(null); requestAnimationFrame(() => window.scrollTo({ top: scroll })); }, [scroll]);
  useTelegramBack(active && !!selected, back);
  const items = useMemo(() => (data?.items ?? []).filter(rule => (!category || rule.category === category) && (!query.trim() || JSON.stringify(rule).toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()))), [data, query, category]);
  if (loading) return <Loading label="Загружаем правила…" />;
  if (error) return <ErrorState error={error} retry={retry} />;
  if (selected) return <article className="rule-reader page-enter" key={selected.id}>
    <button className="back-button" onClick={back}><Icon name="back" />Все правила</button>
    <p className="detail-category">{selected.category}</p><h1>{selected.title}</h1>
    <div className="rule-content">{selected.content.map((block, index) => {
      if (block.type === 'heading') return <h2 key={index}>{block.text}</h2>;
      if (block.type === 'list') return <ul key={index}>{block.items.map((item, i) => <li key={i}><RichText text={item} /></li>)}</ul>;
      if (block.type === 'example') return <blockquote key={index}><RichText text={block.text} /></blockquote>;
      return <p key={index}><RichText text={block.text} /></p>;
    })}</div>
    {!!selected.sources.length && <div className="source-links"><h2>Полное правило</h2>{selected.sources.map(source => <a href={source.url} target="_blank" rel="noopener noreferrer" key={source.url}>{source.title}<Icon name="external" /></a>)}</div>}
    <button className="secondary full-width" onClick={back}>Вернуться к правилам</button>
  </article>;
  return <>
    <h1 className="sr-only">Грамматика</h1>
    <Search value={query} onChange={setQuery} placeholder="Найти правило" />
    <div className="filter-list" role="group" aria-label="Категория грамматики">
      {['', ...(data?.categories ?? [])].map(cat => <button key={cat} aria-pressed={category === cat} className={category === cat ? 'active' : ''} onClick={() => setCategory(cat)}>{cat || 'Все'}</button>)}
    </div>
    <div className="catalog-meta">{items.length} {items.length % 10 === 1 && items.length % 100 !== 11 ? 'правило' : items.length % 10 >= 2 && items.length % 10 <= 4 && !(items.length % 100 >= 12 && items.length % 100 <= 14) ? 'правила' : 'правил'}</div>
    {items.length ? <div className="catalog-list">{items.map(rule => <button className="catalog-row" key={rule.id} onClick={() => { setScroll(window.scrollY); setSelected(rule); window.scrollTo(0, 0); }}>
      <div><span className="row-title">{rule.title}</span>{!category && <span className="row-description">{rule.category}</span>}</div><Icon name="chevron" />
    </button>)}</div> : <EmptyState title="Ничего не нашлось" text="Попробуйте другой запрос или выберите «Все»" />}
  </>;
}
