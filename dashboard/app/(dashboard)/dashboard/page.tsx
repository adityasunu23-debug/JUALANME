"use client";

import {
  ArrowUpRight,
  Boxes,
  CircleDollarSign,
  MessageSquare,
  ShoppingCart,
  TrendingUp,
  Users,
} from "lucide-react";
import Link from "next/link";

import { RevenueChart } from "@/components/charts";
import {
  Badge,
  Card,
  EmptyState,
  Loading,
  PageHeader,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import { useApi } from "@/lib/use-api";
import { formatDate, money, number } from "@/lib/utils";

type SeriesPoint = { date: string; revenue: number; orders: number };
type NameValue = { name: string; value: number; extra?: number | null };

type Stats = {
  revenue_total: number;
  revenue_today: number;
  revenue_month: number;
  orders_total: number;
  orders_today: number;
  orders_pending: number;
  orders_paid: number;
  customers_total: number;
  customers_new_today: number;
  products_total: number;
  stock_available: number;
  tickets_open: number;
  conversion_rate: number;
  average_order_value: number;
  revenue_series: SeriesPoint[];
  orders_by_status: NameValue[];
  top_products: NameValue[];
  payment_methods: NameValue[];
  recent_orders: Array<{
    id: number;
    order_code: string;
    customer: string | null;
    product_name: string;
    total_amount: number;
    status: string;
    created_at: string | null;
  }>;
};

export default function DashboardPage() {
  const { data, loading, error } = useApi<Stats>("/stats/dashboard");

  if (loading) return <Loading label="Loading store overview…" />;
  if (error || !data) {
    return (
      <Card title="Dashboard unavailable">
        <p className="text-sm text-rose-300">{error || "Unable to load statistics."}</p>
      </Card>
    );
  }

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Live revenue, orders and support health across your bot."
        actions={
          <>
            <Link
              href="/orders"
              className="rounded-xl border border-white/10 px-3 py-2 text-xs text-slate-300 transition hover:bg-white/5"
            >
              View orders
            </Link>
            <Link
              href="/catalog"
              className="rounded-xl bg-brand-500 px-3 py-2 text-xs font-medium text-ink-950 transition hover:bg-brand-400"
            >
              Manage catalogue
            </Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Revenue today"
          value={money(data.revenue_today)}
          hint={`${money(data.revenue_month)} this month`}
          icon={<CircleDollarSign className="h-4 w-4" />}
        />
        <StatCard
          label="Total revenue"
          value={money(data.revenue_total)}
          hint={`AOV ${money(data.average_order_value)}`}
          icon={<TrendingUp className="h-4 w-4" />}
          tone="sky"
        />
        <StatCard
          label="Orders today"
          value={number(data.orders_today)}
          hint={`${number(data.orders_pending)} awaiting payment`}
          icon={<ShoppingCart className="h-4 w-4" />}
          tone="amber"
        />
        <StatCard
          label="Conversion"
          value={`${data.conversion_rate.toFixed(1)}%`}
          hint={`${number(data.orders_paid)} of ${number(data.orders_total)} orders paid`}
          icon={<ArrowUpRight className="h-4 w-4" />}
          tone="violet"
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card
          title="Revenue trend"
          subtitle="Paid orders over the last 14 days"
          className="lg:col-span-2"
        >
          <RevenueChart data={data.revenue_series} />
        </Card>

        <Card title="Operational snapshot">
          <div className="space-y-3">
            {[
              {
                label: "Customers",
                value: number(data.customers_total),
                hint: `+${number(data.customers_new_today)} today`,
                icon: Users,
              },
              {
                label: "Products",
                value: number(data.products_total),
                hint: `${number(data.stock_available)} stock items ready`,
                icon: Boxes,
              },
              {
                label: "Open tickets",
                value: number(data.tickets_open),
                hint: "Awaiting support reply",
                icon: MessageSquare,
              },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.label}
                  className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] px-3 py-3"
                >
                  <span className="rounded-lg bg-white/5 p-2 text-brand-300">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="flex-1">
                    <p className="text-xs text-slate-500">{item.label}</p>
                    <p className="text-sm font-medium text-white">{item.value}</p>
                  </div>
                  <p className="text-[11px] text-slate-500">{item.hint}</p>
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Orders by status">
          {data.orders_by_status.length === 0 ? (
            <EmptyState title="No orders yet" description="Orders will appear once customers start buying." />
          ) : (
            <ul className="space-y-2">
              {data.orders_by_status.map((row) => (
                <li
                  key={row.name}
                  className="flex items-center justify-between rounded-xl border border-white/5 px-3 py-2"
                >
                  <StatusBadge status={row.name} />
                  <span className="text-sm font-medium text-slate-200">{number(row.value)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Top products" subtitle="By revenue from paid orders">
          {data.top_products.length === 0 ? (
            <EmptyState title="No sales recorded" />
          ) : (
            <ul className="space-y-3">
              {data.top_products.map((product, index) => (
                <li key={product.name} className="flex items-center gap-3">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/5 text-[11px] text-slate-400">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-slate-200">{product.name}</p>
                    <p className="text-[11px] text-slate-500">
                      {number(product.value)} sold
                    </p>
                  </div>
                  <span className="text-xs font-medium text-brand-300">
                    {money(product.extra ?? 0)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Payment mix">
          {data.payment_methods.length === 0 ? (
            <EmptyState title="No paid invoices" />
          ) : (
            <ul className="space-y-2">
              {data.payment_methods.map((method) => (
                <li
                  key={method.name}
                  className="flex items-center justify-between rounded-xl border border-white/5 px-3 py-2"
                >
                  <span className="text-xs uppercase tracking-wide text-slate-400">
                    {method.name}
                  </span>
                  <Badge tone="green">{number(method.value)} paid</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card
        title="Recent orders"
        subtitle="Latest activity from the Telegram bot"
        className="mt-4"
        actions={
          <Link href="/orders" className="link text-xs">
            View all
          </Link>
        }
        bodyClassName="p-0"
      >
        {data.recent_orders.length === 0 ? (
          <div className="p-5">
            <EmptyState title="No orders yet" />
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_orders.map((order) => (
                  <tr key={order.id}>
                    <td>
                      <Link href={`/orders?focus=${order.id}`} className="font-mono text-xs text-brand-300">
                        {order.order_code}
                      </Link>
                    </td>
                    <td>{order.customer || "—"}</td>
                    <td className="max-w-[220px] truncate">{order.product_name}</td>
                    <td>{money(order.total_amount)}</td>
                    <td>
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="text-xs text-slate-500">{formatDate(order.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
