"use client";

import { Send } from "lucide-react";
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
  SearchField,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, humanize, queryString } from "@/lib/utils";

type Ticket = {
  id: number;
  ticket_code: string;
  customer_id: number;
  customer_name?: string | null;
  customer_telegram_id?: number | null;
  order_id?: number | null;
  subject: string;
  category: string;
  status: string;
  priority: string;
  last_message_at?: string | null;
  created_at?: string | null;
  message_count: number;
};

type TicketMessage = {
  id: number;
  sender_type: string;
  sender_name?: string | null;
  message: string;
  is_read: boolean;
  created_at?: string | null;
};

type TicketDetail = Ticket & { messages: TicketMessage[] };

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

export default function TicketsPage() {
  const toast = useToast();
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [updating, setUpdating] = useState(false);

  const path = useMemo(
    () => `/tickets${queryString({ status, search, page, page_size: 20 })}`,
    [status, search, page]
  );
  const listApi = useApi<Page<Ticket>>(path);
  const detailApi = useApi<TicketDetail>(selectedId ? `/tickets/${selectedId}` : null, [selectedId]);
  const detail = detailApi.data;
  const tickets = listApi.data?.items ?? [];

  async function sendReply() {
    if (!selectedId || !reply.trim()) return;
    setSending(true);
    try {
      await api(`/tickets/${selectedId}/reply`, { method: "POST", body: { message: reply } });
      toast.success("Reply sent to customer");
      setReply("");
      detailApi.reload();
      listApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to send reply");
    } finally {
      setSending(false);
    }
  }

  async function updateTicket(nextStatus: string, priority?: string) {
    if (!selectedId) return;
    setUpdating(true);
    try {
      await api(`/tickets/${selectedId}/status`, {
        method: "PATCH",
        body: { status: nextStatus, priority: priority || detail?.priority || "NORMAL" },
      });
      toast.success("Ticket updated");
      detailApi.reload();
      listApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Update failed");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <>
      <PageHeader title="Support" description="Answer customer tickets created from the bot or dashboard." />

      <div className="mb-4 flex flex-wrap gap-2">
        <SearchField value={search} onChange={(value) => { setSearch(value); setPage(1); }} placeholder="Search subject or ticket code…" className="w-72" />
        <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="w-40">
          <option value="">All statuses</option>
          {["OPEN", "PENDING", "ANSWERED", "CLOSED"].map((value) => (
            <option key={value} value={value}>{humanize(value)}</option>
          ))}
        </Select>
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-2" bodyClassName="p-0">
          {listApi.loading ? (
            <Loading label="Loading tickets…" />
          ) : tickets.length === 0 ? (
            <div className="p-5"><EmptyState title="No tickets" description="Support requests from customers appear here." /></div>
          ) : (
            <div className="divide-y divide-white/5">
              {tickets.map((ticket) => (
                <button
                  key={ticket.id}
                  type="button"
                  onClick={() => { setSelectedId(ticket.id); setReply(""); }}
                  className={`block w-full px-4 py-3 text-left transition hover:bg-white/5 ${
                    selectedId === ticket.id ? "bg-brand-500/5" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[11px] text-brand-300">{ticket.ticket_code}</span>
                    <StatusBadge status={ticket.status} />
                  </div>
                  <p className="mt-1 truncate text-sm text-slate-200">{ticket.subject}</p>
                  <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                    <span>{ticket.customer_name || `Customer #${ticket.customer_id}`}</span>
                    <span>{ticket.message_count} msgs</span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-600">{formatDate(ticket.last_message_at)}</p>
                </button>
              ))}
            </div>
          )}
          {listApi.data && (
            <div className="px-4 pb-4">
              <Pagination page={listApi.data.meta.page} totalPages={listApi.data.meta.total_pages} total={listApi.data.meta.total} onChange={setPage} />
            </div>
          )}
        </Card>

        <Card className="lg:col-span-3" bodyClassName="p-0">
          {!selectedId ? (
            <div className="p-5"><EmptyState title="Select a ticket" description="Choose a conversation to view the thread." /></div>
          ) : detailApi.loading ? (
            <Loading label="Loading conversation…" />
          ) : detail ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/5 px-5 py-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-mono text-xs text-brand-300">{detail.ticket_code}</p>
                    <StatusBadge status={detail.status} />
                    <Badge tone={detail.priority === "URGENT" ? "red" : detail.priority === "HIGH" ? "amber" : "gray"}>
                      {humanize(detail.priority)}
                    </Badge>
                  </div>
                  <h3 className="mt-1 text-base font-medium text-white">{detail.subject}</h3>
                  <p className="text-xs text-slate-500">
                    {detail.customer_name || `Customer #${detail.customer_id}`}
                    {detail.order_id ? ` · Order #${detail.order_id}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Select
                    value={detail.status}
                    onChange={(e) => void updateTicket(e.target.value)}
                    className="w-36"
                    disabled={updating}
                  >
                    {["OPEN", "PENDING", "ANSWERED", "CLOSED"].map((value) => (
                      <option key={value} value={value}>{humanize(value)}</option>
                    ))}
                  </Select>
                  <Select
                    value={detail.priority}
                    onChange={(e) => void updateTicket(detail.status, e.target.value)}
                    className="w-32"
                    disabled={updating}
                  >
                    {["LOW", "NORMAL", "HIGH", "URGENT"].map((value) => (
                      <option key={value} value={value}>{humanize(value)}</option>
                    ))}
                  </Select>
                </div>
              </div>

              <div className="max-h-[420px] space-y-3 overflow-y-auto px-5 py-4">
                {detail.messages.map((message) => {
                  const admin = message.sender_type === "ADMIN";
                  return (
                    <div key={message.id} className={`flex ${admin ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                          admin
                            ? "bg-brand-500/15 text-brand-50"
                            : "border border-white/5 bg-white/[0.03] text-slate-200"
                        }`}
                      >
                        <p className="mb-1 text-[10px] uppercase tracking-wide opacity-60">
                          {admin ? "Support" : message.sender_name || "Customer"} · {formatDate(message.created_at)}
                        </p>
                        <p className="whitespace-pre-wrap">{message.message}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {detail.status !== "CLOSED" ? (
                <div className="border-t border-white/5 px-5 py-4">
                  <Textarea
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder="Write a reply to the customer…"
                    className="min-h-[100px]"
                  />
                  <div className="mt-2 flex justify-end">
                    <Button variant="primary" loading={sending} onClick={() => void sendReply()}>
                      <Send className="h-4 w-4" /> Send reply
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="border-t border-white/5 px-5 py-4 text-xs text-slate-500">
                  This ticket is closed. Reopen it to reply again.
                </div>
              )}
            </>
          ) : (
            <div className="p-5"><p className="text-sm text-rose-300">{detailApi.error || "Ticket not found"}</p></div>
          )}
        </Card>
      </div>
    </>
  );
}
