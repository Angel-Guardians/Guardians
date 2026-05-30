"use client";

import { Shield } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ProfileCorner } from "@/components/profile-corner";
import { cn } from "@/lib/utils";

export function AppHeader() {
  const pathname = usePathname();
  const onHome = pathname === "/";

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/90 backdrop-blur-md supports-[backdrop-filter]:bg-background/75">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-6 md:px-10">
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
        <ProfileCorner />
      </div>
    </header>
  );
}
