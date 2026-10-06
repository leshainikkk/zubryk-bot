export function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span aria-hidden="true" className={`icon ${className}`} style={{ maskImage: `url(/icons/${name}.svg)`, WebkitMaskImage: `url(/icons/${name}.svg)` }} />;
}
