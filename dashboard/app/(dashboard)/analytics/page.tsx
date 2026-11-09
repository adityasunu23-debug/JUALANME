"use client";

import { useMemo, useState } from "react";

import { BarList, MiniBars, RevenueChart, type SeriesPoint } from "@/components/charts";
import {
  Card,
  EmptyState,
  Loading,
  PageHeader,
  Select,
  StatCard,
} from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/use-api";
import { money, number } from "@/lib/utils";

type NameValue = { name: string; value: number; extra?: number | null };

type Analytics = {
  revenue_series: SeriesPoint[];
  orders_by_status: NameValue[];
  category_revenue: NameValue[];
  top_products: NameValue[];
  customer_growth: SeriesPoint[];
  delivery_breakdown: NameValue[];
};

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

export default function AnalyticsPage() {
  const { has } = useAuth();
  const [days, setDays] = useState(30);
  const [period, setPeriod] = useState("month");

  const analyticsApi = useApi<Analytics>(`/analytics?days=${days}`);
  const reportApi = useApi<RevenueReport>(
    has("reports.view") ? `/reports/revenue?period=${period}` : null,
    [period]
  );
  const data = analyticsApi.data;

  const totals = useMemo(() => {
    if (!data) return { revenue: 0, orders: 0, customers: 0 };
    return {
      revenue: data.revenue_series.reduce((sum, point) => sum + Number(point.revenue), 0),
      orders: data.revenue_series.reduce((sum, point) => sum + Number(point.orders), 0),
      customers: data.customer_growth.reduce((sum, point) => sum + Number(point.orders), 0),
    };
  }, [data]);

  if (analyticsApi.loading) return <Loading label="Crunching analytics…" />;
  if (analyticsApi.error || !data) {
    return (
      <Card title="Analytics unavailable">
        <p className="text-sm text-rose-300">{analyticsApi.error || "No data available."}</p>
      </Card>
    );
  }

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Understand growth, category performance and delivery reliability."
        actions={
          <Select value={String(days)} onChange={(e) => setDays(Number(e.target.value))} className="w-40">
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="180">Last 180 days</option>
            <option value="365">Last year</option>
          </Select>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Revenue in range" value={money(totals.revenue)} hint={`${days} day window`} />
        <StatCard label="Paid orders" value={number(totals.orders)} tone="sky" hint="Orders settled in range" />
        <StatCard label="New customers" value={number(totals.customers)} tone="violet" hint="Registrations in range" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Revenue series" className="lg:col-span-2" subtitle="Daily revenue from paid orders">
          <RevenueChart data={data.revenue_series} />
        </Card>
        <Card title="Customer growth" subtitle="New customers per day">
          <MiniBars data={data.customer_growth} />
          <div className="mt-4 space-y-2 text-xs text-slate-500">
            <div className="flex justify-between">
              <span>First day</span>
              <span>{number(data.customer_growth[0]?.orders ?? 0)} new</span>
            </div>
            <div className="flex justify-between">
              <span>Latest day</span>
              <span>{number(data.customer_growth[data.customer_growth.length - 1]?.orders ?? 0)} new</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Revenue by category">
          <BarList items={data.category_revenue} formatValue={(value) => money(value)} />
        </Card>
        <Card title="Top products">
          <BarList
            items={data.top_products}
            formatValue={(value) => `${number(value)} sold`}
          />
        </Card>
        <Card title="Delivery breakdown">
          {data.delivery_breakdown.length === 0 ? (
            <EmptyState title="No delivery data" />
          ) : (
            <ul className="space-y-2">
              {data.delivery_breakdown.map((row) => (
                <li
                  key={row.name}
                  className="flex items-center justify-between rounded-xl border border-white/5 px-3 py-2 text-sm"
                >
                  <span className="text-slate-300">{row.name.replace(/_/g, " ")}</span>
                  <span className="font-medium text-slate-100">{number(row.value)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {has("reports.view") && (
        <Card
          title="Revenue report"
          subtitle="Financial summary with discounts and refunds"
          className="mt-4"
          actions={
            <Select value={period} onChange={(e) => setPeriod(e.target.value)} className="w-40">
              <option value="today">Today</option>
              <option value="week">This week</option>
              <option value="month">This month</option>
              <option value="year">This year</option>
              <option value="all">All time</option>
            </Select>
          }
        >
          {reportApi.loading ? (
            <Loading label="Loading report…" />
          ) : reportApi.error || !reportApi.data ? (
            <p className="text-sm text-rose-300">{reportApi.error || "Unable to load report."}</p>
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  { label: "Gross revenue", value: money(reportApi.data.gross_revenue) },
                  { label: "Net revenue", value: money(reportApi.data.net_revenue) },
                  { label: "Paid orders", value: `${number(reportApi.data.paid_orders)} / ${number(reportApi.data.total_orders)}` },
                  { label: "Average order", value: money(reportApi.data.average_order_value) },
                  { label: "Discounts", value: money(reportApi.data.discount_total) },
                  { label: "Refunds", value: money(reportApi.data.refunded_amount) },
                ].map((item) => (
                  <div key={item.label} className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                    <p className="text-[11px] uppercase tracking-wide text-slate-500">{item.label}</p>
                    <p className="mt-1 text-sm font-medium text-white">{item.value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div>
                  <p className="mb-2 text-xs font-medium text-slate-300">Revenue by product</p>
                  <BarList items={reportApi.data.by_product} formatValue={(value) => money(value)} />
                </div>
                <div>
                  <p className="mb-2 text-xs font-medium text-slate-300">Revenue by category</p>
                  <BarList items={reportApi.data.by_category} formatValue={(value) => money(value)} />
                </div>
              </div>
            </>
          )}
        </Card>
      )}
    </>
  );
}
