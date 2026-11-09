"use client";

import { useMemo } from "react";

import { cn, money, shortDate } from "@/lib/utils";

export type SeriesPoint = { date: string; revenue: number; orders?: number };

export function RevenueChart({
  data,
  className,
  height = 220,
}: {
  data: SeriesPoint[];
  className?: string;
  height?: number;
}) {
  const chart = useMemo(() => {
    const width = 720;
    const padX = 8;
    const padY = 16;
    const points = data.length ? data : [{ date: "", revenue: 0 }];
    const max = Math.max(...points.map((point) => Number(point.revenue) || 0), 1);
    const stepX = points.length > 1 ? (width - padX * 2) / (points.length - 1) : 0;
    const coords = points.map((point, index) => {
      const x = padX + index * stepX;
      const y = height - padY - ((Number(point.revenue) || 0) / max) * (height - padY * 2);
      return { x, y, point };
    });
    const line = coords
      .map((coord, index) => `${index === 0 ? "M" : "L"}${coord.x.toFixed(1)},${coord.y.toFixed(1)}`)
      .join(" ");
    const area = `${line} L${coords[coords.length - 1].x.toFixed(1)},${height - padY} L${coords[0].x.toFixed(1)},${height - padY} Z`;
    return { width, height, coords, line, area, max };
  }, [data, height]);

  if (!data.length) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-slate-500">
        No revenue data yet
      </div>
    );
  }

  const total = data.reduce((sum, point) => sum + (Number(point.revenue) || 0), 0);
  const last = data[data.length - 1];

  return (
    <div className={cn("relative", className)}>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Revenue in range</p>
          <p className="text-xl font-semibold text-white">{money(total)}</p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <p>Latest day</p>
          <p className="font-medium text-brand-300">{money(last?.revenue)}</p>
        </div>
      </div>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        className="h-52 w-full"
        preserveAspectRatio="none"
        role="img"
        aria-label="Revenue chart"
      >
        <defs>
          <linearGradient id="revenueFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((fraction) => (
          <line
            key={fraction}
            x1="0"
            x2={chart.width}
            y1={chart.height * fraction}
            y2={chart.height * fraction}
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="1"
          />
        ))}
        <path d={chart.area} fill="url(#revenueFill)" />
        <path d={chart.line} fill="none" stroke="#34d399" strokeWidth="2.5" strokeLinecap="round" />
        {chart.coords.map((coord, index) => (
          <circle
            key={`${coord.point.date}-${index}`}
            cx={coord.x}
            cy={coord.y}
            r={data.length > 30 ? 1.6 : 2.6}
            fill="#34d399"
          >
            <title>
              {shortDate(coord.point.date)}: {money(coord.point.revenue)}
            </title>
          </circle>
        ))}
      </svg>
      <div className="mt-1 flex justify-between text-[10px] text-slate-600">
        <span>{shortDate(data[0]?.date)}</span>
        <span>{shortDate(data[data.length - 1]?.date)}</span>
      </div>
    </div>
  );
}

export function BarList({
  items,
  formatValue = (value: number) => String(value),
  className,
}: {
  items: Array<{ name: string; value: number; extra?: number | null }>;
  formatValue?: (value: number) => string;
  className?: string;
}) {
  const max = Math.max(...items.map((item) => Number(item.value) || 0), 1);
  if (!items.length) {
    return <p className="py-6 text-center text-sm text-slate-500">No data yet</p>;
  }
  return (
    <div className={cn("space-y-3", className)}>
      {items.map((item) => (
        <div key={item.name}>
          <div className="mb-1 flex items-center justify-between gap-3 text-xs">
            <span className="truncate text-slate-300">{item.name}</span>
            <span className="shrink-0 font-medium text-slate-400">
              {formatValue(Number(item.value) || 0)}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
            <div
              className="h-full rounded-full bg-gradient-to-r from-brand-500 to-sky-400"
              style={{ width: `${Math.max((Number(item.value) / max) * 100, 2)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function MiniBars({
  data,
  className,
}: {
  data: Array<{ date: string; orders?: number }>;
  className?: string;
}) {
  const max = Math.max(...data.map((item) => Number(item.orders) || 0), 1);
  return (
    <div className={cn("flex h-16 items-end gap-1", className)}>
      {data.map((item, index) => (
        <div
          key={`${item.date}-${index}`}
          className="flex-1 rounded-t bg-brand-500/40 transition hover:bg-brand-400"
          style={{ height: `${Math.max(((Number(item.orders) || 0) / max) * 100, 4)}%` }}
          title={`${shortDate(item.date)}: ${Number(item.orders) || 0} orders`}
        />
      ))}
    </div>
  );
}
