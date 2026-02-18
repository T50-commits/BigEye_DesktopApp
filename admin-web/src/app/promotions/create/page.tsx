"use client";

import { useRouter } from "next/navigation";
import { createPromo } from "@/lib/api";
import PromoForm, { type PromoFormData } from "@/components/shared/PromoForm";

export default function CreatePromoPage() {
  const router = useRouter();

  const handleCreate = async (data: PromoFormData) => {
    await createPromo(data as unknown as Record<string, unknown>);
    router.push("/promotions");
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <a href="/promotions" className="text-xs text-txt-muted hover:text-txt-secondary">&larr; กลับ</a>
        <h1 className="text-xl font-bold text-txt-primary">สร้างโปรโมชั่นใหม่</h1>
      </div>
      <PromoForm onSubmit={handleCreate} submitLabel="สร้างโปรโมชั่น" />
    </div>
  );
}
