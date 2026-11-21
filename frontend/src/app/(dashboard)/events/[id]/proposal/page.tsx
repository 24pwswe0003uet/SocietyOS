"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getProposal, updateProposal, getExportUrl } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";

const SECTION_LABELS: Record<string, string> = {
  executive_summary: "Executive Summary",
  objectives: "Objectives",
  scope: "Scope",
  schedule: "Schedule",
  resources: "Resources",
  expected_outcomes: "Expected Outcomes",
  risk_assessment: "Risk Assessment",
  appendices: "Appendices",
};

export default function ProposalEditorPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const eventId = params.id as string;

  const [sections, setSections] = useState<Record<string, string>>({});
  const [version, setVersion] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getProposal(eventId)
      .then((data) => {
        setSections((data as Record<string, unknown>).sections as Record<string, string> || {});
        setVersion((data as Record<string, unknown>).version as number || 1);
      })
      .catch(() => toast("No proposal found — generate the event package first", "error"))
      .finally(() => setLoading(false));
  }, [eventId, toast]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const result = await updateProposal(eventId, sections);
      setVersion(result.version as number);
      toast(`Proposal saved (version ${result.version})`, "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Save failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const updateSection = (key: string, value: string) => {
    setSections((prev) => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20"><div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" /></div>;
  }

  return (
    <div className="animate-slide-up max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Proposal Editor</h1>
          <p className="text-sm text-slate-500">Version {version} — Edit sections below</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => window.open(getExportUrl(eventId, "proposal/pdf"))}>
            PDF
          </Button>
          <Button variant="secondary" size="sm" onClick={() => window.open(getExportUrl(eventId, "proposal/docx"))}>
            DOCX
          </Button>
          <Button onClick={handleSave} loading={saving}>
            Save
          </Button>
          <Button variant="ghost" onClick={() => router.push(`/events/${eventId}`)}>
            Back
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        {Object.entries(SECTION_LABELS).map(([key, label]) => (
          <Card key={key}>
            <CardHeader>
              <h2 className="font-semibold text-slate-900">{label}</h2>
            </CardHeader>
            <CardBody>
              <textarea
                value={sections[key] || ""}
                onChange={(e) => updateSection(key, e.target.value)}
                rows={6}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-y"
                placeholder={`Enter ${label.toLowerCase()}...`}
              />
            </CardBody>
          </Card>
        ))}
      </div>

      <div className="flex justify-end mt-6">
        <Button onClick={handleSave} loading={saving}>Save Changes</Button>
      </div>
    </div>
  );
}
