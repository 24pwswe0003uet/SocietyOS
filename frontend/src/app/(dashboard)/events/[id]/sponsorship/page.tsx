"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getSponsorship, getExportUrl } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";

const TIER_COLORS: Record<string, string> = {
  Gold: "border-amber-400 bg-amber-50",
  Silver: "border-slate-400 bg-slate-50",
  Bronze: "border-orange-400 bg-orange-50",
};

interface Tier { name: string; amount: number; benefits: string[]; }
interface EmailDraft { industry: string; subject_a: string; subject_b: string; body: string; }

export default function SponsorshipPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const eventId = params.id as string;

  const [tiers, setTiers] = useState<Tier[]>([]);
  const [audience, setAudience] = useState("");
  const [emails, setEmails] = useState<EmailDraft[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSponsorship(eventId)
      .then((data: Record<string, unknown>) => {
        setTiers(data.tiers as Tier[] || []);
        setAudience(data.audience_summary as string || "");
        setEmails(data.email_drafts as EmailDraft[] || []);
      })
      .catch(() => toast("No sponsorship package found", "error"))
      .finally(() => setLoading(false));
  }, [eventId, toast]);

  if (loading) {
    return <div className="flex items-center justify-center py-20"><div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" /></div>;
  }

  return (
    <div className="animate-slide-up max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Sponsorship Package</h1>
          <p className="text-sm text-slate-500">{tiers.length} tiers &middot; {emails.length} email templates</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => window.open(getExportUrl(eventId, "sponsorship/pdf"))}>
            Export PDF
          </Button>
          <Button variant="ghost" onClick={() => router.push(`/events/${eventId}`)}>Back</Button>
        </div>
      </div>

      {/* Audience */}
      {audience && (
        <Card className="mb-4">
          <CardHeader><h2 className="font-semibold text-slate-900">Audience</h2></CardHeader>
          <CardBody><p className="text-sm text-slate-600">{audience}</p></CardBody>
        </Card>
      )}

      {/* Tiers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {tiers.map((tier, i) => (
          <Card key={i} className={`border-2 ${TIER_COLORS[tier.name] || "border-slate-200"}`}>
            <CardBody className="text-center">
              <h3 className="font-bold text-lg text-slate-900 mb-1">{tier.name}</h3>
              <p className="text-2xl font-bold text-indigo-600 mb-4">
                PKR {tier.amount?.toLocaleString() || "—"}
              </p>
              <ul className="text-left text-sm space-y-2">
                {tier.benefits?.map((b, j) => (
                  <li key={j} className="flex items-start gap-2">
                    <span className="text-emerald-500 mt-0.5 shrink-0">✓</span>
                    <span className="text-slate-600">{b}</span>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* Email Templates */}
      {emails.length > 0 && (
        <>
          <h2 className="text-lg font-semibold text-slate-900 mb-3">Outreach Email Templates</h2>
          <div className="space-y-4">
            {emails.map((email, i) => (
              <Card key={i}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900 capitalize">{email.industry} Industry</span>
                    <div className="text-xs text-slate-400">
                      A/B subjects
                    </div>
                  </div>
                </CardHeader>
                <CardBody className="space-y-2">
                  <div className="text-sm">
                    <span className="font-medium text-slate-600">Subject A: </span>
                    <span className="text-slate-800">{email.subject_a}</span>
                  </div>
                  <div className="text-sm">
                    <span className="font-medium text-slate-600">Subject B: </span>
                    <span className="text-slate-800">{email.subject_b}</span>
                  </div>
                  <div className="mt-3 bg-slate-50 rounded-md p-3 text-sm text-slate-700 whitespace-pre-wrap">
                    {email.body}
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
