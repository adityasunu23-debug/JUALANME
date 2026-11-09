"use client";

import { Megaphone, Play, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

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
import { formatDate, number } from "@/lib/utils";

type Broadcast = {
  id: number;
  title: string;
  message: string;
  audience: string;
  status: string;
  total_recipients: number;
  sent_count: number;
  failed_count: number;
  started_at?: string | null;
  finished_at?: string | null;
  created_at?: string | null;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

const empty = { title: "", message: "", audience: "ALL", send_now: false };

export default function BroadcastsPage() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<typeof empty | null>(null);
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);

  const { data, loading, error, reload } = useApi<Page<Broadcast>>(`/broadcasts?page=${page}&page_size=20`);
  const broadcasts = data?.items ?? [];

  async function create() {
    if (!form) return;
    setSaving(true);
    try {
      await api("/broadcasts", { method: "POST", body: form });
      toast.success(form.send_now ? "Broadcast queued for delivery" : "Broadcast saved as draft");
      setForm(null);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create broadcast");
    } finally {
      setSaving(false);
    }
  }

  async function run(broadcast: Broadcast) {
    if (!window.confirm(`Send “${broadcast.title}” now?`)) return;
    setBusy(broadcast.id);
    try {
      await api(`/broadcasts/${broadcast.id}/run`, { method: "POST" });
      toast.success("Broadcast sent");
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Send failed");
    } finally {
      setBusy(null);
    }
  }

  async function remove(broadcast: Broadcast) {
    if (!window.confirm(`Delete “${broadcast.title}”?`)) return;
    try {
      await api(`/broadcasts/${broadcast.id}`, { method: "DELETE" });
      toast.success("Broadcast deleted");
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Broadcasts"
        description="Reach all customers or a targeted segment in Telegram."
        actions={
          <Button variant="primary" onClick={() => setForm({ ...empty })}>
            <Plus className="h-4 w-4" /> New broadcast
          </Button>
        }
      />

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading broadcasts…" />
        ) : error ? (
          <p className="p-5 text-sm text-rose-300">{error}</p>
        ) : broadcasts.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="No broadcasts yet"
              description="Announce new products or promotions to your customers."
              action={<Button onClick={() => setForm({ ...empty })}>Create broadcast</Button>}
            />
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th>Audience</th>
                  <th>Status</th>
                  <th>Delivered</th>
                  <th>Failed</th>
                  <th>Finished</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {broadcasts.map((broadcast) => (
                  <tr key={broadcast.id}>
                    <td>
                      <p className="text-sm font-medium text-slate-100">{broadcast.title}</p>
                      <p className="max-w-[320px] truncate text-[11px] text-slate-500">{broadcast.message}</p>
                    </td>
                    <td><Badge tone="blue">{broadcast.audience}</Badge></td>
                    <td><StatusBadge status={broadcast.status} /></td>
                    <td>{number(broadcast.sent_count)} / {number(broadcast.total_recipients)}</td>
                    <td className={broadcast.failed_count > 0 ? "text-rose-300" : ""}>{number(broadcast.failed_count)}</td>
                    <td className="text-xs text-slate-500">{formatDate(broadcast.finished_at)}</td>
                    <td>
                      <div className="flex justify-end gap-1">
                        {!["SENT", "SENDING"].includes(broadcast.status) && (
                          <Button size="sm" loading={busy === broadcast.id} onClick={() => void run(broadcast)}>
                            <Play className="h-3.5 w-3.5" /> Send
                          </Button>
                        )}
                        <button
                          type="button"
                          onClick={() => void remove(broadcast)}
                          className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-rose-300"
                          title="Delete"
                        >
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

      <div className="mt-4 rounded-2xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-200">
        <Megaphone className="mr-2 inline h-4 w-4" />
        Broadcasts are sent sequentially with a short delay to stay within Telegram rate
        limits. Blocked customers are skipped automatically.
      </div>

      <Modal
        open={Boolean(form)}
        onClose={() => setForm(null)}
        title="New broadcast"
        description="Telegram HTML is supported. Keep messages concise."
        footer={
          <>
            <Button onClick={() => setForm(null)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void create()}>
              {form?.send_now ? "Create & send" : "Save draft"}
            </Button>
          </>
        }
      >
        {form && (
          <div className="space-y-4">
            <Field label="Title">
              <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            </Field>
            <Field label="Message">
              <Textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="min-h-[160px]" />
            </Field>
            <Field label="Audience">
              <Select value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })}>
                <option value="ALL">All customers</option>
                <option value="BUYERS">Buyers with at least one order</option>
                <option value="ACTIVE">Active in the last 30 days</option>
              </Select>
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={form.send_now} onChange={(e) => setForm({ ...form, send_now: e.target.checked })} />
              Send immediately after creating
            </label>
          </div>
        )}
      </Modal>
    </>
  );
}
