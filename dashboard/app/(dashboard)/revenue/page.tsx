"use client";

import { Coins, Download, Percent, ReceiptText, TrendingUp, Wallet } from "lucide-react";
import { useMemo, useState } from "react";

import { BarList, RevenueChart } from "@/components/charts";
import {
  Button,
  Card,
  EmptyState,
  Loading,
  PageHeader,
  Select,
  StatCard,
} from "@/components/ui";
import { useApi } from "@/lib/use-api";
import { formatDate, money, number } from "@/lib/utils";

type SeriesPoint = { date: string; revenue: number; orders: number };
type NameValue = { name: string; value: number; extra?: number | null };

type RevenueReport = {
  period: string;
  gross_revenue: number;
  net_revenue: number;
  total_orders: number;
  paid_orders: number;
  refunded_amount: number;
  discount_total: number;
  average_order_value: number;
  daily: SeriesPoint[];
  by_product: NameValue[];
  by_category: NameValue[];
};

const PERIODS = [
  { value: "today", label: "Today" },
  { value: "week", label: "Last 7 days" },
  { value: "month", label: "This month" },
  { value: "year", label: "This year" },
  { value: "all", label: "All time" },
];

export default function RevenuePage() {
  const [period, setPeriod] = useState("month");
  const { data, loading, error } = useApi<RevenueReport>(
    `/reports/revenue?period=${period}`,
    [period]
  );

  const daily = useMemo(
    () =>
      [...(data?.daily ?? [])]
        .reverse()
        .slice(0, 14),
    [data]
  );

  function exportCsv() {
    if (!data) return;
    const rows: string[] = ["date,revenue,orders"];
    data.daily.forEach((point) => {
      rows.push(`${point.date},${point.revenue},${point.orders}`);
    });
    const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `revenue-${data.period}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <PageHeader
        title="Revenue reports"
        description="Gross and net revenue, discounts and the products that drive them."
        actions={
          <>
            <Select
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              className="w-40"
            >
              {PERIODS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            <Button onClick={exportCsv} disabled={!data}>
              <Download className="h-4 w-4" /> Export CSV
            </Button>
          </>
        }
      />

      {loading ? (
        <Loading label="Building revenue report..." />
      ) : error ? (
        <p className="text-sm text-rose-300">{error}</p>
      ) : !data ? (
        <EmptyState title="No report data" />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Gross revenue"
              value={money(data.gross_revenue)}
              hint={`${number(data.total_orders)} orders in range`}
              icon={<Coins className="h-4 w-4" />}
            />
            <StatCard
              label="Net revenue"
              value={money(data.net_revenue)}
              hint={`${number(data.paid_orders)} paid orders`}
              tone="sky"
              icon={<Wallet className="h-4 w-4" />}
            />
            <StatCard
              label="Average order"
              value={money(data.average_order_value)}
              hint="Per paid order"
              tone="amber"
              icon={<TrendingUp className="h-4 w-4" />}
            />
            <StatCard
              label="Discounts given"
              value={money(data.discount_total)}
              hint={`Refunds ${money(data.refunded_amount)}`}
              tone="violet"
              icon={<Percent className="h-4 w-4" />}
            />
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <Card
              title="Revenue trend"
              subtitle={`Period: ${data.period}`}
              className="xl:col-span-2"
            >
              <RevenueChart data={data.daily} />
            </Card>

            <Card title="Top products" subtitle="By revenue in range">
              <BarList
                items={data.by_product.slice(0, 8)}
                formatValue={(value) => money(value)}
              />
            </Card>
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <Card title="Revenue by category">
              <BarList
                items={data.by_category.slice(0, 8)}
                formatValue={(value) => money(value)}
              />
            </Card>

            <Card
              title="Daily breakdown"
              subtitle="Most recent 14 days"
              className="xl:col-span-2"
              bodyClassName="p-0"
            >
              {daily.length === 0 ? (
                <div className="p-5">
                  <EmptyState title="No daily data" />
                </div>
              ) : (
                <div className="table-wrap">
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Orders</th>
                        <th className="text-right">Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {daily.map((point) => (
                        <tr key={point.date}>
                          <td className="text-sm text-slate-300">
                            {formatDate(point.date, false)}
                          </td>
                          <td className="text-sm text-slate-400">
                            {number(point.orders)}
                          </td>
                          <td className="text-right text-sm font-medium text-white">
                            {money(point.revenue)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>

          <Card title="Summary" className="mt-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">
                  Total orders
                </p>
                <p className="mt-1 text-lg font-semibold text-white">
                  {number(data.total_orders)}
                </p>
              </div>
              <div className="rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">
                  Paid orders
                </p>
                <p className="mt-1 text-lg font-semibold text-white">
                  {number(data.paid_orders)}
                </p>
              </div>
              <div className="rounded-xl border border-white/5 bg-white/[0.02] px-4 py-3">
                <p className="text-[11px] uppercase tracking-wide text-slate-500">
                  Conversion
                </p>
                <p className="mt-1 text-lg font-semibold text-white">
                  {data.total_orders
                    ? `${((data.paid_orders / data.total_orders) * 100).toFixed(1)}%`
                    : "0%"}
                </p>
              </div>
            </div>
            <p className="mt-4 flex items-center gap-2 text-xs text-slate-500">
              <ReceiptText className="h-3.5 w-3.5" />
              Revenue is counted from orders in PAID, DELIVERED or COMPLETED state.
            </p>
          </Card>
        </>
      )}
    </>
  );
}