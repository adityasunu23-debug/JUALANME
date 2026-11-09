"use client";

import {
  BarChart3,
  Bell,
  Boxes,
  FolderTree,
  KeyRound,
  TrendingUp,
  DatabaseBackup,
  Inbox,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Megaphone,
  Package,
  ReceiptText,
  Send,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Store,
  Ticket,
  Truck,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Badge, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { cn, initials } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  permissions?: string[];
  ownerOnly?: boolean;
};

type NavGroup = { label: string; items: NavItem[] };

const NAV: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, permissions: ["dashboard.view"] },
      { href: "/analytics", label: "Analytics", icon: BarChart3, permissions: ["analytics.view"] },
    ],
  },
  {
    label: "Catalogue",
    items: [
      {
        href: "/catalog",
        label: "Products",
        icon: Package,
        permissions: ["products.manage", "categories.manage"],
      },
      {
        href: "/categories",
        label: "Categories",
        icon: FolderTree,
        permissions: ["categories.manage"],
      },
      { href: "/stock", label: "Stock", icon: Boxes, permissions: ["stock.manage"] },
    ],
  },
  {
    label: "Sales",
    items: [
      { href: "/orders", label: "Orders", icon: ShoppingCart, permissions: ["orders.manage"] },
      { href: "/deliveries", label: "Deliveries", icon: Truck, permissions: ["delivery.manage"] },
      { href: "/payments", label: "Payments", icon: ReceiptText, permissions: ["payments.view"] },
      { href: "/transactions", label: "Transactions", icon: Send, permissions: ["transactions.view"] },
      { href: "/vouchers", label: "Vouchers", icon: Ticket, permissions: ["vouchers.manage"] },
      {
        href: "/revenue",
        label: "Revenue reports",
        icon: TrendingUp,
        permissions: ["reports.view"],
      },
    ],
  },
  {
    label: "Customers",
    items: [
      { href: "/customers", label: "Customers", icon: Users, permissions: ["customers.manage"] },
      { href: "/tickets", label: "Support", icon: MessageSquare, permissions: ["tickets.manage"] },
      { href: "/broadcasts", label: "Broadcasts", icon: Megaphone, permissions: ["broadcast.manage"] },
    ],
  },
  {
    label: "System",
    items: [
      {
        href: "/api-config",
        label: "API configuration",
        icon: KeyRound,
        permissions: ["settings.manage"],
      },
      {
        href: "/notifications",
        label: "Notifications",
        icon: Bell,
        permissions: ["settings.manage"],
      },
      { href: "/settings", label: "Settings", icon: Settings, permissions: ["settings.manage"] },
      { href: "/admins", label: "Admins", icon: ShieldCheck, ownerOnly: true },
      { href: "/logs", label: "Audit logs", icon: Inbox, permissions: ["logs.view"] },
      { href: "/backups", label: "Backups", icon: DatabaseBackup, ownerOnly: true },
    ],
  },
];

const TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/analytics": "Analytics",
  "/catalog": "Catalogue",
  "/categories": "Categories",
  "/revenue": "Revenue reports",
  "/api-config": "API configuration",
  "/notifications": "Notifications",
  "/stock": "Stock",
  "/orders": "Orders",
  "/deliveries": "Deliveries",
  "/payments": "Payments",
  "/transactions": "Transactions",
  "/vouchers": "Vouchers",
  "/customers": "Customers",
  "/tickets": "Support",
  "/broadcasts": "Broadcasts",
  "/settings": "Settings",
  "/admins": "Admins",
  "/logs": "Audit logs",
  "/backups": "Backups",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { admin, loading, has, isOwner, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!loading && !admin) router.replace("/login");
  }, [admin, loading, router]);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const groups = useMemo(
    () =>
      NAV.map((group) => ({
        ...group,
        items: group.items.filter((item) => {
          if (item.ownerOnly) return isOwner;
          if (!item.permissions?.length) return true;
          return item.permissions.some((permission) => has(permission));
        }),
      })).filter((group) => group.items.length > 0),
    [has, isOwner]
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (!admin) return null;

  const displayName =
    [admin.first_name, admin.last_name].filter(Boolean).join(" ") ||
    admin.username ||
    `Admin ${admin.id}`;
  const botLink = process.env.NEXT_PUBLIC_BOT_USERNAME
    ? `https://t.me/${process.env.NEXT_PUBLIC_BOT_USERNAME.replace("@", "")}`
    : null;

  return (
    <div className="min-h-screen lg:flex">
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setOpen(false)}
          aria-hidden
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-white/5 bg-ink-900/95 transition-transform lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <Link href="/dashboard" className="flex items-center gap-3">
            <span className="rounded-xl bg-brand-500 p-2 text-ink-950">
              <Store className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-white">Telegram Store</p>
              <p className="text-[11px] text-slate-500">Admin console</p>
            </div>
          </Link>
          <button
            type="button"
            className="rounded-lg p-1 text-slate-400 hover:bg-white/5 lg:hidden"
            onClick={() => setOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 pb-6">
          {groups.map((group) => (
            <div key={group.label} className="mb-5">
              <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                {group.label}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const active =
                    pathname === item.href || pathname.startsWith(`${item.href}/`);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition",
                        active
                          ? "bg-brand-500/10 text-brand-200 shadow-[inset_0_0_0_1px_rgba(16,185,129,0.2)]"
                          : "text-slate-400 hover:bg-white/5 hover:text-white"
                      )}
                    >
                      <Icon className={cn("h-4 w-4", active && "text-brand-400")} />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-white/5 p-4">
          <div className="flex items-center gap-3 rounded-xl bg-white/[0.03] px-3 py-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-500/15 text-xs font-semibold text-brand-300">
              {initials(admin.first_name, admin.last_name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">{displayName}</p>
              <p className="truncate text-[11px] text-slate-500">{admin.role}</p>
            </div>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-rose-300"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-white/5 bg-ink-950/80 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="rounded-lg border border-white/10 p-2 text-slate-300 lg:hidden"
              aria-label="Open navigation"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-slate-500">Admin</p>
              <p className="text-sm font-medium text-white">
                {TITLES[pathname] || "Dashboard"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {botLink && (
              <a
                href={botLink}
                target="_blank"
                rel="noreferrer"
                className="hidden rounded-xl border border-white/10 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-white/5 sm:inline-flex"
              >
                Open bot
              </a>
            )}
            <Badge tone={admin.role === "OWNER" ? "violet" : "blue"}>{admin.role}</Badge>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
