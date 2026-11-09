"use client";

import { Pencil, Plus, Tag, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

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
  SearchField,
  Select,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, money, number, queryString, toDateInput } from "@/lib/utils";

type Voucher = {
  id: number;
  code: string;
  description?: string | null;
  type: "PERCENT" | "FIXED";
  value: number;
  min_purchase: number;
  max_discount?: number | null;
  usage_limit: number;
  per_customer_limit: number;
  valid_from?: string | null;
  valid_until?: string | null;
  is_active: boolean;
  used_count: number;
  created_at?: string | null;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

type Redemption = { id: number; customer_id: number; order_id?: number | null; discount_amount: number; created_at?: string | null };

const empty = {
  code: "",
  description: "",
  type: "PERCENT",
  value: "10",
  min_purchase: "0",
  max_discount: "",
  usage_limit: "0",
  per_customer_limit: "1",
  valid_from: "",
  valid_until: "",
  is_active: true,
};

export default function VouchersPage() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [active, setActive] = useState("");
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<typeof empty & { id?: number } | null>(null);
  const [saving, setSaving] = useState(false);
  const [redemptions, setRedemptions] = useState<{ voucher: Voucher; rows: Redemption[] } | null>(null);
  const [testCode, setTestCode] = useState("");
  const [testSubtotal, setTestSubtotal] = useState("10");
  const [testResult, setTestResult] = useState<{ valid: boolean; discount: number; total: number; message: string } | null>(null);

  const path = useMemo(
    () => `/vouchers${queryString({ search, active, page, page_size: 20 })}`,
    [search, active, page]
  );
  const { data, loading, error, reload } = useApi<Page<Voucher>>(path);
  const vouchers = data?.items ?? [];

  function openEdit(voucher: Voucher) {
    setForm({
      id: voucher.id,
      code: voucher.code,
      description: voucher.description || "",
      type: voucher.type,
      value: String(voucher.value),
      min_purchase: String(voucher.min_purchase),
      max_discount: voucher.max_discount ? String(voucher.max_discount) : "",
      usage_limit: String(voucher.usage_limit),
      per_customer_limit: String(voucher.per_customer_limit),
      valid_from: toDateInput(voucher.valid_from),
      valid_until: toDateInput(voucher.valid_until),
      is_active: voucher.is_active,
    });
  }

  async function save() {
    if (!form) return;
    setSaving(true);
    try {
      const payload = {
        description: form.description || null,
        type: form.type,
        value: Number(form.value),
        min_purchase: Number(form.min_purchase),
        max_discount: form.max_discount ? Number(form.max_discount) : null,
        usage_limit: Number(form.usage_limit),
        per_customer_limit: Number(form.per_customer_limit),
        valid_from: form.valid_from ? new Date(form.valid_from).toISOString() : null,
        valid_until: form.valid_until ? new Date(form.valid_until).toISOString() : null,
        is_active: form.is_active,
      };
      if (form.id) {
        await api(`/vouchers/${form.id}`, { method: "PATCH", body: payload });
        toast.success("Voucher updated");
      } else {
        await api("/vouchers", { method: "POST", body: { ...payload, code: form.code } });
        toast.success("Voucher created");
      }
      setForm(null);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save voucher");
    } finally {
      setSaving(false);
    }
  }

  async function remove(voucher: Voucher) {
    if (!window.confirm(`Delete voucher ${voucher.code}?`)) return;
    try {
      await api(`/vouchers/${voucher.id}`, { method: "DELETE" });
      toast.success("Voucher deleted");
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  async function showRedemptions(voucher: Voucher) {
    try {
      const rows = await api<Redemption[]>(`/vouchers/${voucher.id}/redemptions`);
      setRedemptions({ voucher, rows });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load redemptions");
    }
  }

  async function validate() {
    try {
      const result = await api<{ valid: boolean; discount: number; total: number; message: string }>("/vouchers/validate", {
        method: "POST",
        body: { code: testCode, subtotal: Number(testSubtotal) },
      });
      setTestResult(result);
    } catch (err) {
      setTestResult({ valid: false, discount: 0, total: Number(testSubtotal), message: err instanceof Error ? err.message : "Validation failed" });
    }
  }

  return (
    <>
      <PageHeader
        title="Vouchers"
        description="Discount codes customers can redeem during checkout."
        actions={
          <Button variant="primary" onClick={() => setForm({ ...empty })}>
            <Plus className="h-4 w-4" /> New voucher
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <SearchField value={search} onChange={(value) => { setSearch(value); setPage(1); }} placeholder="Search code…" className="w-64" />
        <Select value={active} onChange={(e) => { setActive(e.target.value); setPage(1); }} className="w-40">
          <option value="">All vouchers</option>
          <option value="true">Active only</option>
          <option value="false">Inactive only</option>
        </Select>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        <Card className="lg:col-span-3" bodyClassName="p-0">
          {loading ? (
            <Loading label="Loading vouchers…" />
          ) : error ? (
            <p className="p-5 text-sm text-rose-300">{error}</p>
          ) : vouchers.length === 0 ? (
            <div className="p-5"><EmptyState title="No vouchers" description="Create a code to reward repeat buyers." /></div>
          ) : (
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Discount</th>
                    <th>Rules</th>
                    <th>Used</th>
                    <th>Validity</th>
                    <th>Status</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {vouchers.map((voucher) => (
                    <tr key={voucher.id}>
                      <td>
                        <p className="font-mono text-sm text-brand-300">{voucher.code}</p>
                        {voucher.description && <p className="max-w-[200px] truncate text-[11px] text-slate-500">{voucher.description}</p>}
                      </td>
                      <td>
                        {voucher.type === "PERCENT" ? `${voucher.value}%` : money(voucher.value)}
                        {voucher.max_discount ? <p className="text-[11px] text-slate-500">max {money(voucher.max_discount)}</p> : null}
                      </td>
                      <td className="text-xs">
                        <p>Min {money(voucher.min_purchase)}</p>
                        <p className="text-slate-500">
                          {voucher.usage_limit ? `${voucher.usage_limit} total` : "Unlimited"} · {voucher.per_customer_limit}/customer
                        </p>
                      </td>
                      <td>{number(voucher.used_count)}</td>
                      <td className="text-xs text-slate-500">
                        {voucher.valid_from ? formatDate(voucher.valid_from) : "—"} →{" "}
                        {voucher.valid_until ? formatDate(voucher.valid_until) : "∞"}
                      </td>
                      <td><Badge tone={voucher.is_active ? "green" : "gray"}>{voucher.is_active ? "Active" : "Inactive"}</Badge></td>
                      <td>
                        <div className="flex justify-end gap-1">
                          <button type="button" onClick={() => void showRedemptions(voucher)} className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-brand-300" title="Redemptions">
                            <Tag className="h-4 w-4" />
                          </button>
                          <button type="button" onClick={() => openEdit(voucher)} className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-sky-300" title="Edit">
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button type="button" onClick={() => void remove(voucher)} className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-rose-300" title="Delete">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
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

        <Card title="Validate a code" subtitle="Preview the discount before sharing.">
          <div className="space-y-3">
            <Field label="Voucher code">
              <Input value={testCode} onChange={(e) => setTestCode(e.target.value.toUpperCase())} placeholder="WELCOME10" />
            </Field>
            <Field label="Order subtotal">
              <Input type="number" step="0.01" value={testSubtotal} onChange={(e) => setTestSubtotal(e.target.value)} />
            </Field>
            <Button variant="primary" className="w-full" onClick={() => void validate()}>Validate</Button>
            {testResult && (
              <div className={`rounded-xl border p-3 text-xs ${testResult.valid ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-200" : "border-rose-500/20 bg-rose-500/5 text-rose-200"}`}>
                <p className="font-medium">{testResult.message}</p>
                {testResult.valid && (
                  <p className="mt-1">
                    Discount {money(testResult.discount)} · Total {money(testResult.total)}
                  </p>
                )}
              </div>
            )}
          </div>
        </Card>
      </div>

      <Modal
        open={Boolean(form)}
        onClose={() => setForm(null)}
        title={form?.id ? "Edit voucher" : "New voucher"}
        size="lg"
        footer={
          <>
            <Button onClick={() => setForm(null)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void save()}>
              {form?.id ? "Save changes" : "Create voucher"}
            </Button>
          </>
        }
      >
        {form && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Code" hint="Uppercase, unique.">
              <Input value={form.code} disabled={Boolean(form.id)} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} />
            </Field>
            <Field label="Type">
              <Select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                <option value="PERCENT">Percentage</option>
                <option value="FIXED">Fixed amount</option>
              </Select>
            </Field>
            <Field label={form.type === "PERCENT" ? "Percent off" : "Amount off (USDT)"}>
              <Input type="number" step="0.01" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
            </Field>
            <Field label="Max discount">
              <Input type="number" step="0.01" value={form.max_discount} onChange={(e) => setForm({ ...form, max_discount: e.target.value })} placeholder="No cap" />
            </Field>
            <Field label="Minimum purchase">
              <Input type="number" step="0.01" value={form.min_purchase} onChange={(e) => setForm({ ...form, min_purchase: e.target.value })} />
            </Field>
            <Field label="Total usage limit" hint="0 = unlimited.">
              <Input type="number" value={form.usage_limit} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} />
            </Field>
            <Field label="Per-customer limit">
              <Input type="number" value={form.per_customer_limit} onChange={(e) => setForm({ ...form, per_customer_limit: e.target.value })} />
            </Field>
            <Field label="Valid from">
              <Input type="datetime-local" value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} />
            </Field>
            <Field label="Valid until">
              <Input type="datetime-local" value={form.valid_until} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
            </Field>
            <Field label="Description" className="sm:col-span-2">
              <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-300 sm:col-span-2">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
              Active
            </label>
          </div>
        )}
      </Modal>

      <Modal
        open={Boolean(redemptions)}
        onClose={() => setRedemptions(null)}
        title={redemptions ? `Redemptions · ${redemptions.voucher.code}` : "Redemptions"}
        size="lg"
      >
        {redemptions && (
          redemptions.rows.length === 0 ? (
            <EmptyState title="No redemptions yet" />
          ) : (
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr><th>Customer</th><th>Order</th><th>Discount</th><th>Date</th></tr>
                </thead>
                <tbody>
                  {redemptions.rows.map((row) => (
                    <tr key={row.id}>
                      <td>#{row.customer_id}</td>
                      <td>{row.order_id ? `#${row.order_id}` : "—"}</td>
                      <td>{money(row.discount_amount)}</td>
                      <td className="text-xs text-slate-500">{formatDate(row.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </Modal>
    </>
  );
}
