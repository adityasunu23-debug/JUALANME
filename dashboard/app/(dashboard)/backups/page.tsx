"use client";

import { Database, Download, Plus } from "lucide-react";
import { useState } from "react";

import { useToast } from "@/components/toast";
import {
  Button,
  Card,
  EmptyState,
  Loading,
  PageHeader,
  StatCard,
} from "@/components/ui";
import { api, downloadFile } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { formatDate, number } from "@/lib/utils";

type Backup = {
  filename: string;
  path: string;
  size_bytes: number;
  created_at: string;
  tables: number;
  rows: number;
};

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function BackupsPage() {
  const toast = useToast();
  const { data, loading, error, reload } = useApi<Backup[]>("/backups");
  const [creating, setCreating] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const backups = data ?? [];

  async function create() {
    setCreating(true);
    try {
      await api("/backups", { method: "POST" });
      toast.success("Backup created");
      reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Backup failed");
    } finally {
      setCreating(false);
    }
  }

  async function download(backup: Backup) {
    setDownloading(backup.filename);
    try {
      await downloadFile(`/backups/${encodeURIComponent(backup.filename)}`, backup.filename);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(null);
    }
  }

  const totalSize = backups.reduce((sum, backup) => sum + backup.size_bytes, 0);

  return (
    <>
      <PageHeader
        title="Backups"
        description="JSON snapshots of every table, downloadable for off-site storage."
        actions={
          <Button variant="primary" loading={creating} onClick={() => void create()}>
            <Plus className="h-4 w-4" /> Create backup
          </Button>
        }
      />

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatCard label="Snapshots" value={number(backups.length)} icon={<Database className="h-4 w-4" />} />
        <StatCard label="Total size" value={humanSize(totalSize)} tone="sky" icon={<Database className="h-4 w-4" />} />
        <StatCard
          label="Latest"
          value={backups[0] ? formatDate(backups[0].created_at, false) : "—"}
          tone="violet"
          icon={<Database className="h-4 w-4" />}
        />
      </div>

      <Card bodyClassName="p-0">
        {loading ? (
          <Loading label="Loading backups…" />
        ) : error ? (
          <p className="p-5 text-sm text-rose-300">{error}</p>
        ) : backups.length === 0 ? (
          <div className="p-5">
            <EmptyState
              title="No backups yet"
              description="Create a snapshot before deploys or database changes."
              action={<Button onClick={() => void create()}>Create backup</Button>}
            />
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Created</th>
                  <th>Tables</th>
                  <th>Rows</th>
                  <th>Size</th>
                  <th className="text-right">Download</th>
                </tr>
              </thead>
              <tbody>
                {backups.map((backup) => (
                  <tr key={backup.filename}>
                    <td className="font-mono text-xs">{backup.filename}</td>
                    <td className="text-xs text-slate-500">{formatDate(backup.created_at)}</td>
                    <td>{number(backup.tables)}</td>
                    <td>{number(backup.rows)}</td>
                    <td>{humanSize(backup.size_bytes)}</td>
                    <td>
                      <div className="flex justify-end">
                        <Button
                          size="sm"
                          loading={downloading === backup.filename}
                          onClick={() => void download(backup)}
                        >
                          <Download className="h-3.5 w-3.5" /> Download
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
