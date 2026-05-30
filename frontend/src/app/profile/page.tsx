import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { ProfileEditor } from "@/components/profile/profile-editor";

export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Dashboard
      </Link>
      <ProfileEditor />
    </div>
  );
}
