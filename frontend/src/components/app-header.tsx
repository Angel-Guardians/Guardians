"use client";

import { ProfileCorner } from "@/components/profile-corner";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center justify-end border-b border-border/80 bg-background/85 px-6 backdrop-blur-md supports-[backdrop-filter]:bg-background/70 md:px-10">
      <ProfileCorner />
    </header>
  );
}
