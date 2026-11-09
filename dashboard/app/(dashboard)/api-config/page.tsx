"use client";

import { CheckCircle2, Copy, KeyRound, Link2, RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  InfoGrid,
  Loading,
  PageHeader,
  Select,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Setting = {
  id: number;
  key: string;
  value?: string | null;
  group: string;
  label?: string | null;
  value_type: string;
  is_secret: boolean;
  is_editable: boolean;
};

type ApiConfig = {
  payment_provider: string;
  cryptomus_configured: boolean;
  cryptomus_network: string;
  payment_currency: string;
  webhook_url: string;
  webhook_secret_set: boolean;
  invoice_lifetime_minutes: number;
  bot_configured: boolean;
  bot_username: string;
  auto_delivery_enabled: boolean;
  min_confirmations: number;
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

const PAYMENT_KEYS = [
  "payment.provider",
  "payment.cryptomus_merchant_uuid",
  "payment.cryptomus_api_key",
  "payment.network",
  "payment.currency",
  "payment.invoice_lifetime_minutes",
  "payment.min_confirmations",
  "payment.auto_verify",
];

const MASK = "********";

export default function ApiConfigPage() {
  const toast = useToast();
  const settingsApi = useApi<Setting[]>("/settings");
  const configApi = useApi<ApiConfig>("/settings/api-config");
  const providerApi = useApi<ProviderStatus>("/payments/provider");

  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [check, setCheck] = useState<ProviderCheck | null>(null);

  useEffect(() => {
    if (!settingsApi.data) return;
    const next: Record<string, string> = {};
    settingsApi.data
      .filter((row) => PAYMENT_KEYS.includes(row.key))
      .forEach((row) => {
        next[row.key] = row.value ?? "";
      });
    setValues(next);
  }, [settingsApi.data]);

  async function save() {
    setSaving(true);
    try {
      await api("/settings", { method: "PATCH", body: { values } });
      toast.success("API configuration saved");
      settingsApi.reload();
      configApi.reload();
      providerApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  }

  async function runProviderCheck() {
    setChecking(true);
    setCheck(null);
    try {
      const result = await api<ProviderCheck>("/payments/provider-check", {
        method: "POST",
      });
      setCheck(result);
      if (result.reachable) toast.success("Gateway reachable");
      else toast.error(result.detail);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Provider check failed");
    } finally {
      setChecking(false);
    }
  }

  async function copy(text?: string | null) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Clipboard unavailable");
    }
  }

  function set(key: string, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  const config = configApi.data;
  const provider = providerApi.data;

  return (
    <>
      <PageHeader
        title="API configuration"
        description="Payment gateway credentials, network and webhook endpoint."
        actions={
          <>
            <Button onClick={() => void runProviderCheck()} loading={checking}>
              <RefreshCw className="h-4 w-4" /> Test connection
            </Button>
            <Button variant="primary" loading={saving} onClick={() => void save()}>
              Save configuration
            </Button>
          </>
        }
      />

      {configApi.loading ? (
        <Loading label="Loading configuration..." />
      ) : (
        <div className="grid gap-4 xl:grid-cols-3">
          <Card title="Current status" className="xl:col-span-1">
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-400">Provider</span>
                <Badge tone="blue">{config?.payment_provider?.toUpperCase() || "-"}</Badge>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-400">Credentials</span>
                <Badge tone={config?.cryptomus_configured ? "green" : "amber"}>
                  {config?.cryptomus_configured ? "Configured" : "Incomplete"}
                </Badge>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-400">Network</span>
                <span className="font-mono text-xs text-slate-200">
                  {config?.cryptomus_network?.toUpperCase() || "-"}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-400">Currency</span>
                <span className="text-slate-200">{config?.payment_currency}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-400">Invoice lifetime</span>
                <span className="text-slate-200">
                  {config?.invoice_lifetime_minutes} min
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-400">Auto delivery</span>
                <Badge tone={config?.auto_delivery_enabled ? "green" : "gray"}>
                  {config?.auto_delivery_enabled ? "Enabled" : "Manual"}
                </Badge>
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200">
              <p className="flex items-center gap-2 font-medium">
                <ShieldAlert className="h-3.5 w-3.5" /> USDT BEP20
              </p>
              <p className="mt-1 leading-relaxed">
                Pastikan USDT jaringan BEP20 (BSC) sudah aktif di akun merchant
                Cryptomus sebelum menerima pembayaran nyata. Gunakan tombol
                "Test connection" untuk memeriksa.
              </p>
            </div>
          </Card>

          <Card
            title="Gateway credentials"
            subtitle="Saved values are applied immediately, no redeploy needed."
            className="xl:col-span-2"
          >
            {settingsApi.loading ? (
              <Loading label="Loading settings..." />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Payment provider">
                  <Select
                    value={values["payment.provider"] || "cryptomus"}
                    onChange={(event) => set("payment.provider", event.target.value)}
                  >
                    <option value="cryptomus">Cryptomus</option>
                    <option value="mock">Mock (development only)</option>
                  </Select>
                </Field>
                <Field label="Network">
                  <Select
                    value={values["payment.network"] || "bep20"}
                    onChange={(event) => set("payment.network", event.target.value)}
                  >
                    <option value="bep20">BEP20 (BSC)</option>
                  </Select>
                </Field>
                <Field label="Merchant UUID" hint="From your Cryptomus merchant dashboard.">
                  <Input
                    value={values["payment.cryptomus_merchant_uuid"] || ""}
                    onChange={(event) =>
                      set("payment.cryptomus_merchant_uuid", event.target.value)
                    }
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  />
                </Field>
                <Field label="API key" hint="Leave as-is to keep the stored secret.">
                  <Input
                    type="password"
                    value={values["payment.cryptomus_api_key"] || ""}
                    onChange={(event) =>
                      set("payment.cryptomus_api_key", event.target.value)
                    }
                    placeholder={MASK}
                  />
                </Field>
                <Field label="Currency">
                  <Input
                    value={values["payment.currency"] || "USDT"}
                    onChange={(event) => set("payment.currency", event.target.value)}
                  />
                </Field>
                <Field label="Invoice lifetime (minutes)">
                  <Input
                    type="number"
                    value={values["payment.invoice_lifetime_minutes"] || "30"}
                    onChange={(event) =>
                      set("payment.invoice_lifetime_minutes", event.target.value)
                    }
                  />
                </Field>
                <Field label="Minimum confirmations">
                  <Input
                    type="number"
                    value={values["payment.min_confirmations"] || "1"}
                    onChange={(event) =>
                      set("payment.min_confirmations", event.target.value)
                    }
                  />
                </Field>
                <Field label="Automatic verification">
                  <Select
                    value={values["payment.auto_verify"] || "true"}
                    onChange={(event) => set("payment.auto_verify", event.target.value)}
                  >
                    <option value="true">Enabled</option>
                    <option value="false">Disabled (manual review)</option>
                  </Select>
                </Field>
              </div>
            )}
          </Card>
        </div>
      )}

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <Card title="Webhook endpoint" subtitle="Register this URL at your gateway.">
          <div className="flex flex-wrap items-center gap-2">
            <code className="flex-1 overflow-x-auto rounded-xl border border-white/10 bg-ink-950 px-3 py-2 text-xs text-brand-300">
              {provider?.webhook_url || config?.webhook_url || "Not configured"}
            </code>
            <Button
              onClick={() => void copy(provider?.webhook_url || config?.webhook_url)}
            >
              <Copy className="h-4 w-4" /> Copy
            </Button>
          </div>
          <InfoGrid
            items={[
              {
                label: "Signature validation",
                value: config?.webhook_secret_set ? "Bot secret configured" : "Default on",
              },
              {
                label: "Supported networks",
                value: (provider?.supported_networks ?? ["bep20"]).join(", ").toUpperCase(),
              },
              {
                label: "Merchant UUID",
                value: provider?.merchant_uuid_set ? "Set" : "Not set",
              },
              { label: "API key", value: provider?.api_key_set ? "Set" : "Not set" },
            ]}
          />
        </Card>

        <Card title="Connection test" subtitle="Calls the gateway API from the server.">
          {check ? (
            <div
              className={`rounded-xl border p-4 text-sm ${
                check.reachable
                  ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-200"
                  : "border-rose-500/20 bg-rose-500/5 text-rose-200"
              }`}
            >
              <p className="flex items-center gap-2 font-medium">
                {check.reachable ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <ShieldAlert className="h-4 w-4" />
                )}
                {check.reachable ? "Gateway reachable" : "Gateway unreachable"}
              </p>
              <p className="mt-1 text-xs leading-relaxed">{check.detail}</p>
              <p className="mt-2 text-xs">
                USDT BEP20 supported: {check.usdt_bep20_supported ? "yes" : "unconfirmed"}
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-white/10 p-6 text-center text-xs text-slate-500">
              <KeyRound className="mx-auto mb-2 h-5 w-5 text-slate-600" />
              Run a connection test to verify credentials and BEP20 availability.
            </div>
          )}
          {provider?.notes && (
            <p className="mt-3 flex items-start gap-2 text-xs text-slate-500">
              <Link2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {provider.notes}
            </p>
          )}
        </Card>
      </div>
    </>
  );
}