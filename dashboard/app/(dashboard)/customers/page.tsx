"use client";

import { Ban, CheckCircle2 } from "lucide-react";
import { useMemo, useState } from "react";

import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Loading,
  Modal,
  PageHeader,
  Pagination,
  SearchField,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, money, number, queryString } from "@/lib/utils";

type Customer = {
  id: number;
  telegram_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  language: string;
  is_blocked: boolean;
  total_orders: number;
  total_spent: number;
  notes?: string | null;
  last_seen_at?: string | null;
  created_at?: string | null;
};

type CustomerDetail = Customer & {
  recent_orders: Array<{
    id: number;
    order_code: string;
    product_name: string;
    total_amount: number;
    status: string;
    created_at?: string | null;
  }>;
  open_tickets: number;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

export default function CustomersPage() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [blocked, setBlocked] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<CustomerDetail | null>(null);
  const [notes, setNotes] = useState("");
  const [language, setLanguage] = useState("id");
  const [isBlocked, setIsBlocked] = useState(false);
  const [saving, setSaving] = useState(false);

  const path = useMemo(
    () => `/customers${queryString({ search, blocked, page, page_size: 20 })}`,
    [search, blocked, page]
  );
  const { data, loading, error, reload } = useApi<Page<Customer>>(path);
  const customers = data?.items ?? [];

  async function open(customer: Customer) {
    try {
      const result = await api<CustomerDetail>(`/customers/${customer.id}`);
      setDetail(result);
      setNotes(result.notes || "");
      setLanguage(result.language || "id");
      setIsBlocked(result.is_blocked);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load customer");
    }
  }

  async function save() {
    if (!detail) return;
    setSaving(true);
    try {
      await api(`/customers/${detail.id}`, {
        method: "PATCH",
        body: { notes: notes || null, language, is_blocked: isBlocked },
      });
      toast.success("Customer updated");
      setDetail(null);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader title="Customers" description="Buyers registered through the Telegram bot." />

      <div className="mb-4 flex flex-wrap gap-2">
        <SearchField value={search} onChange={(value) => { setSearch(value); setPage(1); }} placeholder="Search name, username, Telegram ID…" className="w-80" />
        <Select value={blocked} onChange={(e) => { setBlocked(e.target.value); setPage(1); }} className="w-40">
          <option value="">All customers</option>
          <option value="false">Active only</option>
          <option value="true">Blocked only</option>
        </Select>
      </div>

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading customers…" />
        ) : error ? (
          <p className="p-5 text-sm text-rose-300">{error}</p>
        ) : customers.length === 0 ? (
          <div className="p-5"><EmptyState title="No customers found" /></div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Telegram</th>
                  <th>Language</th>
                  <th>Orders</th>
                  <th>Spent</th>
                  <th>Status</th>
                  <th>Last seen</th>
                </tr>
              </thead>
              <tbody>
                {customers.map((customer) => (
                  <tr key={customer.id} className="cursor-pointer" onClick={() => void open(customer)}>
                    <td>
                      <p className="text-sm text-slate-100">
                        {[customer.first_name, customer.last_name].filter(Boolean).join(" ") || `Customer #${customer.id}`}
                      </p>
                      <p className="text-[11px] text-slate-500">Joined {formatDate(customer.created_at, false)}</p>
                    </td>
                    <td>
                      <p className="text-xs">@{customer.username || "—"}</p>
                      <p className="font-mono text-[11px] text-slate-500">{customer.telegram_id}</p>
                    </td>
                    <td className="text-xs uppercase">{customer.language}</td>
                    <td>{number(customer.total_orders)}</td>
                    <td>{money(customer.total_spent)}</td>
                    <td><Badge tone={customer.is_blocked ? "red" : "green"}>{customer.is_blocked ? "Blocked" : "Active"}</Badge></td>
                    <td className="text-xs text-slate-500">{formatDate(customer.last_seen_at)}</td>
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
        open={Boolean(detail)}
        onClose={() => setDetail(null)}
        title={detail ? [detail.first_name, detail.last_name].filter(Boolean).join(" ") || `Customer #${detail.id}` : "Customer"}
        description={detail ? `@${detail.username || "—"} · ${detail.telegram_id}` : undefined}
        size="lg"
        footer={
          <>
            <Button onClick={() => setDetail(null)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void save()}>Save</Button>
          </>
        }
      >
        {detail && (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                <p className="text-[11px] uppercase text-slate-500">Orders</p>
                <p className="text-lg font-semibold text-white">{number(detail.total_orders)}</p>
              </div>
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                <p className="text-[11px] uppercase text-slate-500">Total spent</p>
                <p className="text-lg font-semibold text-white">{money(detail.total_spent)}</p>
              </div>
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
                <p className="text-[11px] uppercase text-slate-500">Open tickets</p>
                <p className="text-lg font-semibold text-white">{number(detail.open_tickets)}</p>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Language">
                <Select value={language} onChange={(e) => setLanguage(e.target.value)}>
                  <option value="id">Indonesian</option>
                  <option value="en">English</option>
                </Select>
              </Field>
              <div className="sm:col-span-2">
                <span className="label">Account status</span>
                <button
                  type="button"
                  onClick={() => setIsBlocked((value) => !value)}
                  className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-sm transition ${
                    isBlocked
                      ? "border-rose-500/30 bg-rose-500/10 text-rose-200"
                      : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {isBlocked ? <Ban className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                    {isBlocked ? "Blocked from ordering" : "Active"}
                  </span>
                  <span className="text-xs opacity-70">Click to toggle</span>
                </button>
              </div>
            </div>

            <Field label="Internal notes">
              <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
            </Field>

            <div>
              <p className="mb-2 text-xs font-medium text-slate-300">Recent orders</p>
              {detail.recent_orders.length === 0 ? (
                <p className="text-xs text-slate-500">No orders yet.</p>
              ) : (
                <div className="table-wrap rounded-xl border border-white/5">
                  <table className="tbl min-w-0">
                    <thead>
                      <tr><th>Order</th><th>Product</th><th>Total</th><th>Status</th><th>Date</th></tr>
                    </thead>
                    <tbody>
                      {detail.recent_orders.map((order) => (
                        <tr key={order.id}>
                          <td className="font-mono text-xs">{order.order_code}</td>
                          <td className="max-w-[180px] truncate">{order.product_name}</td>
                          <td>{money(order.total_amount)}</td>
                          <td><StatusBadge status={order.status} /></td>
                          <td className="text-xs text-slate-500">{formatDate(order.created_at, false)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
