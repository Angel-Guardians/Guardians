import Link from "next/link";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const SECTIONS = [
  {
    href: "/profile",
    title: "Profile",
    description: "Patient info, emergency contacts, and medications.",
  },
  {
    href: "/live",
    title: "Live",
    description: "See what Guardian is hearing and doing right now.",
  },
  {
    href: "/vitals",
    title: "Vitals",
    description: "Heart rate, blood pressure, and SpO2 trends.",
  },
  {
    href: "/reminders",
    title: "Reminders",
    description: "Today's medications and check-ins.",
  },
] as const;

export default function OverviewPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Guardian</h1>
        <p className="text-muted-foreground">
          Home Emergency AI Companion - always-on, fully local. Use the sidebar to navigate.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SECTIONS.map((section) => (
          <Link key={section.href} href={section.href} className="group">
            <Card className="h-full transition-colors group-hover:border-foreground/30">
              <CardHeader>
                <CardTitle>{section.title}</CardTitle>
                <CardDescription>{section.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
