import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { Icon } from './Icon';
import { useTelegramBack } from '../lib/telegram';

export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useTelegramBack(open, onClose, 10);
  useEffect(() => {
    const dialog = ref.current;
    if (open && dialog && !dialog.open) dialog.showModal();
    if (!open && dialog?.open) dialog.close();
    if (open) {
      const previous = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = previous; };
    }
  }, [open]);
  return <dialog ref={ref} className="sheet" aria-labelledby={id} onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="sheet-inner"><div className="sheet-heading"><h2 id={id}>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Закрыть"><Icon name="close" /></button></div>{children}</div>
  </dialog>;
}
