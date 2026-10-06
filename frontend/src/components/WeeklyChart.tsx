import type { Dashboard } from '../types';

export function WeeklyChart({ week }: { week: Dashboard['week'] }) {
  const max = Math.max(1, ...week.days.map(day => day.count));
  const word = week.total % 10 === 1 && week.total % 100 !== 11 ? 'слово' : week.total % 10 >= 2 && week.total % 10 <= 4 && !(week.total % 100 >= 12 && week.total % 100 <= 14) ? 'слова' : 'слов';
  return <section className="panel weekly" aria-labelledby="week-title">
    <h2 id="week-title"><strong>{week.total}</strong> {word} за неделю</h2>
    <div className="chart" role="img" aria-label={`За последние 7 дней изучено ${week.total} слов. ${week.days.map(day => `${day.label}: ${day.count}`).join('; ')}`}>
      {week.days.map(day => <div key={day.date} className={`chart-day ${day.isToday ? 'today' : ''}`} aria-hidden="true">
        <span className="chart-count">{day.count}</span><div className="chart-track"><div className={`chart-bar ${day.count === 0 ? 'zero' : ''}`} style={{ height: `${Math.max(day.count === 0 ? 3 : 10, day.count / max * 100)}%` }} /></div><span className="chart-label">{day.label}</span>
      </div>)}
    </div>
  </section>;
}
