"use client";

import { useAuth } from "@/lib/auth";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import MobileNav from "./MobileNav";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (!isLoading && !token && pathname !== "/login") {
      router.replace("/login");
    }
  }, [isLoading, token, pathname, router]);

  const isLoginPage = pathname === "/login" || pathname === "/login/";

  // Login page — no shell, render immediately (both SSR and client)
  if (isLoginPage) {
    return <>{children}</>;
  }

  // SSR or not yet mounted — show nothing (avoids hydration mismatch)
  if (!mounted || isLoading) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: "#f5f7fa" }}>
        <div className="w-8 h-8 rounded-full animate-spin" style={{ border: "2px solid #3b82f6", borderTopColor: "transparent" }} />
      </div>
    );
  }

  // Not authenticated
  if (!token) return null;

  return (
    <div className="min-h-screen bg-bg-root">
      <Sidebar />
      <MobileNav />
      <main className="lg:ml-[240px] min-h-screen">
        <div className="p-4 sm:p-6 lg:p-8 max-w-[1400px] mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
