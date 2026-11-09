"use client";

import { Save, Settings2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useToast } from "@/components/toast";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  Loading,
  Modal,
  PageHeader,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { humanize } from "@/lib/utils";

type Setting = {
  id: number;
  key: string;
  value?: string | null;
  group: string;
  label?: string | null;
  description?: string | null;
  value_type: string;
  is_secret: boolean;
  is_editable: boolean;
  sort_order: number;
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

type Template = {
  id: number;
  code: string;
  language: string;
  title?: string | null;
  body: string;
  is_active: boolean;
};

export default function SettingsPage() {
  const toast = useToast();
  const settingsApi = useApi<Setting[]>("/settings");
  const configApi = useApi<ApiConfig>("/settings/api-config");
  const templatesApi = useApi<Template[]>("/settings/templates");
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [template, setTemplate] = useState<Template | null>(null);
  const [templateBody, setTemplateBody] = useState("");
  const [templateTitle, setTemplateTitle] = useState("");
  const [templateActive, setTemplateActive] = useState(true);

  useEffect(() => {
    if (!settingsApi.data) return;
    const next: Record<string, string> = {};
    settingsApi.data.forEach((setting) => {
      next[setting.key] = setting.value ?? "";
    });
    setValues(next);
  }, [settingsApi.data]);

  const groups = useMemo(() => {
    const map = new Map<string, Setting[]>();
    (settingsApi.data ?? []).forEach((setting) => {
      const list = map.get(setting.group) || [];
      list.push(setting);
      map.set(setting.group, list);
    });
    return Array.from(map.entries()).map(([name, items]) => ({
      name,
      items: items.sort((a, b) => a.sort_order - b.sort_order),
    }));
  }, [settingsApi.data]);

  async function saveSettings() {
    setSaving(true);
    try {
      await api("/settings", { method: "PATCH", body: { values } });
      toast.success("Settings saved");
      settingsApi.reload();
      configApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  function openTemplate(item: Template) {
    setTemplate(item);
    setTemplateTitle(item.title || "");
    setTemplateBody(item.body);
    setTemplateActive(item.is_active);
  }

  async function saveTemplate() {
    if (!template) return;
    setSaving(true);
    try {
      await api(`/settings/templates/${template.id}`, {
        method: "PATCH",
        body: { title: templateTitle || null, body: templateBody, is_active: templateActive },
      });
      toast.success("Template updated");
      setTemplate(null);
      templatesApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update template");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Settings"
        description="Store defaults, payment credentials and notification templates."
        actions={
          <Button variant="primary" loading={saving} onClick={() => void saveSettings()}>
            <Save className="h-4 w-4" /> Save settings
          </Button>
        }
      />

      {configApi.data && (
        <div className="mb-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[
            {
              label: "Payment provider",
              value: configApi.data.payment_provider.toUpperCase(),
              hint: `${configApi.data.payment_currency} · ${configApi.data.cryptomus_network.toUpperCase()}`,
              tone: configApi.data.cryptomus_configured ? "green" : "red",
            },
            {
              label: "Webhook",
              value: configApi.data.webhook_secret_set ? "Secret set" : "Secret missing",
              hint: configApi.data.webhook_url,
              tone: configApi.data.webhook_secret_set ? "green" : "amber",
            },
            {
              label: "Bot",
              value: configApi.data.bot_configured ? "Connected" : "Not configured",
              hint: `@${configApi.data.bot_username}`,
              tone: configApi.data.bot_configured ? "green" : "red",
            },
            {
              label: "Auto delivery",
              value: configApi.data.auto_delivery_enabled ? "Enabled" : "Disabled",
              hint: `${configApi.data.invoice_lifetime_minutes} min invoices · ${configApi.data.min_confirmations} confirmations`,
              tone: configApi.data.auto_delivery_enabled ? "green" : "amber",
            },
          ].map((item) => (
            <div key={item.label} className="panel p-4">
              <p className="text-[11px] uppercase tracking-wide text-slate-500">{item.label}</p>
              <div className="mt-1 flex items-center gap-2">
                <p className="text-sm font-medium text-white">{item.value}</p>
                <Badge tone={item.tone as "green" | "red" | "amber"}>{item.tone === "green" ? "OK" : "Check"}</Badge>
              </div>
              <p className="mt-1 break-all text-[11px] text-slate-500">{item.hint}</p>
            </div>
          ))}
        </div>
      )}

      {settingsApi.loading ? (
        <Loading label="Loading settings…" />
      ) : settingsApi.error ? (
        <Card><p className="text-sm text-rose-300">{settingsApi.error}</p></Card>
      ) : (
        <div className="space-y-4">
          {groups.map((group) => (
            <Card key={group.name} title={humanize(group.name)} subtitle="Editable store configuration">
              <div className="grid gap-4 md:grid-cols-2">
                {group.items.map((setting) => (
                  <Field
                    key={setting.key}
                    label={setting.label || setting.key}
                    hint={setting.description || setting.key}
                  >
                    {setting.value_type === "bool" ? (
                      <Select
                        value={values[setting.key] === "true" ? "true" : "false"}
                        disabled={!setting.is_editable}
                        onChange={(e) => setValues({ ...values, [setting.key]: e.target.value })}
                      >
                        <option value="true">Enabled</option>
                        <option value="false">Disabled</option>
                      </Select>
                    ) : setting.value_type === "text" ? (
                      <Textarea
                        value={values[setting.key] ?? ""}
                        disabled={!setting.is_editable}
                        onChange={(e) => setValues({ ...values, [setting.key]: e.target.value })}
                      />
                    ) : (
                      <Input
                        type={setting.is_secret ? "password" : setting.value_type === "int" || setting.value_type === "float" ? "number" : "text"}
                        value={values[setting.key] ?? ""}
                        disabled={!setting.is_editable}
                        placeholder={setting.is_secret ? "Leave blank to keep current value" : ""}
                        onChange={(e) => setValues({ ...values, [setting.key]: e.target.value })}
                      />
                    )}
                  </Field>
                ))}
              </div>
            </Card>
          ))}

          <Card
            title="Notification templates"
            subtitle="Telegram HTML messages sent to customers and admins"
            bodyClassName="p-0"
            actions={<Settings2 className="h-4 w-4 text-slate-500" />}
          >
            {templatesApi.loading ? (
              <Loading />
            ) : (templatesApi.data?.length ?? 0) === 0 ? (
              <p className="p-5 text-sm text-slate-500">No templates configured.</p>
            ) : (
              <div className="table-wrap">
                <table className="tbl">
                  <thead>
                    <tr><th>Code</th><th>Language</th><th>Title</th><th>Status</th><th className="text-right">Actions</th></tr>
                  </thead>
                  <tbody>
                    {templatesApi.data!.map((item) => (
                      <tr key={item.id}>
                        <td className="font-mono text-xs">{item.code}</td>
                        <td className="text-xs uppercase">{item.language}</td>
                        <td className="max-w-[320px] truncate">{item.title || item.body.slice(0, 80)}</td>
                        <td><Badge tone={item.is_active ? "green" : "gray"}>{item.is_active ? "Active" : "Inactive"}</Badge></td>
                        <td>
                          <div className="flex justify-end">
                            <Button size="sm" onClick={() => openTemplate(item)}>Edit</Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      <Modal
        open={Boolean(template)}
        onClose={() => setTemplate(null)}
        title={template ? `Template · ${template.code}` : "Template"}
        size="lg"
        footer={
          <>
            <Button onClick={() => setTemplate(null)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void saveTemplate()}>Save template</Button>
          </>
        }
      >
        {template && (
          <div className="space-y-4">
            <Field label="Title">
              <Input value={templateTitle} onChange={(e) => setTemplateTitle(e.target.value)} />
            </Field>
            <Field label="Body" hint="HTML is supported. Keep placeholders unchanged.">
              <Textarea value={templateBody} onChange={(e) => setTemplateBody(e.target.value)} className="min-h-[220px] font-mono" />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={templateActive} onChange={(e) => setTemplateActive(e.target.checked)} />
              Active
            </label>
            <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
              <p className="mb-1 text-[11px] uppercase text-slate-500">Preview</p>
              <p className="whitespace-pre-wrap text-xs text-slate-400">{templateBody}</p>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
