export default function PageHeader({ overline, title, actions, testid }) {
  return (
    <div className="border-b border-[#1F2A33] px-8 py-6 flex items-end justify-between flex-wrap gap-4" data-testid={testid}>
      <div>
        {overline && (
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-neutral-500 mb-1">{overline}</p>
        )}
        <h1 className="font-heading font-bold tracking-tight text-2xl sm:text-3xl">{title}</h1>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
