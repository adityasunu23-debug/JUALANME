"use client";

import { ArrowRight, Lock, ShieldCheck, Store } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button, Field, Input } from "@/components/ui";
import { useToast } from "@/components/toast";
import { getToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type TelegramUser = {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
};

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramUser) => void;
  }
}

const BOT_USERNAME = process.env.NEXT_PUBLIC_BOT_USERNAME || "";

export default function LoginPage() {
  const router = useRouter();
  const toast = useToast();
  const { loginDev, loginTelegram } = useAuth();
  const widgetRef = useRef<HTMLDivElement>(null);
  const [telegramId, setTelegramId] = useState("123456789");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (getToken()) router.replace("/dashboard");
  }, [router]);

  useEffect(() => {
    if (!BOT_USERNAME || !widgetRef.current) return;
    window.onTelegramAuth = async (user: TelegramUser) => {
      setBusy(true);
      setError(null);
      try {
        await loginTelegram(user);
        toast.success("Signed in with Telegram");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Telegram login failed");
      } finally {
        setBusy(false);
      }
    };
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", BOT_USERNAME);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "10");
    script.setAttribute("data-onauth", "onTelegramAuth(user)");
    script.setAttribute("data-request-access", "write");
    widgetRef.current.innerHTML = "";
    widgetRef.current.appendChild(script);
    return () => {
      delete window.onTelegramAuth;
    };
  }, [loginTelegram, toast]);

  async function handleDevLogin(event: React.FormEvent) {
    event.preventDefault();
    const id = Number(telegramId);
    if (!Number.isFinite(id) || id <= 0) {
      setError("Enter a valid Telegram ID");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await loginDev(id);
      toast.success("Development login successful");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <div className="pointer-events-none absolute -left-40 top-0 h-96 w-96 rounded-full bg-brand-500/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-sky-500/10 blur-3xl" />

      <div className="relative grid w-full max-w-4xl gap-8 lg:grid-cols-2">
        <div className="hidden flex-col justify-between rounded-3xl border border-white/5 bg-ink-900/60 p-8 lg:flex">
          <div className="flex items-center gap-3">
            <span className="rounded-2xl bg-brand-500 p-2.5 text-ink-950">
              <Store className="h-5 w-5" />
            </span>
            <div>
              <p className="text-sm font-semibold text-white">Telegram Store</p>
              <p className="text-xs text-slate-500">USDT · BEP20 · Instant delivery</p>
            </div>
          </div>

          <div className="space-y-5">
            <h1 className="text-3xl font-semibold leading-tight text-white">
              Run your crypto store with confidence.
            </h1>
            <p className="text-sm leading-relaxed text-slate-400">
              Track revenue, fulfil orders, manage stock and talk to customers from a
              single dark-mode control room.
            </p>
            <ul className="space-y-3 text-sm text-slate-300">
              <li className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-brand-400" /> Automatic payment
                verification and delivery
              </li>
              <li className="flex items-center gap-2">
                <Lock className="h-4 w-4 text-brand-400" /> Role based access, audit
                trail and backups
              </li>
              <li className="flex items-center gap-2">
                <ArrowRight className="h-4 w-4 text-brand-400" /> Bilingual customer bot
                (Indonesian / English)
              </li>
            </ul>
          </div>

          <p className="text-xs text-slate-600">
            Authorised staff only. Sessions are signed with your server secret.
          </p>
        </div>

        <div className="panel p-6 sm:p-8">
          <div className="mb-6">
            <p className="text-xs font-medium uppercase tracking-wider text-brand-400">
              Admin access
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-white">Sign in</h2>
            <p className="mt-1 text-sm text-slate-400">
              Use the Telegram Login Widget or a development account.
            </p>
          </div>

          <div className="mb-6 space-y-3">
            {BOT_USERNAME ? (
              <div ref={widgetRef} className="min-h-[44px]" />
            ) : (
              <p className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-300">
                Set NEXT_PUBLIC_BOT_USERNAME to enable the Telegram Login Widget.
              </p>
            )}
          </div>

          <div className="mb-6 flex items-center gap-3 text-xs text-slate-600">
            <span className="h-px flex-1 bg-white/5" />
            or development login
            <span className="h-px flex-1 bg-white/5" />
          </div>

          <form onSubmit={handleDevLogin} className="space-y-3">
            <Field label="Telegram ID" hint="Must belong to a seeded admin account.">
              <Input
                value={telegramId}
                onChange={(event) => setTelegramId(event.target.value)}
                inputMode="numeric"
                placeholder="123456789"
              />
            </Field>
            <Button type="submit" variant="primary" loading={busy} className="w-full">
              Continue
            </Button>
          </form>

          {error && (
            <p className="mt-4 rounded-xl border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-xs text-rose-300">
              {error}
            </p>
          )}

          <p className="mt-6 text-center text-[11px] text-slate-600">
            Development login is disabled in production by the backend.
          </p>
        </div>
      </div>
    </main>
  );
}
