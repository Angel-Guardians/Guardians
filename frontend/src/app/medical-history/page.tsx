import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { MedicalHistoryUpload } from "@/components/medical-history/medical-history-upload";

export default function MedicalHistoryPage() {
  return (
    <div className="space-y-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Dashboard
      </Link>
      <MedicalHistoryUpload />
    </div>
  );
}
