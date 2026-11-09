"use client";

import { Boxes, Pencil, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
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
  Tabs,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { humanize, money, number, queryString } from "@/lib/utils";

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
};

type Product = {
  id: number;
  category_id?: number | null;
  sku?: string | null;
  name_id: string;
  name_en: string;
  description_id?: string | null;
  description_en?: string | null;
  price: number;
  compare_price?: number | null;
  currency: string;
  delivery_type: "AUTO" | "MANUAL";
  image_url?: string | null;
  min_quantity: number;
  max_quantity: number;
  is_active: boolean;
  is_featured: boolean;
  sort_order: number;
  sold_count: number;
  stock_available: number;
  stock_sold: number;
  category_name?: string | null;
  delivery_instructions?: string | null;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

const emptyProduct = {
  category_id: "",
  sku: "",
  name_id: "",
  name_en: "",
  description_id: "",
  description_en: "",
  price: "",
  compare_price: "",
  delivery_type: "AUTO",
  image_url: "",
  min_quantity: "1",
  max_quantity: "100",
  is_active: true,
  is_featured: false,
  sort_order: "0",
  delivery_instructions: "",
  stock: "",
};

const emptyCategory = {
  slug: "",
  name_id: "",
  name_en: "",
  description_id: "",
  description_en: "",
  icon: "📦",
  sort_order: "0",
  is_active: true,
};

export default function CatalogPage() {
  const toast = useToast();
  const [tab, setTab] = useState<"products" | "categories">("products");
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [page, setPage] = useState(1);
  const [productForm, setProductForm] = useState<typeof emptyProduct & { id?: number } | null>(null);
  const [categoryForm, setCategoryForm] = useState<typeof emptyCategory & { id?: number } | null>(null);
  const [saving, setSaving] = useState(false);

  const categoriesApi = useApi<Category[]>("/categories");
  const categories = categoriesApi.data ?? [];
  const productsPath = useMemo(
    () =>
      `/products${queryString({
        search,
        category_id: categoryFilter,
        page,
        page_size: 20,
      })}`,
    [search, categoryFilter, page]
  );
  const productsApi = useApi<Page<Product>>(productsPath);
  const products = productsApi.data?.items ?? [];

  function openNewProduct() {
    setProductForm({ ...emptyProduct, category_id: categoryFilter || "" });
  }

  function openEditProduct(product: Product) {
    setProductForm({
      id: product.id,
      category_id: product.category_id ? String(product.category_id) : "",
      sku: product.sku || "",
      name_id: product.name_id,
      name_en: product.name_en,
      description_id: product.description_id || "",
      description_en: product.description_en || "",
      price: String(product.price),
      compare_price: product.compare_price ? String(product.compare_price) : "",
      delivery_type: product.delivery_type,
      image_url: product.image_url || "",
      min_quantity: String(product.min_quantity),
      max_quantity: String(product.max_quantity),
      is_active: product.is_active,
      is_featured: product.is_featured,
      sort_order: String(product.sort_order),
      delivery_instructions: product.delivery_instructions || "",
      stock: "",
    });
  }

  async function saveProduct() {
    if (!productForm) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {
        category_id: productForm.category_id ? Number(productForm.category_id) : null,
        sku: productForm.sku || null,
        name_id: productForm.name_id,
        name_en: productForm.name_en,
        description_id: productForm.description_id || null,
        description_en: productForm.description_en || null,
        price: Number(productForm.price),
        compare_price: productForm.compare_price ? Number(productForm.compare_price) : null,
        currency: "USDT",
        delivery_type: productForm.delivery_type,
        image_url: productForm.image_url || null,
        min_quantity: Number(productForm.min_quantity),
        max_quantity: Number(productForm.max_quantity),
        is_active: productForm.is_active,
        is_featured: productForm.is_featured,
        sort_order: Number(productForm.sort_order),
        delivery_instructions: productForm.delivery_instructions || null,
      };
      if (productForm.id) {
        await api(`/products/${productForm.id}`, { method: "PATCH", body: payload });
        toast.success("Product updated");
      } else {
        payload.stock = productForm.stock
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean);
        await api("/products", { method: "POST", body: payload });
        toast.success("Product created");
      }
      setProductForm(null);
      productsApi.reload();
      categoriesApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save product");
    } finally {
      setSaving(false);
    }
  }

  async function removeProduct(product: Product) {
    if (!window.confirm(`Delete “${product.name_en}”? This cannot be undone.`)) return;
    try {
      await api(`/products/${product.id}`, { method: "DELETE" });
      toast.success("Product deleted");
      productsApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  async function saveCategory() {
    if (!categoryForm) return;
    setSaving(true);
    try {
      const payload = {
        slug: categoryForm.slug,
        name_id: categoryForm.name_id,
        name_en: categoryForm.name_en,
        description_id: categoryForm.description_id || null,
        description_en: categoryForm.description_en || null,
        icon: categoryForm.icon || "📦",
        sort_order: Number(categoryForm.sort_order),
        is_active: categoryForm.is_active,
      };
      if (categoryForm.id) {
        await api(`/categories/${categoryForm.id}`, { method: "PATCH", body: payload });
        toast.success("Category updated");
      } else {
        await api("/categories", { method: "POST", body: payload });
        toast.success("Category created");
      }
      setCategoryForm(null);
      categoriesApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save category");
    } finally {
      setSaving(false);
    }
  }

  async function removeCategory(category: Category) {
    if (!window.confirm(`Delete category “${category.name_en}”?`)) return;
    try {
      await api(`/categories/${category.id}`, { method: "DELETE" });
      toast.success("Category deleted");
      categoriesApi.reload();
      productsApi.reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  return (
    <>
      <PageHeader
        title="Catalogue"
        description="Products, pricing and categories shown in the Telegram bot."
        actions={
          <Button
            variant="primary"
            onClick={() => (tab === "products" ? openNewProduct() : setCategoryForm({ ...emptyCategory }))}
          >
            <Plus className="h-4 w-4" />
            {tab === "products" ? "New product" : "New category"}
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Tabs
          tabs={[
            { value: "products", label: "Products", count: productsApi.data?.meta.total },
            { value: "categories", label: "Categories", count: categories.length },
          ]}
          value={tab}
          onChange={setTab}
        />
        {tab === "products" && (
          <div className="flex flex-wrap gap-2">
            <SearchField value={search} onChange={(value) => { setSearch(value); setPage(1); }} placeholder="Search products…" />
            <Select
              value={categoryFilter}
              onChange={(event) => { setCategoryFilter(event.target.value); setPage(1); }}
              className="w-48"
            >
              <option value="">All categories</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name_en}
                </option>
              ))}
            </Select>
          </div>
        )}
      </div>

      {tab === "products" ? (
        <Card bodyClassName="p-0">
          {productsApi.loading ? (
            <Loading label="Loading products…" />
          ) : productsApi.error ? (
            <p className="p-5 text-sm text-rose-300">{productsApi.error}</p>
          ) : products.length === 0 ? (
            <div className="p-5">
              <EmptyState
                title="No products found"
                description="Create your first product to start selling in the bot."
                action={<Button variant="primary" onClick={openNewProduct}>Create product</Button>}
              />
            </div>
          ) : (
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Category</th>
                    <th>Price</th>
                    <th>Delivery</th>
                    <th>Stock</th>
                    <th>Sold</th>
                    <th>Status</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((product) => (
                    <tr key={product.id}>
                      <td>
                        <p className="font-medium text-slate-100">{product.name_en}</p>
                        <p className="text-xs text-slate-500">{product.name_id}{product.sku ? ` · ${product.sku}` : ""}</p>
                      </td>
                      <td className="text-xs">{product.category_name || "—"}</td>
                      <td>{money(product.price, product.currency)}</td>
                      <td>
                        <Badge tone={product.delivery_type === "AUTO" ? "blue" : "violet"}>
                          {humanize(product.delivery_type)}
                        </Badge>
                      </td>
                      <td>
                        <span className={product.delivery_type === "AUTO" && product.stock_available <= 0 ? "text-rose-300" : ""}>
                          {number(product.stock_available)}
                        </span>
                      </td>
                      <td>{number(product.sold_count)}</td>
                      <td>
                        <Badge tone={product.is_active ? "green" : "gray"}>
                          {product.is_active ? "Active" : "Hidden"}
                        </Badge>
                      </td>
                      <td>
                        <div className="flex justify-end gap-1">
                          <Link
                            href={`/stock?product=${product.id}`}
                            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-brand-300"
                            title="Manage stock"
                          >
                            <Boxes className="h-4 w-4" />
                          </Link>
                          <button
                            type="button"
                            onClick={() => openEditProduct(product)}
                            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-sky-300"
                            title="Edit"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => void removeProduct(product)}
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
          {productsApi.data && (
            <div className="px-4 pb-4">
              <Pagination
                page={productsApi.data.meta.page}
                totalPages={productsApi.data.meta.total_pages}
                total={productsApi.data.meta.total}
                onChange={setPage}
              />
            </div>
          )}
        </Card>
      ) : (
        <Card bodyClassName="p-0">
          {categoriesApi.loading ? (
            <Loading label="Loading categories…" />
          ) : categories.length === 0 ? (
            <div className="p-5">
              <EmptyState
                title="No categories"
                description="Group products into categories for easier browsing."
                action={<Button onClick={() => setCategoryForm({ ...emptyCategory })}>Create category</Button>}
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
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((category) => (
                    <tr key={category.id}>
                      <td>
                        <p className="font-medium text-slate-100">
                          {category.icon} {category.name_en}
                        </p>
                        <p className="text-xs text-slate-500">{category.name_id}</p>
                      </td>
                      <td className="font-mono text-xs">{category.slug}</td>
                      <td>{number(category.product_count)}</td>
                      <td>{category.sort_order}</td>
                      <td>
                        <Badge tone={category.is_active ? "green" : "gray"}>
                          {category.is_active ? "Active" : "Hidden"}
                        </Badge>
                      </td>
                      <td>
                        <div className="flex justify-end gap-1">
                          <button
                            type="button"
                            onClick={() =>
                              setCategoryForm({
                                id: category.id,
                                slug: category.slug,
                                name_id: category.name_id,
                                name_en: category.name_en,
                                description_id: category.description_id || "",
                                description_en: category.description_en || "",
                                icon: category.icon,
                                sort_order: String(category.sort_order),
                                is_active: category.is_active,
                              })
                            }
                            className="rounded-lg p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-sky-300"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => void removeCategory(category)}
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
        </Card>
      )}

      <Modal
        open={Boolean(productForm)}
        onClose={() => setProductForm(null)}
        title={productForm?.id ? "Edit product" : "New product"}
        size="lg"
        footer={
          <>
            <Button onClick={() => setProductForm(null)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void saveProduct()}>
              {productForm?.id ? "Save changes" : "Create product"}
            </Button>
          </>
        }
      >
        {productForm && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name (ID)">
              <Input value={productForm.name_id} onChange={(e) => setProductForm({ ...productForm, name_id: e.target.value })} />
            </Field>
            <Field label="Name (EN)">
              <Input value={productForm.name_en} onChange={(e) => setProductForm({ ...productForm, name_en: e.target.value })} />
            </Field>
            <Field label="Category">
              <Select value={productForm.category_id} onChange={(e) => setProductForm({ ...productForm, category_id: e.target.value })}>
                <option value="">Uncategorised</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name_en}</option>
                ))}
              </Select>
            </Field>
            <Field label="SKU">
              <Input value={productForm.sku} onChange={(e) => setProductForm({ ...productForm, sku: e.target.value })} />
            </Field>
            <Field label="Price (USDT)">
              <Input type="number" step="0.01" value={productForm.price} onChange={(e) => setProductForm({ ...productForm, price: e.target.value })} />
            </Field>
            <Field label="Compare price">
              <Input type="number" step="0.01" value={productForm.compare_price} onChange={(e) => setProductForm({ ...productForm, compare_price: e.target.value })} />
            </Field>
            <Field label="Delivery type">
              <Select value={productForm.delivery_type} onChange={(e) => setProductForm({ ...productForm, delivery_type: e.target.value })}>
                <option value="AUTO">AUTO · instant from stock</option>
                <option value="MANUAL">MANUAL · admin delivers</option>
              </Select>
            </Field>
            <Field label="Image URL">
              <Input value={productForm.image_url} onChange={(e) => setProductForm({ ...productForm, image_url: e.target.value })} />
            </Field>
            <Field label="Min quantity">
              <Input type="number" min="1" value={productForm.min_quantity} onChange={(e) => setProductForm({ ...productForm, min_quantity: e.target.value })} />
            </Field>
            <Field label="Max quantity">
              <Input type="number" min="1" value={productForm.max_quantity} onChange={(e) => setProductForm({ ...productForm, max_quantity: e.target.value })} />
            </Field>
            <Field label="Description (ID)" className="sm:col-span-2">
              <Textarea value={productForm.description_id} onChange={(e) => setProductForm({ ...productForm, description_id: e.target.value })} />
            </Field>
            <Field label="Description (EN)" className="sm:col-span-2">
              <Textarea value={productForm.description_en} onChange={(e) => setProductForm({ ...productForm, description_en: e.target.value })} />
            </Field>
            <Field label="Delivery instructions" className="sm:col-span-2">
              <Textarea value={productForm.delivery_instructions} onChange={(e) => setProductForm({ ...productForm, delivery_instructions: e.target.value })} />
            </Field>
            {!productForm.id && (
              <Field label="Initial stock (one item per line)" className="sm:col-span-2">
                <Textarea value={productForm.stock} onChange={(e) => setProductForm({ ...productForm, stock: e.target.value })} placeholder={"account@example.com:password\ncode-2"} />
              </Field>
            )}
            <Field label="Sort order">
              <Input type="number" value={productForm.sort_order} onChange={(e) => setProductForm({ ...productForm, sort_order: e.target.value })} />
            </Field>
            <div className="flex items-end gap-4">
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input type="checkbox" checked={productForm.is_active} onChange={(e) => setProductForm({ ...productForm, is_active: e.target.checked })} />
                Active
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input type="checkbox" checked={productForm.is_featured} onChange={(e) => setProductForm({ ...productForm, is_featured: e.target.checked })} />
                Featured
              </label>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        open={Boolean(categoryForm)}
        onClose={() => setCategoryForm(null)}
        title={categoryForm?.id ? "Edit category" : "New category"}
        footer={
          <>
            <Button onClick={() => setCategoryForm(null)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={() => void saveCategory()}>
              {categoryForm?.id ? "Save changes" : "Create category"}
            </Button>
          </>
        }
      >
        {categoryForm && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Name (ID)">
              <Input value={categoryForm.name_id} onChange={(e) => setCategoryForm({ ...categoryForm, name_id: e.target.value })} />
            </Field>
            <Field label="Name (EN)">
              <Input value={categoryForm.name_en} onChange={(e) => setCategoryForm({ ...categoryForm, name_en: e.target.value })} />
            </Field>
            <Field label="Slug" hint="Unique, lowercase, dashes.">
              <Input value={categoryForm.slug} onChange={(e) => setCategoryForm({ ...categoryForm, slug: e.target.value })} />
            </Field>
            <Field label="Icon">
              <Input value={categoryForm.icon} onChange={(e) => setCategoryForm({ ...categoryForm, icon: e.target.value })} />
            </Field>
            <Field label="Description (ID)" className="sm:col-span-2">
              <Textarea value={categoryForm.description_id} onChange={(e) => setCategoryForm({ ...categoryForm, description_id: e.target.value })} />
            </Field>
            <Field label="Description (EN)" className="sm:col-span-2">
              <Textarea value={categoryForm.description_en} onChange={(e) => setCategoryForm({ ...categoryForm, description_en: e.target.value })} />
            </Field>
            <Field label="Sort order">
              <Input type="number" value={categoryForm.sort_order} onChange={(e) => setCategoryForm({ ...categoryForm, sort_order: e.target.value })} />
            </Field>
            <label className="flex items-end gap-2 pb-2 text-sm text-slate-300">
              <input type="checkbox" checked={categoryForm.is_active} onChange={(e) => setCategoryForm({ ...categoryForm, is_active: e.target.checked })} />
              Active
            </label>
          </div>
        )}
      </Modal>
    </>
  );
}
