import { Icon } from './Icon';

export function Search({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return <div className="search"><Icon name="search" /><input type="search" aria-label={placeholder} placeholder={placeholder} value={value} onChange={event => onChange(event.target.value)} autoComplete="off" />
    {value && <button className="icon-button clear" onClick={() => onChange('')} aria-label="Очистить поиск"><Icon name="close" /></button>}
  </div>;
}
