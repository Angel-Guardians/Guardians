"use client";

import { Settings, Shield } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ProfileCorner } from "@/components/profile-corner";
import { cn } from "@/lib/utils";

export function AppHeader() {
  const pathname = usePathname();
  const onHome = pathname === "/";
  const onAdmin = pathname.startsWith("/admin");

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/90 backdrop-blur-md supports-[backdrop-filter]:bg-background/75">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-6 md:px-10">
        <div className="flex items-center gap-2">
          <Link
            href="/admin"
            aria-label="Admin settings"
            aria-current={onAdmin ? "page" : undefined}
            className={cn(
              "flex size-9 items-center justify-center rounded-xl border border-border/80 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
              onAdmin && "border-primary/30 bg-primary/5 text-primary",
            )}
          >
            <Settings className="size-4.5" strokeWidth={2} />
          </Link>
          <Link
            href="/"
            className={cn(
              "group flex items-center gap-2.5 rounded-lg transition-opacity hover:opacity-90",
              onHome && "pointer-events-none",
            )}
          >
            <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Shield className="size-4.5" strokeWidth={2.25} />
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-semibold leading-tight tracking-tight">Guardian</p>
              <p className="text-xs text-muted-foreground">Home Emergency Companion</p>
            </div>
          </Link>
        </div>
        <ProfileCorner />
      </div>
    </header>
  );
}
