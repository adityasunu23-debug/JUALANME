"use client";

import { Loader2, Search, X } from "lucide-react";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

import { cn, humanize } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* Buttons                                                             */
/* ------------------------------------------------------------------ */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success";

const buttonStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-500 text-ink-950 hover:bg-brand-400 focus-visible:ring-brand-400/40",
  secondary:
    "border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10 focus-visible:ring-white/20",
  ghost: "text-slate-300 hover:bg-white/5 hover:text-white focus-visible:ring-white/20",
  danger:
    "bg-rose-500/90 text-white hover:bg-rose-500 focus-visible:ring-rose-400/40",
  success:
    "bg-emerald-500/90 text-ink-950 hover:bg-emerald-400 focus-visible:ring-emerald-400/40",
};

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  loading?: boolean;
}) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm",
        buttonStyles[variant],
        className
      )}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  );
}

/* ------------------------------------------------------------------ */
/* Form controls                                                       */
/* ------------------------------------------------------------------ */

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn("field", className)} />;
}

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cn("field min-h-[92px] resize-y", className)} />;
}

export function Select({ className, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...props} className={cn("field appearance-none pr-8", className)}>
      {children}
    </select>
  );
}

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label?: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("block", className)}>
      {label && <span className="label">{label}</span>}
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export function SearchField({
  value,
  onChange,
  placeholder = "Search…",
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <div className={cn("relative", className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="field pl-9"
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Layout primitives                                                   */
/* ------------------------------------------------------------------ */

export function Card({
  title,
  subtitle,
  actions,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("panel", className)}>
      {(title || actions) && (
        <div className="panel-head">
          <div>
            {title && <h2 className="text-base font-semibold text-white">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={cn("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-400">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = "brand",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
  tone?: "brand" | "sky" | "amber" | "rose" | "violet";
}) {
  const tones = {
    brand: "from-brand-500/15 text-brand-300",
    sky: "from-sky-500/15 text-sky-300",
    amber: "from-amber-500/15 text-amber-300",
    rose: "from-rose-500/15 text-rose-300",
    violet: "from-violet-500/15 text-violet-300",
  };
  return (
    <div className={cn("panel relative overflow-hidden p-5")}>
      <div
        className={cn(
          "pointer-events-none absolute inset-x-0 top-0 h-20 bg-gradient-to-b to-transparent",
          tones[tone]
        )}
      />
      <div className="relative flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
          {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
        </div>
        {icon && (
          <span className={cn("rounded-xl border border-white/5 bg-white/5 p-2", tones[tone])}>
            {icon}
          </span>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Badges                                                              */
/* ------------------------------------------------------------------ */

type BadgeTone = "green" | "amber" | "red" | "blue" | "gray" | "violet";

const badgeStyles: Record<BadgeTone, string> = {
  green: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  amber: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  red: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  blue: "border-sky-500/30 bg-sky-500/10 text-sky-300",
  gray: "border-white/10 bg-white/5 text-slate-400",
  violet: "border-violet-500/30 bg-violet-500/10 text-violet-300",
};

export function Badge({
  children,
  tone = "gray",
  className,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        badgeStyles[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function statusTone(status?: string | null): BadgeTone {
  const value = (status || "").toUpperCase();
  if (["PAID", "COMPLETED", "DELIVERED", "SENT", "ANSWERED", "SUCCESS", "ACTIVE"].includes(value)) {
    return "green";
  }
  if (["PENDING", "PENDING_PAYMENT", "CONFIRMING", "QUEUED", "SENDING", "PROCESSING", "OPEN", "UNDERPAID", "UPCOMING"].includes(value)) {
    return "amber";
  }
  if (["FAILED", "CANCELLED", "EXPIRED", "BLOCKED", "CLOSED", "ERROR"].includes(value)) {
    return "red";
  }
  if (["OVERPAID", "REFUNDED"].includes(value)) return "blue";
  if (["OWNER", "SUPER_ADMIN"].includes(value)) return "violet";
  return "gray";
}

export function StatusBadge({ status }: { status?: string | null }) {
  return <Badge tone={statusTone(status)}>{humanize(status)}</Badge>;
}

/* ------------------------------------------------------------------ */
/* Modal                                                               */
/* ------------------------------------------------------------------ */

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
}) {
  useEffect(() => {
    if (!open) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  const widths = {
    sm: "max-w-md",
    md: "max-w-xl",
    lg: "max-w-3xl",
    xl: "max-w-5xl",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm sm:items-center">
      <div className="absolute inset-0" onClick={onClose} aria-hidden />
      <div
        className={cn(
          "panel relative my-8 w-full animate-in border-white/10 bg-ink-900",
          widths[size]
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/5 px-5 py-4">
          <div>
            <h3 className="text-base font-semibold text-white">{title}</h3>
            {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 transition hover:bg-white/5 hover:text-white"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex flex-wrap justify-end gap-2 border-t border-white/5 px-5 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Misc                                                                */
/* ------------------------------------------------------------------ */

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-5 w-5 animate-spin text-brand-400", className)} />;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-500">
      <Spinner />
      {label}
    </div>
  );
}

export function EmptyState({
  title = "Nothing here yet",
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-white/10 px-6 py-12 text-center">
      <p className="text-sm font-medium text-slate-300">{title}</p>
      {description && <p className="max-w-sm text-xs text-slate-500">{description}</p>}
      {action}
    </div>
  );
}

export function Pagination({
  page,
  totalPages,
  total,
  onChange,
}: {
  page: number;
  totalPages: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (total <= 0) return null;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-3 text-xs text-slate-500">
      <span>
        Page {page} of {Math.max(totalPages, 1)} · {total} record{total === 1 ? "" : "s"}
      </span>
      <div className="flex gap-2">
        <Button size="sm" onClick={() => onChange(page - 1)} disabled={page <= 1}>
          Previous
        </Button>
        <Button
          size="sm"
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tabs                                                                */
/* ------------------------------------------------------------------ */

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: Array<{ value: T; label: string; count?: number }>;
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-xl border border-white/5 bg-ink-850 p-1">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          type="button"
          onClick={() => onChange(tab.value)}
          className={cn(
            "rounded-lg px-3 py-1.5 text-xs font-medium transition",
            value === tab.value
              ? "bg-brand-500 text-ink-950"
              : "text-slate-400 hover:bg-white/5 hover:text-white"
          )}
        >
          {tab.label}
          {typeof tab.count === "number" && (
            <span className="ml-1.5 opacity-70">{tab.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Confirm dialog helper                                               */
/* ------------------------------------------------------------------ */

export function useConfirm() {
  return useMemo(
    () =>
      (message: string): boolean => {
        if (typeof window === "undefined") return false;
        return window.confirm(message);
      },
    []
  );
}

/* ------------------------------------------------------------------ */
/* Simple JSON editor helper                                           */
/* ------------------------------------------------------------------ */

export function JsonBlock({ value }: { value: unknown }) {
  const [expanded, setExpanded] = useState(false);
  const text = useMemo(() => JSON.stringify(value, null, 2) ?? "null", [value]);
  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="link text-xs"
      >
        {expanded ? "Hide JSON" : "Show JSON"}
      </button>
      {expanded && (
        <pre className="mt-2 max-h-72 overflow-auto rounded-xl border border-white/5 bg-ink-950 p-3 text-xs text-slate-400">
          {text}
        </pre>
      )}
    </div>
  );
}

/* Small context helper used by pages that want a compact info grid */
export function InfoGrid({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
          <dt className="text-[11px] uppercase tracking-wide text-slate-500">{item.label}</dt>
          <dd className="mt-1 break-words text-sm text-slate-200">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
