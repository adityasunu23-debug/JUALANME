"use client";

import { Download, Plus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

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
  StatCard,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { api, downloadFile } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, number, queryString } from "@/lib/utils";

type Product = { id: number; name_en: string; delivery_type: string };
type StockSummary = {
  product_id: number;
  product_name: string;
  delivery_type: string;
  available: number;
  sold: number;
  total: number;
  low_stock: boolean;
};
type StockItem = {
  id: number;
  product_id: number;
  content: string;
  label?: string | null;
  is_used: boolean;
  order_id?: number | null;
  used_at?: string | null;
  source: string;
  created_at?: string | null;
};
type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

export default function StockPage() {
  const toast = useToast();
  const [productFilter, setProductFilter] = useState("");
  const [usedFilter, setUsedFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [importOpen, setImportOpen] = useState(false);
  const [importProduct, setImportProduct] = useState("");
  const [importLines, setImportLines] = useState("");
  const [label, setLabel] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const product = params.get("product");
    if (product) setProductFilter(product);
  }, []);

  const productsApi = useApi<Page<Product>>("/products?page_size=200&page=1");
  const products = productsApi.data?.items ?? [];
  const summaryApi = useApi<StockSummary[]>("/stock/summary");
  const summary = summaryApi.data ?? [];
  const itemsPath = `/stock${queryString({
    product_id: productFilter,
    used: usedFilter,
    search,
    page,
    page_size: 20,
  })}`;
  const itemsApi = useApi<Page<StockItem>>(itemsPath);
  const items = itemsApi.data?.items ?? [];

  const totals = useMemo(
    () =>
      summary.reduce(
        (acc, item) => ({
          available: acc.available + item.available,
          sold: acc.sold + item.sold,
          low: acc.low + (item.low_stock ? 1 : 0),
        }),
        { available: 0, sold: 0, low: 0 }
      ),
    [summary]
  );

  function openImport(productId?: number) {
    setImportProduct(productId ? String(productId) : productFilter);
    setImportLines("");
    setLabel("");
    setImportOpen(true);
  }

  async function submitImport() {
    if (!importProduct) {
      toast.error("Choose a product first");
      return;
    }
    const lines = importLines
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (!lines.length) {
      toast.error("Add at least one stock line");
      return;
    }
    setSaving(true);
    try {
      const result = await api<{ imported: number; duplicates: number; message: string }>("/stock", {
        method: "POST",
        body: {
          product_id: Number(importProduct),
          lines,
          label: label || null,
          deduplicate: true,
        },
      });
      toast.success(result.message || `${result.imported} items imported`);
      setImportOpen(false);
      itemsApi.reload();
      summaryApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      setSaving(false);
    }
  }

  async function removeItem(item: StockItem) {
    if (!window.confirm("Delete this unused stock item?")) return;
    try {
      await api(`/stock/${item.id}`, { method: "DELETE" });
      toast.success("Stock item deleted");
      itemsApi.reload();
      summaryApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  async function exportItems() {
    try {
      const suffix = queryString({ product_id: productFilter, used: usedFilter || undefined });
      await downloadFile(`/stock/export${suffix}`, "stock-export.csv");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Export failed");
    }
  }

  return (
    <>
      <PageHeader
        title="Stock"
        description="Deliverable items for automatic fulfilment."
        actions={
          <>
            <Button onClick={() => void exportItems()}>
              <Download className="h-4 w-4" /> Export CSV
            </Button>
            <Button variant="primary" onClick={() => openImport()}>
              <Plus className="h-4 w-4" /> Import stock
            </Button>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Available" value={number(totals.available)} hint="Unused items ready to deliver" icon={<span className="text-xs font-bold">AV</span>} />
        <StatCard label="Delivered" value={number(totals.sold)} hint="Items already sold" tone="sky" icon={<span className="text-xs font-bold">SL</span>} />
        <StatCard label="Low stock" value={number(totals.low)} hint="Products below threshold" tone="amber" icon={<span className="text-xs font-bold">LW</span>} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Stock by product" subtitle="Import or inspect each product" className="lg:col-span-1" bodyClassName="p-0">
          {summaryApi.loading ? (
            <Loading />
          ) : summary.length === 0 ? (
            <div className="p-4"><EmptyState title="No stock recorded" /></div>
          ) : (
            <div className="max-h-[420px] overflow-y-auto p-3">
              {summary.map((item) => (
                <button
                  key={item.product_id}
                  type="button"
                  onClick={() => setProductFilter(String(item.product_id))}
                  className="mb-2 flex w-full items-center justify-between gap-2 rounded-xl border border-white/5 px-3 py-2 text-left transition hover:bg-white/5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm text-slate-200">{item.product_name}</p>
                    <p className="text-[11px] text-slate-500">
                      {item.delivery_type} · {number(item.sold)} sold
                    </p>
                  </div>
                  <Badge tone={item.available === 0 ? "red" : item.low_stock ? "amber" : "green"}>
                    {number(item.available)}
                  </Badge>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card className="lg:col-span-2" bodyClassName="p-0">
          <div className="flex flex-wrap items-center gap-2 border-b border-white/5 px-4 py-3">
            <Select value={productFilter} onChange={(e) => { setProductFilter(e.target.value); setPage(1); }} className="w-52">
              <option value="">All products</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>{product.name_en}</option>
              ))}
            </Select>
            <Select value={usedFilter} onChange={(e) => { setUsedFilter(e.target.value); setPage(1); }} className="w-36">
              <option value="">All items</option>
              <option value="false">Available</option>
              <option value="true">Used</option>
            </Select>
            <SearchField value={search} onChange={(value) => { setSearch(value); setPage(1); }} placeholder="Search content…" className="w-52" />
            {productFilter && (
              <Button size="sm" variant="primary" onClick={() => openImport(Number(productFilter))}>
                <Plus className="h-3.5 w-3.5" /> Add
              </Button>
            )}
          </div>

          {itemsApi.loading ? (
            <Loading />
          ) : items.length === 0 ? (
            <div className="p-4"><EmptyState title="No stock items" description="Import lines to make this product deliverable." /></div>
          ) : (
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Content</th>
                    <th>Label</th>
                    <th>Status</th>
                    <th>Order</th>
                    <th>Created</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td className="max-w-[280px] truncate font-mono text-xs">{item.content}</td>
                      <td className="text-xs">{item.label || "—"}</td>
                      <td>
                        <Badge tone={item.is_used ? "gray" : "green"}>
                          {item.is_used ? "Used" : "Available"}
                        </Badge>
                      </td>
                      <td className="text-xs">{item.order_id ? `#${item.order_id}` : "—"}</td>
                      <td className="text-xs text-slate-500">{formatDate(item.created_at)}</td>
                      <td>
                        <div className="flex justify-end">
                          <button
                            type="button"
                            disabled={item.is_used}
                            onClick={() => void removeItem(item)}
                            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-rose-300 disabled:opacity-30"
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
          {itemsApi.data && (
            <div className="px-4 pb-4">
              <Pagination
                page={itemsApi.data.meta.page}
                totalPages={itemsApi.data.meta.total_pages}
                total={itemsApi.data.meta.total}
                onChange={setPage}
              />
            </div>
          )}
        </Card>
      </div>

      <Modal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title="Import stock"
        description="One deliverable per line. Duplicates are skipped automatically."
        footer={
          <>
            <Button onClick={() => setImportOpen(false)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void submitImport()}>
              Import
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Product">
            <Select value={importProduct} onChange={(e) => setImportProduct(e.target.value)}>
              <option value="">Choose product…</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>{product.name_en}</option>
              ))}
            </Select>
          </Field>
          <Field label="Label (optional)">
            <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="batch-january" />
          </Field>
          <Field label="Lines">
            <Textarea
              value={importLines}
              onChange={(e) => setImportLines(e.target.value)}
              className="min-h-[220px] font-mono"
              placeholder={"user@example.com:password123\nuser2@example.com:password456"}
            />
          </Field>
        </div>
      </Modal>
    </>
  );
}
