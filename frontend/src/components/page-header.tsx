import { ArrowLeft } from "lucide-react";
import Link from "next/link";

interface PageHeaderProps {
  title: string;
  description?: string;
  backHref?: string;
  backLabel?: string;
  action?: React.ReactNode;
}

export function PageHeader({
  title,
  description,
  backHref = "/",
  backLabel = "Dashboard",
  action,
}: PageHeaderProps) {
  return (
    <header className="space-y-4">
      <Link
        href={backHref}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        {backLabel}
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {description ? (
            <p className="max-w-2xl text-muted-foreground">{description}</p>
          ) : null}
        </div>
        {action}
      </div>
    </header>
  );
}
