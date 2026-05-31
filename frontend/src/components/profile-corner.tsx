"use client";

import { UserRound } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import {
  ACTIVE_PATIENT_CHANGED_EVENT,
  EMPTY_PATIENT_PROFILE,
  PROFILE_UPDATED_EVENT,
  profileInitials,
} from "@/lib/profile-storage";
import type { PatientProfile } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ProfileCorner() {
  const pathname = usePathname();
  const active = pathname.startsWith("/profile");
  const [profile, setProfile] = useState<PatientProfile>(EMPTY_PATIENT_PROFILE);

  const refresh = useCallback(async () => {
    try {
      const loaded = await api.getPatientProfile();
      setProfile(loaded);
    } catch {
      // Keep last known profile; header stays usable offline.
    }
  }, []);

  useEffect(() => {
    void refresh();
    const onUpdated = (event: Event) => {
      const detail = (event as CustomEvent<PatientProfile>).detail;
      if (detail) setProfile(detail);
      else void refresh();
    };
    window.addEventListener(PROFILE_UPDATED_EVENT, onUpdated);
    window.addEventListener(ACTIVE_PATIENT_CHANGED_EVENT, refresh);
    return () => {
      window.removeEventListener(PROFILE_UPDATED_EVENT, onUpdated);
      window.removeEventListener(ACTIVE_PATIENT_CHANGED_EVENT, refresh);
    };
  }, [refresh]);

  const initials = profileInitials(profile.name);
  const label = profile.name.trim() || "Patient";

  return (
    <Link
      href="/profile"
      aria-current={active ? "page" : undefined}
      className={cn(
        "group flex items-center gap-3 rounded-full border border-border/80 bg-card py-1.5 pr-3 pl-1.5 shadow-sm transition-all hover:border-foreground/20 hover:shadow-md focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
        active && "border-primary/30 bg-primary/5 ring-1 ring-primary/20",
      )}
    >
      <div className="relative shrink-0">
        <div
          className={cn(
            "absolute -inset-0.5 rounded-full bg-gradient-to-br from-sky-400/80 via-indigo-400/70 to-violet-500/80 opacity-90 transition-opacity group-hover:opacity-100",
            active && "from-sky-500 via-indigo-500 to-violet-600",
          )}
          aria-hidden
        />
        <div
          className={cn(
            "relative flex size-10 items-center justify-center rounded-full bg-gradient-to-br from-slate-800 to-slate-950 text-sm font-semibold text-white shadow-inner dark:from-slate-700 dark:to-slate-900",
            active && "from-indigo-700 to-slate-950",
          )}
        >
          {initials ? (
            initials
          ) : (
            <UserRound className="size-5 text-white/90" strokeWidth={1.75} />
          )}
        </div>
        <span
          className="absolute -right-0.5 -bottom-0.5 size-3 rounded-full border-2 border-card bg-emerald-500 shadow-sm"
          aria-hidden
          title="Profile active"
        />
      </div>

      <div className="hidden min-w-0 text-left sm:block">
        <p className="truncate text-sm font-medium leading-tight text-foreground">
          {label}
        </p>
        <p className="text-xs text-muted-foreground transition-colors group-hover:text-foreground/70">
          {active ? "Viewing profile" : "Patient profile"}
        </p>
      </div>
    </Link>
  );
}
