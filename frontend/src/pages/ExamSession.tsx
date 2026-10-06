import { useState } from 'react';
import type { AnswerResult, ExamTopic, Question } from '../types';
import { api } from '../lib/api';
import { useResource } from '../lib/useResource';
import { isTelegram } from '../lib/telegram';
import { haptic } from '../lib/haptics';
import { Icon } from '../components/Icon';
import { ErrorState, Loading } from '../components/States';

export function ExamSession({ topic, onBack }: { topic: ExamTopic; onBack: () => void }) {
  const { data, loading, error, retry } = useResource<{ items: Question[]; variants: string[] }>(`/exam/topics/${topic.id}/questions`);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [choices, setChoices] = useState<Record<string, string[]>>({});
  const [results, setResults] = useState<Record<string, AnswerResult>>({});
  const [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState('');
  const [complete, setComplete] = useState(false);
  if (loading) return <Loading label="Готовим упражнение…" />;
  if (error) return <ErrorState error={error} retry={retry} />;
  if (!data?.items.length) return <div className="empty-state"><h2>Задания скоро появятся</h2><button className="secondary" onClick={onBack}>Все темы</button></div>;
  const items = data.items;
  const question = items.find(item => item.id === selectedId) ?? items.find(item => !item.attempt) ?? items[0];
  const result = results[question.id] ?? question.attempt;
  const answers = result?.answers ?? choices[question.id] ?? [];
  const answered = (item: Question) => results[item.id] ?? item.attempt;
  const solvedCount = items.filter(answered).length;
  const correctCount = items.filter(item => answered(item)?.correct).length;
  async function check() {
    setChecking(true); setCheckError('');
    try {
      const next = await api<AnswerResult>(`/exam/questions/${question.id}/check`, { method: 'POST', body: JSON.stringify({ answers, preview: !isTelegram() }) });
      setResults(current => ({ ...current, [question.id]: next }));
      haptic(next.correct ? 'success' : 'error');
    } catch (err) { setCheckError((err as Error).message); }
    finally { setChecking(false); }
  }
  function next() {
    const candidate = items.find(item => item.variantId !== question.variantId && !answered(item)) ?? items.find(item => item.id !== question.id && !answered(item));
    setCheckError('');
    if (candidate) setSelectedId(candidate.id);
    else setComplete(true);
    window.scrollTo(0, 0);
  }
  if (complete) return <div className="exam-complete page-enter"><button className="back-button" onClick={onBack}><Icon name="back" />Все темы</button><div className="complete-mark"><Icon name="check" /></div><h1>Добрая праца!</h1><p>Вы разобрали все задания этой темы.</p><div className="result-summary"><strong>{correctCount}<span> / {solvedCount}</span></strong><span>правильных ответов</span></div><button className="primary full-width" onClick={onBack}>Выбрать другую тему<Icon name="arrow" /></button></div>;
  return <div className="exam-session">
    <button className="back-button" onClick={onBack}><Icon name="back" />Все темы</button><h1 className="exam-title">{topic.title}</h1>
    <div className="variant-picker" role="group" aria-label="Вариант задания">{data.variants.map((variant, index) => <button key={variant} aria-pressed={variant === question.variantId} className={variant === question.variantId ? 'active' : ''} disabled={checking} onClick={() => { setSelectedId(items.find(item => item.variantId === variant && !answered(item))?.id ?? items.find(item => item.variantId === variant)!.id); setCheckError(''); }}>Вариант {index + 1}</button>)}</div>
    <div className="question-meta">Задание {items.indexOf(question) + 1} из {items.length}<span>{question.type === 'multiple' ? 'Несколько ответов' : 'Один ответ'}</span></div>
    <section className="question-body page-enter" key={question.id}><h2>{question.prompt}</h2>{question.materials.map((text, index) => <p className="question-material" key={index}>{text}</p>)}
      <fieldset className="answer-options" disabled={checking || !!result}><legend className="sr-only">Выберите ответ</legend>{question.options.map(option => {
        const chosen = answers.includes(option.id);
        const correct = result?.correctAnswers.includes(option.id);
        const wrong = result && chosen && !correct;
        return <label key={option.id} className={`answer-option ${chosen ? 'chosen' : ''} ${correct ? 'correct' : ''} ${wrong ? 'wrong' : ''}`}>
          <input type={question.type === 'multiple' ? 'checkbox' : 'radio'} name={`answer-${question.id}`} value={option.id} checked={chosen} onChange={() => {
            setChoices(current => ({ ...current, [question.id]: question.type === 'single' ? [option.id] : chosen ? answers.filter(answer => answer !== option.id) : [...answers, option.id] }));
          }} /><span className="answer-text">{option.text}</span>
          {!!result && <span className="answer-state">{correct ? <><Icon name="check" /><span>Верно</span></> : wrong ? <><Icon name="close" /><span>Ваш ответ</span></> : null}</span>}
        </label>;
      })}</fieldset>
    </section>
    {checkError && <p className="form-error" role="alert">{checkError}</p>}
    {result ? <><div className={`answer-feedback ${result.correct ? 'success' : 'error'}`} role="status"><div><Icon name={result.correct ? 'check' : 'info'} /><h3>{result.correct ? 'Правильно!' : 'Есть ошибка'}</h3></div><p>{result.explanation || `Верный ответ: ${question.options.filter(option => result.correctAnswers.includes(option.id)).map(option => option.text).join(', ')}`}</p></div><button className="primary full-width" onClick={next}>{solvedCount === items.length ? 'Посмотреть результат' : 'Следующее задание'}<Icon name="arrow" /></button></>
      : <button className="primary full-width" disabled={!answers.length || checking} onClick={check}>{checking ? 'Проверяем…' : 'Проверить'}</button>}
    <p className="exercise-source">{question.source}</p>
  </div>;
}
