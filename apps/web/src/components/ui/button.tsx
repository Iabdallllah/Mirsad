import Link from "next/link";
import { type ButtonHTMLAttributes, type ComponentProps } from "react";

type Variant = "primary" | "secondary" | "ghost" | "destructive";

const BASE =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 text-sm font-medium " +
  "transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 " +
  "focus-visible:outline-none";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-secondary text-text hover:bg-secondary/90",
  secondary: "border border-border-strong bg-surface-1 text-text hover:bg-surface-2",
  ghost: "text-text-muted hover:bg-surface-2 hover:text-text",
  destructive: "border border-critical/60 bg-transparent text-critical hover:bg-critical/10",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant };

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return <button className={`${BASE} ${VARIANTS[variant]} ${className}`} {...props} />;
}

type ButtonLinkProps = ComponentProps<typeof Link> & { variant?: Variant };

export function ButtonLink({ variant = "primary", className = "", ...props }: ButtonLinkProps) {
  return <Link className={`${BASE} ${VARIANTS[variant]} ${className}`} {...props} />;
}
