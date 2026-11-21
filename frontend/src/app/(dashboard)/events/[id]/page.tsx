"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getEvent, generateAll, type GenerationUpdate } from "@/lib/api";
import type { EventRecord } from "@/types";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700",
  generating: "bg-amber-100 text-amber-700",
  review: "bg-blue-100 text-blue-700",
  submitted: "bg-indigo-100 text-indigo-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-red-100 text-red-700",
  completed: "bg-slate-100 text-slate-700",
};

function formatCurrency(amount: number | null, currency: string): string {
  if (amount === null) return "—";
  return `${currency} ${Number(amount).toLocaleString()}`;
}

export default function EventDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const [event, setEvent] = useState<EventRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [updates, setUpdates] = useState<GenerationUpdate[]>([]);

  useEffect(() => {
    if (!params.id) return;
    getEvent(params.id as string)
      .then(setEvent)
      .catch(() => toast("Failed to load event", "error"))
      .finally(() => setLoading(false));
  }, [params.id, toast]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!event) {
    return <p className="text-slate-500 py-10 text-center">Event not found.</p>;
  }

  return (
    <div className="animate-slide-up max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-slate-900">{event.title}</h1>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[event.status] || ""}`}>
              {event.status}
            </span>
          </div>
          <p className="text-slate-500 capitalize">{event.event_type}</p>
        </div>
        <div className="flex items-center gap-2">
          {(event.status === "review" || event.status === "submitted" || event.status === "approved") && (
            <Button onClick={() => router.push(`/events/${params.id}/manage`)}>
              Dashboard
            </Button>
          )}
          <Button variant="secondary" onClick={() => router.push(`/events/${params.id}/policy`)}>
            Policy
          </Button>
          <Button variant="ghost" onClick={() => router.push("/events")}>
            Back
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <Card>
          <CardBody>
            <p className="text-sm text-slate-500">Budget</p>
            <p className="text-xl font-bold text-slate-900 mt-1">
              {formatCurrency(event.budget_target, event.currency)}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-sm text-slate-500">Audience Size</p>
            <p className="text-xl font-bold text-slate-900 mt-1">
              {event.audience_size?.toLocaleString() || "—"}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-sm text-slate-500">Event Date</p>
            <p className="text-xl font-bold text-slate-900 mt-1">
              {event.event_date || "Not set"}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-sm text-slate-500">Duration</p>
            <p className="text-xl font-bold text-slate-900 mt-1">
              {event.duration_days} day{event.duration_days !== 1 ? "s" : ""}
            </p>
          </CardBody>
        </Card>
      </div>

      {event.description && (
        <Card className="mb-6">
          <CardHeader>
            <h2 className="font-semibold text-slate-900">Description</h2>
          </CardHeader>
          <CardBody>
            <p className="text-slate-700 text-sm leading-relaxed">{event.description}</p>
          </CardBody>
        </Card>
      )}

      {event.venue_type && (
        <Card className="mb-6">
          <CardHeader>
            <h2 className="font-semibold text-slate-900">Venue Requirements</h2>
          </CardHeader>
          <CardBody>
            <p className="text-slate-700 text-sm">{event.venue_type}</p>
          </CardBody>
        </Card>
      )}

      {/* Generation section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-900">Event Package</h2>
            {!generating && (event.status === "draft" || event.status === "review") && (
              <Button
                onClick={async () => {
                  setGenerating(true);
                  setUpdates([]);
                  try {
                    await generateAll(event.id, (u) => setUpdates((p) => [...p, u]));
                    const updated = await getEvent(event.id);
                    setEvent(updated);
                    toast("Event package generated!", "success");
                  } catch (err: unknown) {
                    toast(err instanceof Error ? err.message : "Generation failed", "error");
                  } finally {
                    setGenerating(false);
                  }
                }}
              >
                {event.status === "review" ? "Regenerate" : "Generate Package"}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardBody>
          {updates.length > 0 ? (
            <div className="space-y-2">
              {updates.map((u, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${
                    u.status === "complete" ? "bg-emerald-500" :
                    u.status === "error" ? "bg-red-500" :
                    "bg-amber-500 animate-pulse"
                  }`} />
                  <span className="capitalize font-medium text-slate-700 w-24">{u.agent}</span>
                  <span className="text-slate-500 truncate">{u.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              Generate a full event package: proposal, budget, sponsorship, approval workflow, and task board.
            </p>
          )}
        </CardBody>
      </Card>

      {/* Document links — shown after generation */}
      {(event.status === "review" || event.status === "submitted" || event.status === "approved" || event.status === "completed") && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
          <button onClick={() => router.push(`/events/${event.id}/proposal`)} className="text-left">
            <Card className="hover:border-indigo-300 transition-colors">
              <CardBody className="flex items-center gap-3">
                <span className="text-xl">📄</span>
                <div>
                  <p className="font-medium text-slate-900 text-sm">Proposal</p>
                  <p className="text-xs text-slate-500">View & edit • PDF/DOCX export</p>
                </div>
              </CardBody>
            </Card>
          </button>
          <button onClick={() => router.push(`/events/${event.id}/budget`)} className="text-left">
            <Card className="hover:border-indigo-300 transition-colors">
              <CardBody className="flex items-center gap-3">
                <span className="text-xl">💰</span>
                <div>
                  <p className="font-medium text-slate-900 text-sm">Budget</p>
                  <p className="text-xs text-slate-500">Edit line items • XLSX export</p>
                </div>
              </CardBody>
            </Card>
          </button>
          <button onClick={() => router.push(`/events/${event.id}/sponsorship`)} className="text-left">
            <Card className="hover:border-indigo-300 transition-colors">
              <CardBody className="flex items-center gap-3">
                <span className="text-xl">🤝</span>
                <div>
                  <p className="font-medium text-slate-900 text-sm">Sponsorship</p>
                  <p className="text-xs text-slate-500">Tiers & emails • PDF export</p>
                </div>
              </CardBody>
            </Card>
          </button>
        </div>
      )}

      {/* Phase 7 — Memory & Learning links */}
      {(event.status === "review" || event.status === "submitted" || event.status === "approved" || event.status === "completed") && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
          <button onClick={() => router.push(`/events/${event.id}/insights`)} className="text-left">
            <Card className="hover:border-blue-300 transition-colors border-blue-100">
              <CardBody className="flex items-center gap-3">
                <span className="text-xl">🔍</span>
                <div>
                  <p className="font-medium text-slate-900 text-sm">Historical Insights</p>
                  <p className="text-xs text-slate-500">Lessons from past events at your university</p>
                </div>
              </CardBody>
            </Card>
          </button>
          <button onClick={() => router.push(`/events/${event.id}/outcome`)} className="text-left">
            <Card className="hover:border-green-300 transition-colors border-green-100">
              <CardBody className="flex items-center gap-3">
                <span className="text-xl">📊</span>
                <div>
                  <p className="font-medium text-slate-900 text-sm">Post-Event Report</p>
                  <p className="text-xs text-slate-500">Record actual results for institutional memory</p>
                </div>
              </CardBody>
            </Card>
          </button>
        </div>
      )}
    </div>
  );
}
