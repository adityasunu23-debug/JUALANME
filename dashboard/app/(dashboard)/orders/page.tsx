"use client";

import { RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Loading,
  Modal,
  PageHeader,
  Pagination,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, humanize, money, queryString } from "@/lib/utils";

export type Invoice = {
  id: number;
  provider: string;
  provider_invoice_id?: string | null;
  amount: number;
  paid_amount?: number | null;
  currency: string;
  network: string;
  pay_address?: string | null;
  pay_amount?: number | null;
  qr_code_url?: string | null;
  payment_url?: string | null;
  status: string;
  provider_status?: string | null;
  tx_hash?: string | null;
  expires_at?: string | null;
  paid_at?: string | null;
};

export type Delivery = {
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
};

export type Order = {
  id: number;
  order_code: string;
  customer_id: number;
  customer_name?: string | null;
  customer_username?: string | null;
  customer_telegram_id?: number | null;
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
  discount_amount: number;
  total_amount: number;
  currency: string;
  status: string;
  delivery_type: string;
  delivery_status: string;
  voucher_code?: string | null;
  customer_note?: string | null;
  admin_note?: string | null;
  expires_at?: string | null;
  paid_at?: string | null;
  delivered_at?: string | null;
  created_at?: string | null;
  invoice?: Invoice | null;
  delivery?: Delivery | null;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

const STATUSES = [
  "PENDING_PAYMENT",
  "PAID",
  "DELIVERED",
  "COMPLETED",
  "EXPIRED",
  "CANCELLED",
  "FAILED",
  "REFUNDED",
];

export default function OrdersPage() {
  const toast = useToast();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Order | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [statusTarget, setStatusTarget] = useState("");
  const [deliveryContent, setDeliveryContent] = useState("");
  const [deliveryNote, setDeliveryNote] = useState("");
  const [markCompleted, setMarkCompleted] = useState(true);

  const path = useMemo(
    () => `/orders${queryString({ status, search, page, page_size: 20 })}`,
    [status, search, page]
  );
  const { data, loading, error, reload } = useApi<Page<Order>>(path);
  const orders = data?.items ?? [];

  useEffect(() => {
    const focus = new URLSearchParams(window.location.search).get("focus");
    if (!focus) return;
    api<Order>(`/orders/${focus}`)
      .then((order) => {
        setSelected(order);
        setNote(order.admin_note || "");
        setStatusTarget(order.status);
        setDeliveryContent(order.delivery?.delivered_content || "");
      })
      .catch(() => undefined);
  }, []);

  function openOrder(order: Order) {
    setSelected(order);
    setNote(order.admin_note || "");
    setStatusTarget(order.status);
    setDeliveryContent(order.delivery?.delivered_content || "");
    setDeliveryNote("");
    setMarkCompleted(true);
  }

  async function refreshSelected() {
    if (!selected) return;
    try {
      const updated = await api<Order>(`/orders/${selected.id}`);
      setSelected(updated);
      setNote(updated.admin_note || "");
      setStatusTarget(updated.status);
    } catch {
      // ignored
    }
  }

  async function runAction(label: string, action: () => Promise<unknown>, success: string) {
    if (!selected) return;
    setBusy(label);
    try {
      await action();
      toast.success(success);
      await refreshSelected();
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  async function markPaid() {
    if (!selected) return;
    if (!window.confirm("Settle this order manually and trigger delivery?")) return;
    await runAction(
      "paid",
      () => api(`/orders/${selected.id}/mark-paid`, { method: "POST" }),
      "Order marked as paid"
    );
  }

  async function cancelOrder() {
    if (!selected) return;
    if (!window.confirm("Cancel this unpaid order?")) return;
    await runAction(
      "cancel",
      () => api(`/orders/${selected.id}/cancel`, { method: "POST" }),
      "Order cancelled"
    );
  }

  async function refreshInvoice() {
    if (!selected) return;
    await runAction(
      "invoice",
      () => api(`/orders/${selected.id}/invoice/refresh`, { method: "POST" }),
      "Invoice refreshed"
    );
  }

  async function saveNote() {
    if (!selected) return;
    await runAction(
      "note",
      () => api(`/orders/${selected.id}/note`, { method: "PATCH", body: { admin_note: note || null } }),
      "Note saved"
    );
  }

  async function changeStatus() {
    if (!selected) return;
    await runAction(
      "status",
      () =>
        api(`/orders/${selected.id}/status`, {
          method: "PATCH",
          body: { status: statusTarget, note: note || undefined },
        }),
      "Status updated"
    );
  }

  async function deliver() {
    if (!selected) return;
    if (!deliveryContent.trim()) {
      toast.error("Delivery content is required");
      return;
    }
    await runAction(
      "deliver",
      () =>
        api(`/orders/${selected.id}/deliver`, {
          method: "POST",
          body: {
            content: deliveryContent,
            note: deliveryNote || undefined,
            mark_completed: markCompleted,
          },
        }),
      "Delivery sent to customer"
    );
  }

  return (
    <>
      <PageHeader
        title="Orders"
        description="Inspect payments, resolve stuck orders and deliver manually."
        actions={
          <Button onClick={() => reload()}>
            <RefreshCw className="h-4 w-4" /> Refresh
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="w-52">
          <option value="">All statuses</option>
          {STATUSES.map((value) => (
            <option key={value} value={value}>{humanize(value)}</option>
          ))}
        </Select>
        <div className="relative min-w-[240px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <Input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search order code, customer, product…"
            className="pl-9"
          />
        </div>
      </div>

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading orders…" />
        ) : error ? (
          <p className="p-5 text-sm text-rose-300">{error}</p>
        ) : orders.length === 0 ? (
          <div className="p-5"><EmptyState title="No orders found" description="Adjust the filters or wait for customers." /></div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th>Qty</th>
                  <th>Total</th>
                  <th>Status</th>
                  <th>Delivery</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => (
                  <tr key={order.id} className="cursor-pointer" onClick={() => openOrder(order)}>
                    <td>
                      <p className="font-mono text-xs text-brand-300">{order.order_code}</p>
                      {order.voucher_code && <p className="text-[11px] text-slate-500">Voucher {order.voucher_code}</p>}
                    </td>
                    <td>
                      <p className="text-sm">{order.customer_name || "—"}</p>
                      <p className="text-[11px] text-slate-500">
                        {order.customer_username ? `@${order.customer_username}` : order.customer_telegram_id}
                      </p>
                    </td>
                    <td className="max-w-[220px] truncate">{order.product_name}</td>
                    <td>{order.quantity}</td>
                    <td>{money(order.total_amount, order.currency)}</td>
                    <td><StatusBadge status={order.status} /></td>
                    <td><Badge tone={order.delivery_type === "AUTO" ? "blue" : "violet"}>{humanize(order.delivery_type)}</Badge></td>
                    <td className="text-xs text-slate-500">{formatDate(order.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && (
          <div className="px-4 pb-4">
            <Pagination page={data.meta.page} totalPages={data.meta.total_pages} total={data.meta.total} onChange={setPage} />
          </div>
        )}
      </Card>

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? `Order ${selected.order_code}` : "Order"}
        description={selected ? `${selected.product_name} · ${selected.quantity} × ${money(selected.unit_price, selected.currency)}` : undefined}
        size="xl"
      >
        {selected && (
          <div className="grid gap-5 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Customer</p>
                  <p className="mt-1 text-sm text-slate-100">{selected.customer_name || "—"}</p>
                  <p className="text-xs text-slate-500">
                    {selected.customer_username ? `@${selected.customer_username}` : selected.customer_telegram_id}
                  </p>
                </div>
                <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Totals</p>
                  <p className="mt-1 text-sm text-slate-100">{money(selected.total_amount, selected.currency)}</p>
                  <p className="text-xs text-slate-500">
                    Subtotal {money(selected.subtotal, selected.currency)}
                    {selected.discount_amount > 0 ? ` · discount ${money(selected.discount_amount, selected.currency)}` : ""}
                  </p>
                </div>
                <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Status</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    <StatusBadge status={selected.status} />
                    <Badge tone="gray">Delivery: {humanize(selected.delivery_status)}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">Created {formatDate(selected.created_at)}</p>
                </div>
                <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                  <p className="text-[11px] uppercase tracking-wide text-slate-500">Payment</p>
                  <p className="mt-1 text-sm text-slate-100">
                    {selected.invoice ? `${humanize(selected.invoice.provider)} · ${humanize(selected.invoice.status)}` : "No invoice"}
                  </p>
                  <p className="text-xs text-slate-500">
                    {selected.paid_at ? `Paid ${formatDate(selected.paid_at)}` : selected.expires_at ? `Expires ${formatDate(selected.expires_at)}` : "—"}
                  </p>
                </div>
              </div>

              {selected.invoice && (
                <div className="rounded-xl border border-white/5 p-3 text-xs">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-slate-400">Invoice #{selected.invoice.id}</span>
                    <Button size="sm" loading={busy === "invoice"} onClick={() => void refreshInvoice()}>
                      Check gateway
                    </Button>
                  </div>
                  <p className="break-all font-mono text-slate-500">{selected.invoice.pay_address || "No pay address"}</p>
                  {selected.invoice.tx_hash && <p className="mt-1 break-all font-mono text-emerald-300">tx: {selected.invoice.tx_hash}</p>}
                  {selected.invoice.payment_url && (
                    <a href={selected.invoice.payment_url} target="_blank" rel="noreferrer" className="link mt-1 inline-block">
                      Open hosted invoice
                    </a>
                  )}
                </div>
              )}

              <Field label="Admin note">
                <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Internal note for this order…" />
              </Field>
              <div className="flex flex-wrap gap-2">
                <Button loading={busy === "note"} onClick={() => void saveNote()}>Save note</Button>
                {selected.status === "PENDING_PAYMENT" && (
                  <Button variant="danger" loading={busy === "cancel"} onClick={() => void cancelOrder()}>
                    Cancel order
                  </Button>
                )}
                {!["PAID", "DELIVERED", "COMPLETED", "REFUNDED"].includes(selected.status) && (
                  <Button variant="success" loading={busy === "paid"} onClick={() => void markPaid()}>
                    Mark paid &amp; deliver
                  </Button>
                )}
              </div>

              {["PAID", "DELIVERED", "COMPLETED"].includes(selected.status) && (
                <div className="rounded-xl border border-brand-500/20 bg-brand-500/5 p-3">
                  <p className="text-xs font-medium text-brand-200">Manual delivery</p>
                  <p className="mb-2 text-[11px] text-brand-200/60">
                    Sends the content to the customer on Telegram and completes the order.
                  </p>
                  <Field label="Deliverable content">
                    <Textarea
                      value={deliveryContent}
                      onChange={(e) => setDeliveryContent(e.target.value)}
                      className="min-h-[120px] font-mono"
                      placeholder="Account credentials, license key, instructions…"
                    />
                  </Field>
                  <Field label="Delivery note" className="mt-2">
                    <Input value={deliveryNote} onChange={(e) => setDeliveryNote(e.target.value)} />
                  </Field>
                  <label className="mt-2 flex items-center gap-2 text-xs text-slate-300">
                    <input type="checkbox" checked={markCompleted} onChange={(e) => setMarkCompleted(e.target.checked)} />
                    Mark order as completed
                  </label>
                  <Button variant="primary" className="mt-3" loading={busy === "deliver"} onClick={() => void deliver()}>
                    Send delivery
                  </Button>
                  {selected.delivery?.delivered_content && (
                    <p className="mt-2 text-[11px] text-slate-500">
                      Last delivered {formatDate(selected.delivery.delivered_at)} · attempts {selected.delivery.attempts}
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-4">
              <div className="rounded-xl border border-white/5 p-3">
                <p className="mb-2 text-xs font-medium text-slate-300">Change status</p>
                <Select value={statusTarget} onChange={(e) => setStatusTarget(e.target.value)}>
                  {STATUSES.map((value) => (
                    <option key={value} value={value}>{humanize(value)}</option>
                  ))}
                </Select>
                <Button className="mt-2 w-full" loading={busy === "status"} onClick={() => void changeStatus()}>
                  Apply status
                </Button>
              </div>

              {selected.delivery && (
                <div className="rounded-xl border border-white/5 p-3 text-xs">
                  <p className="mb-1 font-medium text-slate-300">Delivery record</p>
                  <p className="text-slate-500">Mode: {humanize(selected.delivery.mode)} · Attempts: {selected.delivery.attempts}</p>
                  <p className="text-slate-500">Status: {humanize(selected.delivery.status)}</p>
                  {selected.delivery.last_error && (
                    <p className="mt-1 rounded-lg bg-rose-500/10 p-2 text-rose-300">{selected.delivery.last_error}</p>
                  )}
                  {selected.delivery.delivered_content && (
                    <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg bg-ink-950 p-2 font-mono text-[11px] text-slate-400">
                      {selected.delivery.delivered_content}
                    </pre>
                  )}
                </div>
              )}

              {selected.customer_note && (
                <div className="rounded-xl border border-white/5 p-3 text-xs">
                  <p className="mb-1 font-medium text-slate-300">Customer note</p>
                  <p className="whitespace-pre-wrap text-slate-400">{selected.customer_note}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
