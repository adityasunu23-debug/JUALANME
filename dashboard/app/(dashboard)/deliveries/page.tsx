"use client";

import { RefreshCw, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";

import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Loading,
  PageHeader,
  Pagination,
  Select,
  StatusBadge,
  Tabs,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, humanize, queryString } from "@/lib/utils";

type Delivery = {
  id: number;
  order_id: number;
  product_id: number;
  mode: string;
  status: string;
  quantity: number;
  delivered_content?: string | null;
  attempts: number;
  last_error?: string | null;
  delivered_by_admin_id?: number | null;
  delivered_at?: string | null;
  order_code?: string | null;
  customer_name?: string | null;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

export default function DeliveriesPage() {
  const toast = useToast();
  const [tab, setTab] = useState<"queue" | "failed" | "all">("queue");
  const [status, setStatus] = useState("");
  const [mode, setMode] = useState("");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState<number | null>(null);

  const queueApi = useApi<Delivery[]>(tab === "queue" ? "/deliveries/queue" : null);
  const failedApi = useApi<Delivery[]>(tab === "failed" ? "/deliveries/failed" : null);
  const allPath = useMemo(
    () => `/deliveries${queryString({ status, mode, page, page_size: 20 })}`,
    [status, mode, page]
  );
  const allApi = useApi<Page<Delivery>>(tab === "all" ? allPath : null);

  const rows =
    tab === "queue" ? queueApi.data ?? [] : tab === "failed" ? failedApi.data ?? [] : allApi.data?.items ?? [];
  const loading = tab === "queue" ? queueApi.loading : tab === "failed" ? failedApi.loading : allApi.loading;

  function reload() {
    if (tab === "queue") queueApi.reload();
    else if (tab === "failed") failedApi.reload();
    else allApi.reload();
  }

  async function retry(delivery: Delivery) {
    if (!window.confirm(`Retry delivery for order #${delivery.order_id}?`)) return;
    setBusy(delivery.id);
    try {
      await api(`/deliveries/${delivery.id}/retry`, { method: "POST" });
      toast.success("Delivery retried");
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Deliveries"
        description="Monitor automatic fulfilment and resolve manual or failed deliveries."
        actions={<Button onClick={reload}><RefreshCw className="h-4 w-4" /> Refresh</Button>}
      />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Tabs
          tabs={[
            { value: "queue", label: "Manual queue", count: queueApi.data?.length },
            { value: "failed", label: "Failed", count: failedApi.data?.length },
            { value: "all", label: "All deliveries", count: allApi.data?.meta.total },
          ]}
          value={tab}
          onChange={(value) => { setTab(value); setPage(1); }}
        />
        {tab === "all" && (
          <div className="flex gap-2">
            <Select value={mode} onChange={(e) => { setMode(e.target.value); setPage(1); }} className="w-36">
              <option value="">All modes</option>
              <option value="AUTO">Auto</option>
              <option value="MANUAL">Manual</option>
            </Select>
            <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="w-44">
              <option value="">All statuses</option>
              {["PENDING", "PROCESSING", "DELIVERED", "FAILED", "NOT_REQUIRED"].map((value) => (
                <option key={value} value={value}>{humanize(value)}</option>
              ))}
            </Select>
          </div>
        )}
      </div>

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading deliveries…" />
        ) : rows.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title={tab === "queue" ? "Queue is clear" : tab === "failed" ? "No failed deliveries" : "No deliveries"}
              description={
                tab === "queue"
                  ? "Paid manual orders will appear here for fulfilment."
                  : undefined
              }
            />
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Delivery</th>
                  <th>Order</th>
                  <th>Mode</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Delivered</th>
                  <th>Content / error</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((delivery) => (
                  <tr key={delivery.id}>
                    <td className="font-mono text-xs">#{delivery.id}</td>
                    <td>
                      <p className="text-sm text-slate-200">Order #{delivery.order_id}</p>
                      {delivery.customer_name && <p className="text-[11px] text-slate-500">{delivery.customer_name}</p>}
                    </td>
                    <td><Badge tone={delivery.mode === "AUTO" ? "blue" : "violet"}>{humanize(delivery.mode)}</Badge></td>
                    <td><StatusBadge status={delivery.status} /></td>
                    <td>{delivery.attempts}</td>
                    <td className="text-xs text-slate-500">{formatDate(delivery.delivered_at)}</td>
                    <td className="max-w-[260px]">
                      {delivery.last_error ? (
                        <span className="text-xs text-rose-300">{delivery.last_error}</span>
                      ) : (
                        <span className="line-clamp-2 font-mono text-[11px] text-slate-500">
                          {delivery.delivered_content || "—"}
                        </span>
                      )}
                    </td>
                    <td>
                      <div className="flex justify-end">
                        {delivery.status !== "DELIVERED" && (
                          <Button
                            size="sm"
                            variant="secondary"
                            loading={busy === delivery.id}
                            onClick={() => void retry(delivery)}
                          >
                            <RotateCcw className="h-3.5 w-3.5" /> Retry
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {tab === "all" && allApi.data && (
          <div className="px-4 pb-4">
            <Pagination
              page={allApi.data.meta.page}
              totalPages={allApi.data.meta.total_pages}
              total={allApi.data.meta.total}
              onChange={setPage}
            />
          </div>
        )}
      </Card>
    </>
  );
}
