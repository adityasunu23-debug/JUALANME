"use client";

import { BellRing, Pencil, Save, Send } from "lucide-react";
import { useEffect, useState } from "react";

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
  Select,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate } from "@/lib/utils";

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
};

type Template = {
  id: number;
  code: string;
  language: string;
  title?: string | null;
  body: string;
  is_active: boolean;
};

const NOTIFY_KEYS = [
  "notification.order_paid_enabled",
  "notification.admin_new_order_enabled",
  "notification.admin_telegram_id",
  "general.store_name",
  "general.support_username",
  "general.store_channel",
  "general.maintenance_mode",
];

export default function NotificationsPage() {
  const toast = useToast();
  const settingsApi = useApi<Setting[]>("/settings");
  const templatesApi = useApi<Template[]>("/settings/templates");

  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<Template | null>(null);
  const [savingTemplate, setSavingTemplate] = useState(false);

  useEffect(() => {
    if (!settingsApi.data) return;
    const next: Record<string, string> = {};
    settingsApi.data
      .filter((row) => NOTIFY_KEYS.includes(row.key))
      .forEach((row) => {
        next[row.key] = row.value ?? "";
      });
    setValues(next);
  }, [settingsApi.data]);

  async function saveSettings() {
    setSaving(true);
    try {
      await api("/settings", { method: "PATCH", body: { values } });
      toast.success("Notification settings saved");
      settingsApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  async function saveTemplate() {
    if (!editing) return;
    setSavingTemplate(true);
    try {
      await api(`/settings/templates/${editing.id}`, {
        method: "PATCH",
        body: {
          title: editing.title || null,
          body: editing.body,
          is_active: editing.is_active,
        },
      });
      toast.success("Template updated");
      setEditing(null);
      templatesApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update template");
    } finally {
      setSavingTemplate(false);
    }
  }

  const templates = templatesApi.data ?? [];

  return (
    <>
      <PageHeader
        title="Notifications"
        description="Control which bot alerts fire and edit the message templates."
        actions={
          <Button variant="primary" loading={saving} onClick={() => void saveSettings()}>
            <Save className="h-4 w-4" /> Save settings
          </Button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-3">
        <Card title="Alert toggles" subtitle="Applies to every new transaction.">
          {settingsApi.loading ? (
            <Loading label="Loading settings..." />
          ) : (
            <div className="space-y-4">
              <Field label="Notify customer on payment">
                <Select
                  value={values["notification.order_paid_enabled"] || "true"}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      "notification.order_paid_enabled": event.target.value,
                    }))
                  }
                >
                  <option value="true">Enabled</option>
                  <option value="false">Disabled</option>
                </Select>
              </Field>
              <Field label="Notify admin on new order">
                <Select
                  value={values["notification.admin_new_order_enabled"] || "true"}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      "notification.admin_new_order_enabled": event.target.value,
                    }))
                  }
                >
                  <option value="true">Enabled</option>
                  <option value="false">Disabled</option>
                </Select>
              </Field>
              <Field
                label="Admin Telegram ID"
                hint="Destination for staff alerts. Empty uses ADMIN_TELEGRAM_IDS."
              >
                <Input
                  value={values["notification.admin_telegram_id"] || ""}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      "notification.admin_telegram_id": event.target.value,
                    }))
                  }
                  placeholder="123456789"
                />
              </Field>
              <Field label="Maintenance mode" hint="Shows a maintenance notice in the bot.">
                <Select
                  value={values["general.maintenance_mode"] || "false"}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      "general.maintenance_mode": event.target.value,
                    }))
                  }
                >
                  <option value="false">Off</option>
                  <option value="true">On</option>
                </Select>
              </Field>
            </div>
          )}
        </Card>

        <Card
          title="Store identity"
          subtitle="Shown in the bot welcome message."
          className="xl:col-span-2"
        >
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Store name">
              <Input
                value={values["general.store_name"] || ""}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    "general.store_name": event.target.value,
                  }))
                }
              />
            </Field>
            <Field label="Support username">
              <Input
                value={values["general.support_username"] || ""}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    "general.support_username": event.target.value,
                  }))
                }
                placeholder="@support"
              />
            </Field>
            <Field label="Store channel">
              <Input
                value={values["general.store_channel"] || ""}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    "general.store_channel": event.target.value,
                  }))
                }
                placeholder="@channel"
              />
            </Field>
          </div>
          <div className="mt-4 flex items-start gap-3 rounded-xl border border-sky-500/20 bg-sky-500/5 p-3 text-xs text-sky-200">
            <BellRing className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <p className="leading-relaxed">
              Notifications are delivered through the Telegram Bot API. The bot token
              must be configured in the environment for messages to be sent.
            </p>
          </div>
        </Card>
      </div>

      <Card
        title="Message templates"
        subtitle="Overrides for localized bot messages."
        className="mt-4"
        bodyClassName="p-0"
      >
        {templatesApi.loading ? (
          <Loading label="Loading templates..." />
        ) : templates.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="No templates"
              description="Templates are optional overrides; the built-in localized copy is used otherwise."
            />
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Language</th>
                  <th>Title</th>
                  <th>Preview</th>
                  <th>Status</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {templates.map((template) => (
                  <tr key={template.id}>
                    <td className="font-mono text-xs text-brand-300">{template.code}</td>
                    <td>
                      <Badge tone={template.language === "id" ? "blue" : "violet"}>
                        {template.language.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="text-sm text-slate-300">{template.title || "—"}</td>
                    <td className="max-w-[320px]">
                      <p className="truncate text-xs text-slate-500">{template.body}</p>
                    </td>
                    <td>
                      <Badge tone={template.is_active ? "green" : "gray"}>
                        {template.is_active ? "Active" : "Off"}
                      </Badge>
                    </td>
                    <td>
                      <div className="flex justify-end">
                        <button
                          type="button"
                          onClick={() => setEditing(template)}
                          className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-sky-300"
                          title="Edit template"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        title={editing ? `Edit template · ${editing.code}` : "Edit template"}
        description="Placeholders such as {order_code} are replaced at send time."
        size="lg"
        footer={
          <>
            <Button onClick={() => setEditing(null)}>Cancel</Button>
            <Button variant="primary" loading={savingTemplate} onClick={() => void saveTemplate()}>
              <Send className="h-4 w-4" /> Save template
            </Button>
          </>
        }
      >
        {editing && (
          <div className="space-y-4">
            <Field label="Title">
              <Input
                value={editing.title || ""}
                onChange={(event) => setEditing({ ...editing, title: event.target.value })}
              />
            </Field>
            <Field label="Body">
              <Textarea
                className="min-h-[180px] font-mono text-xs"
                value={editing.body}
                onChange={(event) => setEditing({ ...editing, body: event.target.value })}
              />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={editing.is_active}
                onChange={(event) =>
                  setEditing({ ...editing, is_active: event.target.checked })
                }
              />
              Active
            </label>
            <p className="text-xs text-slate-500">
              Created {formatDate(null)} · language {editing.language.toUpperCase()}
            </p>
          </div>
        )}
      </Modal>
    </>
  );
}