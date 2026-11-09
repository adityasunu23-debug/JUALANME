"use client";

import { FolderTree, Pencil, Plus, Trash2 } from "lucide-react";
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
  SearchField,
  Select,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, number } from "@/lib/utils";

type Category = {
  id: number;
  slug: string;
  name_id: string;
  name_en: string;
  description_id?: string | null;
  description_en?: string | null;
  icon: string;
  sort_order: number;
  is_active: boolean;
  product_count: number;
  created_at?: string | null;
};

const empty = {
  slug: "",
  name_id: "",
  name_en: "",
  description_id: "",
  description_en: "",
  icon: "*",
  sort_order: "0",
  is_active: true,
};

export default function CategoriesPage() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [active, setActive] = useState("");
  const [form, setForm] = useState<(typeof empty & { id?: number }) | null>(null);
  const [saving, setSaving] = useState(false);

  const { data, loading, error, reload } = useApi<Category[]>("/categories");

  const categories = useMemo(() => {
    const rows = data ?? [];
    return rows.filter((row) => {
      const haystack = [row.slug, row.name_id, row.name_en].join(" ").toLowerCase();
      const matchesSearch = search ? haystack.includes(search.toLowerCase()) : true;
      const matchesActive =
        active === "" ? true : active === "true" ? row.is_active : !row.is_active;
      return matchesSearch && matchesActive;
    });
  }, [data, search, active]);

  function openEdit(category: Category) {
    setForm({
      id: category.id,
      slug: category.slug,
      name_id: category.name_id,
      name_en: category.name_en,
      description_id: category.description_id || "",
      description_en: category.description_en || "",
      icon: category.icon || "*",
      sort_order: String(category.sort_order),
      is_active: category.is_active,
    });
  }

  async function save() {
    if (!form) return;
    if (!form.slug.trim() || !form.name_id.trim() || !form.name_en.trim()) {
      toast.error("Slug and both names are required");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        slug: form.slug.trim().toLowerCase(),
        name_id: form.name_id,
        name_en: form.name_en,
        description_id: form.description_id || null,
        description_en: form.description_en || null,
        icon: form.icon || "*",
        sort_order: Number(form.sort_order || 0),
        is_active: form.is_active,
      };
      if (form.id) {
        await api(`/categories/${form.id}`, { method: "PATCH", body: payload });
        toast.success("Category updated");
      } else {
        await api("/categories", { method: "POST", body: payload });
        toast.success("Category created");
      }
      setForm(null);
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save category");
    } finally {
      setSaving(false);
    }
  }

  async function remove(category: Category) {
    if (!window.confirm(`Delete category "${category.name_en}"?`)) return;
    try {
      await api(`/categories/${category.id}`, { method: "DELETE" });
      toast.success("Category deleted");
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Categories"
        description="Group products so customers can browse the bot catalogue faster."
        actions={
          <Button variant="primary" onClick={() => setForm({ ...empty })}>
            <Plus className="h-4 w-4" /> New category
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <SearchField
          value={search}
          onChange={setSearch}
          placeholder="Search categories..."
          className="w-64"
        />
        <Select
          value={active}
          onChange={(event) => setActive(event.target.value)}
          className="w-44"
        >
          <option value="">All categories</option>
          <option value="true">Active only</option>
          <option value="false">Inactive only</option>
        </Select>
      </div>

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading categories..." />
        ) : error ? (
          <p className="p-5 text-sm text-rose-300">{error}</p>
        ) : categories.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="No categories yet"
              description="Create your first category so products are easier to find."
            />
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Slug</th>
                  <th>Products</th>
                  <th>Order</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {categories.map((category) => (
                  <tr key={category.id}>
                    <td>
                      <div className="flex items-center gap-3">
                        <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-brand-300">
                          {category.icon && category.icon !== "*" ? (
                            <span className="text-sm">{category.icon}</span>
                          ) : (
                            <FolderTree className="h-4 w-4" />
                          )}
                        </span>
                        <div>
                          <p className="text-sm font-medium text-white">
                            {category.name_en}
                          </p>
                          <p className="text-[11px] text-slate-500">
                            {category.name_id}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="font-mono text-xs text-slate-400">{category.slug}</td>
                    <td>{number(category.product_count)}</td>
                    <td className="text-xs text-slate-500">{category.sort_order}</td>
                    <td>
                      <Badge tone={category.is_active ? "green" : "gray"}>
                        {category.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="text-xs text-slate-500">
                      {formatDate(category.created_at, false)}
                    </td>
                    <td>
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openEdit(category)}
                          className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-sky-300"
                          title="Edit"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => void remove(category)}
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
      </Card>

      <Modal
        open={Boolean(form)}
        onClose={() => setForm(null)}
        title={form?.id ? "Edit category" : "New category"}
        size="lg"
        footer={
          <>
            <Button onClick={() => setForm(null)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void save()}>
              {form?.id ? "Save changes" : "Create category"}
            </Button>
          </>
        }
      >
        {form && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Slug" hint="Lowercase, used in URLs.">
              <Input
                value={form.slug}
                onChange={(event) => setForm({ ...form, slug: event.target.value })}
                placeholder="game-topup"
              />
            </Field>
            <Field label="Icon" hint="Short character shown in the bot.">
              <Input
                value={form.icon}
                onChange={(event) => setForm({ ...form, icon: event.target.value })}
                placeholder="*"
              />
            </Field>
            <Field label="Name (ID)">
              <Input
                value={form.name_id}
                onChange={(event) => setForm({ ...form, name_id: event.target.value })}
              />
            </Field>
            <Field label="Name (EN)">
              <Input
                value={form.name_en}
                onChange={(event) => setForm({ ...form, name_en: event.target.value })}
              />
            </Field>
            <Field label="Description (ID)" className="sm:col-span-2">
              <Textarea
                value={form.description_id}
                onChange={(event) =>
                  setForm({ ...form, description_id: event.target.value })
                }
              />
            </Field>
            <Field label="Description (EN)" className="sm:col-span-2">
              <Textarea
                value={form.description_en}
                onChange={(event) =>
                  setForm({ ...form, description_en: event.target.value })
                }
              />
            </Field>
            <Field label="Sort order" hint="Lower numbers appear first.">
              <Input
                type="number"
                value={form.sort_order}
                onChange={(event) => setForm({ ...form, sort_order: event.target.value })}
              />
            </Field>
            <label className="flex items-center gap-2 self-end text-sm text-slate-300">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  setForm({ ...form, is_active: event.target.checked })
                }
              />
              Active
            </label>
          </div>
        )}
      </Modal>
    </>
  );
}