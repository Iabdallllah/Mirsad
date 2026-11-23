type PageHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  menuButton?: React.ReactNode;
};

/** Light page header inside the content area (design.md §4.2). */
export function PageHeader({ title, subtitle, actions, menuButton }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex items-start gap-3">
        {menuButton}
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-text">{title}</h1>
          {subtitle ? <p className="mt-1 text-sm text-text-muted">{subtitle}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
