import type { Leader } from '../types';
import { Icon } from './Icon';

export function Leaderboard({ leaders }: { leaders: Leader[] }) {
  return <section className="home-section" aria-labelledby="leaders-title"><h2 id="leaders-title">Рейтинг игроков</h2>
    {leaders.length ? <ol className="leaderboard">{leaders.map((person, index) => <li key={index} className={person.isMe ? 'is-me' : ''}>
      <span className="leader-rank">{person.rank}</span><span className="leader-name">{person.name}{person.isMe && <small>вы</small>}</span><span className="leader-balance">{person.balance.toLocaleString('ru-RU')} <span aria-label="бульбенов">🥔</span></span>
    </li>)}</ol> : <div className="leader-empty"><Icon name="chart" /><p>Рейтинг появится после первых игр</p></div>}
  </section>;
}
