"use client";

import { useMemo, useState } from "react";

import {
  Card,
  EmptyState,
  Input,
  Loading,
  PageHeader,
  Pagination,
  Select,
  StatusBadge,
} from "@/components/ui";
import { useApi } from "@/lib/use-api";
import { formatDate, humanize, money, queryString } from "@/lib/utils";

type Transaction = {
  id: number;
  order_code: string;
  customer_name?: string | null;
  product_name: string;
  amount: number;
  currency: string;
  status: string;
  delivery_status: string;
  provider?: string | null;
  tx_hash?: string | null;
  network?: string | null;
  created_at?: string | null;
  paid_at?: string | null;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

export default function TransactionsPage() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const path = useMemo(
    () => `/transactions${queryString({ search, status, page, page_size: 20 })}`,
    [search, status, page]
  );
  const { data, loading, error } = useApi<Page<Transaction>>(path);
  const transactions = data?.items ?? [];

  const paidTotal = transactions
    .filter((item) => ["PAID", "DELIVERED", "COMPLETED"].includes(item.status))
    .reduce((sum, item) => sum + Number(item.amount), 0);

  return (
    <>
      <PageHeader
        title="Transactions"
        description="Payment-linked ledger of every order."
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="w-48">
          <option value="">All statuses</option>
          {["PENDING_PAYMENT", "PAID", "DELIVERED", "COMPLETED", "EXPIRED", "CANCELLED", "FAILED", "REFUNDED"].map((value) => (
            <option key={value} value={value}>{humanize(value)}</option>
          ))}
        </Select>
        <Input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search order, customer, tx hash…"
          className="max-w-md"
        />
      </div>

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading transactions…" />
        ) : error ? (
          <p className="p-5 text-sm text-rose-300">{error}</p>
        ) : transactions.length === 0 ? (
          <div className="p-5"><EmptyState title="No transactions" /></div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Customer</th>
                  <th>Product</th>
                  <th>Amount</th>
                  <th>Payment</th>
                  <th>Delivery</th>
                  <th>Network / tx</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td className="font-mono text-xs text-brand-300">{transaction.order_code}</td>
                    <td>{transaction.customer_name || "—"}</td>
                    <td className="max-w-[220px] truncate">{transaction.product_name}</td>
                    <td>{money(transaction.amount, transaction.currency)}</td>
                    <td><StatusBadge status={transaction.status} /></td>
                    <td><StatusBadge status={transaction.delivery_status} /></td>
                    <td>
                      <p className="text-xs uppercase">{transaction.network || "—"}</p>
                      {transaction.tx_hash && (
                        <p className="max-w-[160px] truncate font-mono text-[10px] text-slate-500">{transaction.tx_hash}</p>
                      )}
                    </td>
                    <td className="text-xs text-slate-500">{formatDate(transaction.paid_at || transaction.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && (
          <div className="flex flex-wrap items-center justify-between gap-2 px-4 pb-4">
            <span className="text-xs text-slate-500">Page total paid: {money(paidTotal)}</span>
            <Pagination page={data.meta.page} totalPages={data.meta.total_pages} total={data.meta.total} onChange={setPage} />
          </div>
        )}
      </Card>
    </>
  );
}
