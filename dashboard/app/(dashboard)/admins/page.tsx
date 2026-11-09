"use client";

import { Pencil, Plus, Trash2 } from "lucide-react";
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
} from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/use-api";
import { formatDate, humanize } from "@/lib/utils";

type Admin = {
  id: number;
  telegram_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  role: string;
  is_active: boolean;
  notes?: string | null;
  last_login_at?: string | null;
  created_at?: string | null;
};

type RoleOption = { value: string; label: string; permissions: string[] };
type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

const empty = {
  telegram_id: "",
  username: "",
  first_name: "",
  last_name: "",
  role: "SUPPORT_ADMIN",
  is_active: true,
  notes: "",
};

export default function AdminsPage() {
  const toast = useToast();
  const { admin: me } = useAuth();
  const [page, setPage] = useState(1);
  const [form, setForm] = useState<typeof empty & { id?: number } | null>(null);
  const [saving, setSaving] = useState(false);

  const { data, loading, error, reload } = useApi<Page<Admin>>(`/admins?page=${page}&page_size=20`);
  const rolesApi = useApi<RoleOption[]>("/admins/roles");
  const roles = rolesApi.data ?? [];
  const admins = data?.items ?? [];

  const rolePermissions = useMemo(() => {
    const map = new Map<string, string[]>();
    roles.forEach((role) => map.set(role.value, role.permissions));
    return map;
  }, [roles]);

  async function save() {
    if (!form) return;
    setSaving(true);
    try {
      if (form.id) {
        await api(`/admins/${form.id}`, {
          method: "PATCH",
          body: { role: form.role, is_active: form.is_active, notes: form.notes || null },
        });
        toast.success("Admin updated");
      } else {
        await api("/admins", {
          method: "POST",
          body: {
            telegram_id: Number(form.telegram_id),
            username: form.username || null,
            first_name: form.first_name || null,
            last_name: form.last_name || null,
            role: form.role,
            is_active: form.is_active,
            notes: form.notes || null,
          },
        });
        toast.success("Admin invited");
      }
      setForm(null);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save admin");
    } finally {
      setSaving(false);
    }
  }

  async function deactivate(admin: Admin) {
    if (admin.id === me?.id) {
      toast.error("You cannot deactivate your own account");
      return;
    }
    if (!window.confirm(`Deactivate ${admin.first_name || admin.username || admin.telegram_id}?`)) return;
    try {
      await api(`/admins/${admin.id}`, { method: "DELETE" });
      toast.success("Admin deactivated");
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to deactivate");
    }
  }

  return (
    <>
      <PageHeader
        title="Admins"
        description="Owner-only access control for the dashboard and API."
        actions={
          <Button variant="primary" onClick={() => setForm({ ...empty })}>
            <Plus className="h-4 w-4" /> Invite admin
          </Button>
        }
      />

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading admins…" />
        ) : error ? (
          <p className="p-5 text-sm text-rose-300">{error}</p>
        ) : admins.length === 0 ? (
          <div className="p-5"><EmptyState title="No admins" /></div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Admin</th>
                  <th>Telegram</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Last login</th>
                  <th>Permissions</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {admins.map((admin) => (
                  <tr key={admin.id}>
                    <td>
                      <p className="text-sm text-slate-100">
                        {[admin.first_name, admin.last_name].filter(Boolean).join(" ") || `Admin #${admin.id}`}
                        {admin.id === me?.id && <Badge tone="blue" className="ml-2">You</Badge>}
                      </p>
                      <p className="text-[11px] text-slate-500">Joined {formatDate(admin.created_at, false)}</p>
                    </td>
                    <td>
                      <p className="text-xs">@{admin.username || "—"}</p>
                      <p className="font-mono text-[11px] text-slate-500">{admin.telegram_id}</p>
                    </td>
                    <td><Badge tone={admin.role === "OWNER" ? "violet" : "blue"}>{humanize(admin.role)}</Badge></td>
                    <td><Badge tone={admin.is_active ? "green" : "gray"}>{admin.is_active ? "Active" : "Inactive"}</Badge></td>
                    <td className="text-xs text-slate-500">{formatDate(admin.last_login_at)}</td>
                    <td className="max-w-[240px]">
                      {admin.role === "OWNER" ? (
                        <span className="text-xs text-violet-300">All permissions</span>
                      ) : (
                        <span className="text-[11px] text-slate-500">
                          {(rolePermissions.get(admin.role) || []).join(", ") || "—"}
                        </span>
                      )}
                    </td>
                    <td>
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          onClick={() =>
                            setForm({
                              id: admin.id,
                              telegram_id: String(admin.telegram_id),
                              username: admin.username || "",
                              first_name: admin.first_name || "",
                              last_name: admin.last_name || "",
                              role: admin.role,
                              is_active: admin.is_active,
                              notes: admin.notes || "",
                            })
                          }
                          className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-sky-300"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => void deactivate(admin)}
                          className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-rose-300"
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

      <Modal
        open={Boolean(form)}
        onClose={() => setForm(null)}
        title={form?.id ? "Edit admin" : "Invite admin"}
        description="The person must sign in with the Telegram Login Widget using this ID."
        footer={
          <>
            <Button onClick={() => setForm(null)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void save()}>
              {form?.id ? "Save changes" : "Send invite"}
            </Button>
          </>
        }
      >
        {form && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Telegram ID">
              <Input
                value={form.telegram_id}
                disabled={Boolean(form.id)}
                onChange={(e) => setForm({ ...form, telegram_id: e.target.value })}
                inputMode="numeric"
              />
            </Field>
            <Field label="Username">
              <Input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </Field>
            <Field label="First name">
              <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </Field>
            <Field label="Last name">
              <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </Field>
            <Field label="Role">
              <Select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {roles.map((role) => (
                  <option key={role.value} value={role.value}>{role.label}</option>
                ))}
              </Select>
            </Field>
            <Field label="Notes">
              <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </Field>
            <div className="sm:col-span-2 rounded-xl border border-white/5 bg-white/[0.02] p-3 text-xs text-slate-400">
              <p className="mb-1 font-medium text-slate-300">Permissions</p>
              {(rolePermissions.get(form.role) || []).join(", ") || "All permissions"}
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300 sm:col-span-2">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
              Active
            </label>
          </div>
        )}
      </Modal>
    </>
  );
}
