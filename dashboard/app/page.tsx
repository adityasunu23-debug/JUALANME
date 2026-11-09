"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Spinner } from "@/components/ui";
import { getToken } from "@/lib/api";

export default function IndexPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(getToken() ? "/dashboard" : "/login");
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <Spinner className="h-8 w-8" />
    </main>
  );
}
