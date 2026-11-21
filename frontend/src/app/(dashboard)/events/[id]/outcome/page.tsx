"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { submitOutcome, getOutcome, verifyOutcome, getEventInsights } from "@/lib/api";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Card from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";

export default function OutcomePage() {
  const params = useParams();
  const router = useRouter();
  const eventId = params.id as string;
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [existingOutcome, setExistingOutcome] = useState<Record<string, unknown> | null>(null);
  const [insights, setInsights] = useState<Record<string, unknown> | null>(null);

  // Form state
  const [form, setForm] = useState({
    approval_result: "approved",
    rejection_reasons: "",
    actual_approval_days: "",
    actual_spend: "",
    overspent_categories: "",
    actual_audience: "",
    sponsors_pitched: "",
    sponsors_confirmed: "",
    lessons_learned: "",
    risk_flags: "",
  });

  useEffect(() => {
    loadData();
  }, [eventId]);

  async function loadData() {
    setLoading(true);
    try {
      const outcome = await getOutcome(eventId);
      if (outcome) {
        setExistingOutcome(outcome);
        // Pre-fill form
        setForm({
          approval_result: String(outcome.approval_result || "approved"),
          rejection_reasons: Array.isArray(outcome.rejection_reasons) ? (outcome.rejection_reasons as string[]).join(", ") : "",
          actual_approval_days: outcome.actual_approval_days != null ? String(outcome.actual_approval_days) : "",
          actual_spend: outcome.actual_spend != null ? String(outcome.actual_spend) : "",
          overspent_categories: Array.isArray(outcome.overspent_categories) ? (outcome.overspent_categories as string[]).join(", ") : "",
          actual_audience: outcome.actual_audience != null ? String(outcome.actual_audience) : "",
          sponsors_pitched: outcome.sponsors_pitched != null ? String(outcome.sponsors_pitched) : "",
          sponsors_confirmed: outcome.sponsors_confirmed != null ? String(outcome.sponsors_confirmed) : "",
          lessons_learned: String(outcome.lessons_learned || ""),
          risk_flags: Array.isArray(outcome.risk_flags) ? (outcome.risk_flags as string[]).join(", ") : "",
        });
      }
    } catch {
      // No existing outcome — that's fine
    }

    // Load insights
    try {
      const insightData = await getEventInsights(eventId);
      setInsights(insightData);
    } catch {
      // No insights yet
    }
    setLoading(false);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);

    const payload: Record<string, unknown> = {
      approval_result: form.approval_result,
      actual_approval_days: form.actual_approval_days ? parseInt(form.actual_approval_days) : null,
      actual_spend: form.actual_spend ? parseFloat(form.actual_spend) : null,
      actual_audience: form.actual_audience ? parseInt(form.actual_audience) : null,
      sponsors_pitched: form.sponsors_pitched ? parseInt(form.sponsors_pitched) : null,
      sponsors_confirmed: form.sponsors_confirmed ? parseInt(form.sponsors_confirmed) : null,
      lessons_learned: form.lessons_learned || null,
    };

    if (form.rejection_reasons) {
      payload.rejection_reasons = form.rejection_reasons.split(",").map((r: string) => r.trim()).filter(Boolean);
    }
    if (form.overspent_categories) {
      payload.overspent_categories = form.overspent_categories.split(",").map((c: string) => c.trim()).filter(Boolean);
    }
    if (form.risk_flags) {
      payload.risk_flags = form.risk_flags.split(",").map((f: string) => f.trim()).filter(Boolean);
    }

    try {
      await submitOutcome(eventId, payload);
      toast("Event outcome recorded and memory generated!", "success");
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit outcome";
      toast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerify() {
    try {
      await verifyOutcome(eventId);
      toast("Outcome verified!", "success");
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to verify";
      toast(msg, "error");
    }
  }

  if (loading) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Post-Event Report</h1>
          <p className="text-gray-500 mt-1">Record actual results for institutional memory</p>
        </div>
        <Button variant="ghost" onClick={() => router.push(`/events/${eventId}`)}>
          ← Back to Event
        </Button>
      </div>

      {/* Historical Insights */}
      {insights && (insights.recommendations as string[] | undefined)?.length ? (
        <Card>
          <div className="p-4">
            <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              Historical Insights
            </h2>
            <div className="space-y-2">
              {(insights.recommendations as string[]).map((rec: string, i: number) => (
                <div key={i} className="text-sm bg-blue-50 p-3 rounded-lg border border-blue-200">
                  {rec}
                </div>
              ))}
            </div>
            {insights.total_historical_events ? (
              <p className="text-xs text-gray-500 mt-2">
                Based on {String(insights.total_historical_events)} previous event(s) at this university
              </p>
            ) : null}
          </div>
        </Card>
      ) : null}

      {/* Existing Outcome Display */}
      {existingOutcome && (
        <Card>
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">Recorded Outcome</h2>
              <div className="flex items-center gap-2">
                {existingOutcome.is_verified ? (
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded-full">Verified</span>
                ) : (
                  <>
                    <span className="text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full">Unverified</span>
                    <Button size="sm" onClick={handleVerify}>Verify</Button>
                  </>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Result</span>
                <div className="font-medium capitalize">{String(existingOutcome.approval_result)}</div>
              </div>
              <div>
                <span className="text-gray-500">Budget Variance</span>
                <div className={`font-medium ${Number(existingOutcome.budget_variance_pct) > 0 ? "text-red-600" : "text-green-600"}`}>
                  {existingOutcome.budget_variance_pct != null ? `${Number(existingOutcome.budget_variance_pct).toFixed(1)}%` : "N/A"}
                </div>
              </div>
              <div>
                <span className="text-gray-500">Actual Audience</span>
                <div className="font-medium">{existingOutcome.actual_audience != null ? String(existingOutcome.actual_audience) : "N/A"}</div>
              </div>
              <div>
                <span className="text-gray-500">Approval Days</span>
                <div className="font-medium">{existingOutcome.actual_approval_days != null ? String(existingOutcome.actual_approval_days) : "N/A"}</div>
              </div>
            </div>
            {existingOutcome.lessons_learned ? (
              <div className="mt-3 text-sm">
                <span className="text-gray-500">Lessons Learned</span>
                <p className="mt-1">{String(existingOutcome.lessons_learned)}</p>
              </div>
            ) : null}
          </div>
        </Card>
      )}

      {/* Outcome Form */}
      {!existingOutcome && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <Card>
            <div className="p-4 space-y-4">
              <h2 className="text-lg font-semibold">Event Results</h2>

              <div>
                <label className="block text-sm font-medium mb-1">Approval Result *</label>
                <select
                  className="w-full border rounded-lg px-3 py-2"
                  value={form.approval_result}
                  onChange={(e) => setForm({ ...form, approval_result: e.target.value })}
                >
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                  <option value="withdrawn">Withdrawn</option>
                </select>
              </div>

              {form.approval_result === "rejected" && (
                <Input
                  label="Rejection Reasons (comma-separated)"
                  value={form.rejection_reasons}
                  onChange={(e) => setForm({ ...form, rejection_reasons: e.target.value })}
                  placeholder="e.g., Insufficient documentation, Budget too high"
                />
              )}

              <Input
                label="Actual Approval Duration (days)"
                type="number"
                value={form.actual_approval_days}
                onChange={(e) => setForm({ ...form, actual_approval_days: e.target.value })}
                placeholder="e.g., 14"
              />
            </div>
          </Card>

          <Card>
            <div className="p-4 space-y-4">
              <h2 className="text-lg font-semibold">Financial Results</h2>
              <Input
                label="Actual Spend"
                type="number"
                value={form.actual_spend}
                onChange={(e) => setForm({ ...form, actual_spend: e.target.value })}
                placeholder="e.g., 150000"
              />
              <Input
                label="Overspent Categories (comma-separated)"
                value={form.overspent_categories}
                onChange={(e) => setForm({ ...form, overspent_categories: e.target.value })}
                placeholder="e.g., Catering, Marketing"
              />
            </div>
          </Card>

          <Card>
            <div className="p-4 space-y-4">
              <h2 className="text-lg font-semibold">Attendance & Sponsorship</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Actual Audience"
                  type="number"
                  value={form.actual_audience}
                  onChange={(e) => setForm({ ...form, actual_audience: e.target.value })}
                  placeholder="e.g., 300"
                />
                <Input
                  label="Sponsors Pitched"
                  type="number"
                  value={form.sponsors_pitched}
                  onChange={(e) => setForm({ ...form, sponsors_pitched: e.target.value })}
                  placeholder="e.g., 10"
                />
                <Input
                  label="Sponsors Confirmed"
                  type="number"
                  value={form.sponsors_confirmed}
                  onChange={(e) => setForm({ ...form, sponsors_confirmed: e.target.value })}
                  placeholder="e.g., 4"
                />
              </div>
            </div>
          </Card>

          <Card>
            <div className="p-4 space-y-4">
              <h2 className="text-lg font-semibold">Lessons & Risks</h2>
              <div>
                <label className="block text-sm font-medium mb-1">Lessons Learned</label>
                <textarea
                  className="w-full border rounded-lg px-3 py-2 h-24"
                  value={form.lessons_learned}
                  onChange={(e) => setForm({ ...form, lessons_learned: e.target.value })}
                  placeholder="What went well? What would you do differently?"
                />
              </div>
              <Input
                label="Risk Flags (comma-separated)"
                value={form.risk_flags}
                onChange={(e) => setForm({ ...form, risk_flags: e.target.value })}
                placeholder="e.g., Venue overcrowded, Late sponsor payments"
              />
            </div>
          </Card>

          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={() => router.push(`/events/${eventId}`)}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Submit Event Outcome
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
