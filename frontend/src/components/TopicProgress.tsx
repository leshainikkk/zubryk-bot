import type { WordTopic } from '../types';
import { Icon } from './Icon';

const topicIcon: Record<string, string> = { person: 'person', home_life: 'home', food: 'food' };
export function TopicProgress({ topics, onOpen }: { topics: WordTopic[]; onOpen?: (key: string) => void }) {
  return <section className="home-section" aria-labelledby="topics-title"><h2 id="topics-title">Темы</h2>
    <div className="topic-list">{topics.map(topic => <button className="topic-row" key={topic.key} onClick={() => onOpen?.(topic.key)} disabled={!onOpen} aria-label={`${topic.name}: ${topic.learned} из ${topic.total} слов. Продолжить в боте`}>
      <span className="topic-icon"><Icon name={topicIcon[topic.key] || 'book'} /></span><div className="topic-content">
        <div className="row-heading"><span>{topic.name}</span><small>{topic.learned}<span className="muted"> / {topic.total}</span></small></div>
        <div className="progress" role="progressbar" aria-label={topic.name} aria-valuenow={topic.learned} aria-valuemin={0} aria-valuemax={topic.total}><span style={{ width: `${topic.total ? Math.min(100, topic.learned / topic.total * 100) : 0}%` }} /></div>
      </div><Icon name="chevron" className="chevron" />
    </button>)}</div>
  </section>;
}
