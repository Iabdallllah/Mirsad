type AlertVariant = "info" | "warning" | "critical";

const STYLES: Record<AlertVariant, string> = {
  info: "border-info/40 bg-info/10 text-info",
  warning: "border-warning/40 bg-warning/10 text-warning",
  critical: "border-critical/40 bg-critical/10 text-critical",
};

type AlertProps = {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  role?: "status" | "alert";
};

/** Inline banner with explicit text (never color-only meaning). */
export function Alert({ variant = "info", title, children, role = "status" }: AlertProps) {
  return (
    <div role={role} className={`rounded-md border px-4 py-3 text-sm ${STYLES[variant]}`}>
      {title ? <p className="font-semibold">{title}</p> : null}
      <div className={title ? "mt-1" : ""}>{children}</div>
    </div>
  );
}
