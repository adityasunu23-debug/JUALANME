"use client";

import { RefreshCw, ShieldCheck } from "lucide-react";
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
  Select,
  StatCard,
  StatusBadge,
  Tabs,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, humanize, money, queryString } from "@/lib/utils";

type Invoice = {
  id: number;
  order_id: number;
  order_code?: string | null;
  provider: string;
  provider_invoice_id?: string | null;
  provider_order_ref: string;
  amount: number;
  paid_amount?: number | null;
  currency: string;
  network: string;
  pay_address?: string | null;
  pay_amount?: number | null;
  payment_url?: string | null;
  status: string;
  provider_status?: string | null;
  tx_hash?: string | null;
  confirmations: number;
  is_manual: boolean;
  expires_at?: string | null;
  paid_at?: string | null;
  created_at?: string | null;
};

type WebhookEvent = {
  id: number;
  provider: string;
  event_type?: string | null;
  signature_valid: boolean;
  processed: boolean;
  order_code?: string | null;
  provider_invoice_id?: string | null;
  error?: string | null;
  source_ip?: string | null;
  created_at?: string | null;
};

type ProviderStatus = {
  provider: string;
  configured: boolean;
  merchant_uuid_set: boolean;
  api_key_set: boolean;
  network: string;
  currency: string;
  webhook_url?: string | null;
  supported_networks: string[];
  notes?: string | null;
};

type ProviderCheck = {
  provider: string;
  reachable: boolean;
  usdt_bep20_supported: boolean;
  detail: string;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

export default function PaymentsPage() {
  const toast = useToast();
  const [tab, setTab] = useState<"invoices" | "webhooks" | "provider">("invoices");
  const [status, setStatus] = useState("");
  const [provider, setProvider] = useState("");
  const [processed, setProcessed] = useState("");
  const [page, setPage] = useState(1);
  const [manualInvoice, setManualInvoice] = useState<Invoice | null>(null);
  const [txHash, setTxHash] = useState("");
  const [paidAmount, setPaidAmount] = useState("");
  const [manualNote, setManualNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [checkResult, setCheckResult] = useState<ProviderCheck | null>(null);

  const invoicesPath = useMemo(
    () => `/payments/invoices${queryString({ status, provider, page, page_size: 20 })}`,
    [status, provider, page]
  );
  const invoicesApi = useApi<Page<Invoice>>(invoicesPath);
  const webhooksPath = useMemo(
    () => `/payments/webhook-events${queryString({ processed, page, page_size: 20 })}`,
    [processed, page]
  );
  const webhooksApi = useApi<Page<WebhookEvent>>(tab === "webhooks" ? webhooksPath : null);
  const providerApi = useApi<ProviderStatus>(tab === "provider" ? "/payments/provider" : null);

  const invoices = invoicesApi.data?.items ?? [];

  async function checkInvoice(invoice: Invoice) {
    setBusy(`check-${invoice.id}`);
    try {
      await api(`/payments/invoices/${invoice.id}/check`, { method: "POST" });
      toast.success("Invoice refreshed from gateway");
      invoicesApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setBusy(null);
    }
  }

  async function submitManual() {
    if (!manualInvoice) return;
    setBusy("manual");
    try {
      await api(`/payments/invoices/${manualInvoice.id}/manual`, {
        method: "POST",
        body: {
          tx_hash: txHash || undefined,
          paid_amount: paidAmount ? Number(paidAmount) : undefined,
          note: manualNote || undefined,
        },
      });
      toast.success("Invoice settled manually");
      setManualInvoice(null);
      invoicesApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Manual settlement failed");
    } finally {
      setBusy(null);
    }
  }

  async function runProviderCheck() {
    setBusy("provider-check");
    try {
      const result = await api<ProviderCheck>("/payments/provider-check", { method: "POST" });
      setCheckResult(result);
      toast.push(result.detail, result.reachable ? "success" : "error");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Provider check failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Payments"
        description="Gateway invoices, webhook audit trail and provider health."
        actions={<Button onClick={() => (tab === "invoices" ? invoicesApi.reload() : tab === "webhooks" ? webhooksApi.reload() : providerApi.reload())}><RefreshCw className="h-4 w-4" /> Refresh</Button>}
      />

      <div className="mb-4">
        <Tabs
          tabs={[
            { value: "invoices", label: "Invoices", count: invoicesApi.data?.meta.total },
            { value: "webhooks", label: "Webhook events", count: webhooksApi.data?.meta.total },
            { value: "provider", label: "Provider" },
          ]}
          value={tab}
          onChange={(value) => { setTab(value); setPage(1); }}
        />
      </div>

      {tab === "invoices" && (
        <>
          <div className="mb-4 flex flex-wrap gap-2">
            <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="w-44">
              <option value="">All statuses</option>
              {["PENDING", "CONFIRMING", "PAID", "UNDERPAID", "OVERPAID", "EXPIRED", "FAILED", "CANCELLED"].map((value) => (
                <option key={value} value={value}>{humanize(value)}</option>
              ))}
            </Select>
            <Select value={provider} onChange={(e) => { setProvider(e.target.value); setPage(1); }} className="w-40">
              <option value="">All providers</option>
              <option value="cryptomus">Cryptomus</option>
              <option value="mock">Mock</option>
            </Select>
          </div>

          <Card bodyClassName="p-0">
            {invoicesApi.loading ? (
              <Loading label="Loading invoices…" />
            ) : invoices.length === 0 ? (
              <div className="p-5"><EmptyState title="No invoices found" /></div>
            ) : (
              <div className="table-wrap">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Invoice</th>
                      <th>Order</th>
                      <th>Provider</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th className="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((invoice) => (
                      <tr key={invoice.id}>
                        <td>
                          <p className="font-mono text-xs text-slate-300">#{invoice.id}</p>
                          <p className="text-[11px] text-slate-500">{invoice.provider_invoice_id || "—"}</p>
                        </td>
                        <td>
                          <p className="text-sm">{invoice.order_code || invoice.provider_order_ref}</p>
                          <p className="text-[11px] text-slate-500">Order #{invoice.order_id}</p>
                        </td>
                        <td className="text-xs uppercase">
                          {invoice.provider}
                          {invoice.is_manual && <Badge tone="violet" className="ml-1">Manual</Badge>}
                        </td>
                        <td>
                          <p>{money(invoice.amount, invoice.currency)}</p>
                          <p className="text-[11px] text-slate-500">{invoice.network.toUpperCase()}</p>
                        </td>
                        <td>
                          <StatusBadge status={invoice.status} />
                          {invoice.tx_hash && (
                            <p className="mt-1 max-w-[160px] truncate font-mono text-[10px] text-slate-500">{invoice.tx_hash}</p>
                          )}
                        </td>
                        <td className="text-xs text-slate-500">{formatDate(invoice.created_at)}</td>
                        <td>
                          <div className="flex justify-end gap-1">
                            <Button size="sm" loading={busy === `check-${invoice.id}`} onClick={() => void checkInvoice(invoice)}>
                              Check
                            </Button>
                            {!["PAID", "OVERPAID"].includes(invoice.status) && (
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => {
                                  setManualInvoice(invoice);
                                  setTxHash("");
                                  setPaidAmount(String(invoice.amount));
                                  setManualNote("");
                                }}
                              >
                                Settle
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
            {invoicesApi.data && (
              <div className="px-4 pb-4">
                <Pagination page={invoicesApi.data.meta.page} totalPages={invoicesApi.data.meta.total_pages} total={invoicesApi.data.meta.total} onChange={setPage} />
              </div>
            )}
          </Card>
        </>
      )}

      {tab === "webhooks" && (
        <>
          <div className="mb-4">
            <Select value={processed} onChange={(e) => { setProcessed(e.target.value); setPage(1); }} className="w-44">
              <option value="">All events</option>
              <option value="true">Processed</option>
              <option value="false">Unprocessed</option>
            </Select>
          </div>
          <Card bodyClassName="p-0">
            {webhooksApi.loading ? (
              <Loading label="Loading webhook events…" />
            ) : (webhooksApi.data?.items.length ?? 0) === 0 ? (
              <div className="p-5"><EmptyState title="No webhook events" description="Gateway callbacks will be logged here." /></div>
            ) : (
              <div className="table-wrap">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Provider</th>
                      <th>Event</th>
                      <th>Order</th>
                      <th>Signature</th>
                      <th>Processed</th>
                      <th>Source IP</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {webhooksApi.data!.items.map((event) => (
                      <tr key={event.id}>
                        <td className="text-xs uppercase">{event.provider}</td>
                        <td className="text-xs">{event.event_type || "—"}</td>
                        <td className="font-mono text-xs">{event.order_code || event.provider_invoice_id || "—"}</td>
                        <td><Badge tone={event.signature_valid ? "green" : "red"}>{event.signature_valid ? "Valid" : "Invalid"}</Badge></td>
                        <td><Badge tone={event.processed ? "green" : "amber"}>{event.processed ? "Yes" : "No"}</Badge></td>
                        <td className="text-xs text-slate-500">{event.source_ip || "—"}</td>
                        <td className="text-xs text-slate-500">{formatDate(event.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {webhooksApi.data && (
              <div className="px-4 pb-4">
                <Pagination page={webhooksApi.data.meta.page} totalPages={webhooksApi.data.meta.total_pages} total={webhooksApi.data.meta.total} onChange={setPage} />
              </div>
            )}
          </Card>
        </>
      )}

      {tab === "provider" && (
        <>
          {providerApi.loading ? (
            <Loading label="Loading provider…" />
          ) : providerApi.data ? (
            <div className="grid gap-4 lg:grid-cols-3">
              <StatCard
                label="Provider"
                value={providerApi.data.provider.toUpperCase()}
                hint={`${providerApi.data.currency} · ${providerApi.data.network.toUpperCase()}`}
                icon={<ShieldCheck className="h-4 w-4" />}
              />
              <StatCard
                label="Configuration"
                value={providerApi.data.configured ? "Configured" : "Missing keys"}
                hint={`Merchant UUID ${providerApi.data.merchant_uuid_set ? "set" : "missing"} · API key ${providerApi.data.api_key_set ? "set" : "missing"}`}
                tone={providerApi.data.configured ? "brand" : "rose"}
                icon={<ShieldCheck className="h-4 w-4" />}
              />
              <StatCard
                label="Webhook"
                value={providerApi.data.webhook_url ? "Configured" : "Not set"}
                hint={providerApi.data.webhook_url || "Set WEBHOOK_BASE_URL in backend config"}
                tone="sky"
                icon={<ShieldCheck className="h-4 w-4" />}
              />
              <Card title="Provider diagnostics" className="lg:col-span-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="primary" loading={busy === "provider-check"} onClick={() => void runProviderCheck()}>
                    Run connectivity check
                  </Button>
                  <Button onClick={() => providerApi.reload()}>Reload status</Button>
                </div>
                {checkResult && (
                  <div className="mt-4 rounded-xl border border-white/5 bg-white/[0.02] p-3 text-sm">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone={checkResult.reachable ? "green" : "red"}>
                        {checkResult.reachable ? "Reachable" : "Unreachable"}
                      </Badge>
                      <Badge tone={checkResult.usdt_bep20_supported ? "green" : "amber"}>
                        USDT BEP20 {checkResult.usdt_bep20_supported ? "supported" : "unverified"}
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">{checkResult.detail}</p>
                  </div>
                )}
                {providerApi.data.supported_networks.length > 0 && (
                  <p className="mt-4 text-xs text-slate-500">
                    Supported networks: {providerApi.data.supported_networks.join(", ")}
                  </p>
                )}
                {providerApi.data.notes && (
                  <p className="mt-2 text-xs text-slate-500">{providerApi.data.notes}</p>
                )}
              </Card>
            </div>
          ) : (
            <Card><p className="text-sm text-rose-300">{providerApi.error || "Unable to load provider status."}</p></Card>
          )}
        </>
      )}

      <Modal
        open={Boolean(manualInvoice)}
        onClose={() => setManualInvoice(null)}
        title="Settle invoice manually"
        description="Use only after verifying the blockchain transaction yourself."
        footer={
          <>
            <Button onClick={() => setManualInvoice(null)}>Cancel</Button>
            <Button variant="primary" loading={busy === "manual"} onClick={() => void submitManual()}>
              Mark paid
            </Button>
          </>
        }
      >
        {manualInvoice && (
          <div className="space-y-4">
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200">
              Invoice #{manualInvoice.id} · {money(manualInvoice.amount, manualInvoice.currency)} · {manualInvoice.network.toUpperCase()}
            </div>
            <Field label="Transaction hash">
              <Input value={txHash} onChange={(e) => setTxHash(e.target.value)} placeholder="0x…" />
            </Field>
            <Field label="Paid amount">
              <Input type="number" step="0.000001" value={paidAmount} onChange={(e) => setPaidAmount(e.target.value)} />
            </Field>
            <Field label="Internal note">
              <Textarea value={manualNote} onChange={(e) => setManualNote(e.target.value)} />
            </Field>
          </div>
        )}
      </Modal>
    </>
  );
}
