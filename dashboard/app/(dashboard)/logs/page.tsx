"use client";

import { useMemo, useState } from "react";

import {
  Badge,
  Card,
  EmptyState,
  Input,
  Loading,
  PageHeader,
  Pagination,
} from "@/components/ui";
import { useApi } from "@/lib/use-api";
import { formatDate, humanize, queryString } from "@/lib/utils";

type Log = {
  id: number;
  admin_id?: number | null;
  admin_name?: string | null;
  action: string;
  resource?: string | null;
  resource_id?: string | null;
  description?: string | null;
  ip_address?: string | null;
  status: string;
  created_at?: string | null;
};

type Page<T> = { items: T[]; meta: { total: number; page: number; page_size: number; total_pages: number } };

export default function LogsPage() {
  const [action, setAction] = useState("");
  const [adminId, setAdminId] = useState("");
  const [page, setPage] = useState(1);

  const path = useMemo(
    () => `/logs${queryString({ action, admin_id: adminId, page, page_size: 25 })}`,
    [action, adminId, page]
  );
  const { data, loading, error } = useApi<Page<Log>>(path);
  const logs = data?.items ?? [];

  return (
    <>
      <PageHeader title="Audit logs" description="Every privileged action recorded by the backend." />

      <div className="mb-4 flex flex-wrap gap-2">
        <Input
          value={action}
          onChange={(e) => { setAction(e.target.value); setPage(1); }}
          placeholder="Filter by action e.g. order.mark_paid"
          className="max-w-xs"
        />
        <Input
          value={adminId}
          onChange={(e) => { setAdminId(e.target.value); setPage(1); }}
          placeholder="Admin ID"
          inputMode="numeric"
          className="w-32"
        />
      </div>

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading audit trail…" />
        ) : error ? (
          <p className="p-5 text-sm text-rose-300">{error}</p>
        ) : logs.length === 0 ? (
          <div className="p-5"><EmptyState title="No log entries" /></div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Admin</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Description</th>
                  <th>IP</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="text-xs text-slate-500">{formatDate(log.created_at)}</td>
                    <td className="text-xs">{log.admin_name || (log.admin_id ? `#${log.admin_id}` : "System")}</td>
                    <td className="font-mono text-[11px] text-brand-300">{log.action}</td>
                    <td className="text-xs">
                      {log.resource || "—"}
                      {log.resource_id ? ` #${log.resource_id}` : ""}
                    </td>
                    <td className="max-w-[320px] truncate text-xs text-slate-400">{log.description || "—"}</td>
                    <td className="text-xs text-slate-500">{log.ip_address || "—"}</td>
                    <td><Badge tone={log.status === "SUCCESS" ? "green" : "red"}>{humanize(log.status)}</Badge></td>
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
    </>
  );
}
