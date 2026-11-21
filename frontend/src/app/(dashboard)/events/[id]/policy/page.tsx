"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getEvent, listMySocieties, uploadPolicy, submitQuestionnaire, verifyPolicy,
} from "@/lib/api";
import type { EventRecord, Society, PolicyDataRecord, QuestionnaireInput } from "@/types";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

type Mode = "select" | "upload" | "prospectus" | "questionnaire" | "review";

export default function PolicyPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();

  const [event, setEvent] = useState<EventRecord | null>(null);
  const [society, setSociety] = useState<Society | null>(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [mode, setMode] = useState<Mode>("select");
  const [policy, setPolicy] = useState<PolicyDataRecord | null>(null);

  // Upload
  const [file, setFile] = useState<File | null>(null);

  // Questionnaire
  const [q, setQ] = useState<QuestionnaireInput>({
    university_id: "",
    faculty_advisor: "",
    department: "",
    reports_to: "academic",
    previous_events: "",
    past_rejections: "",
  });

  // Verification edits
  const [editingChain, setEditingChain] = useState(false);
  const [verifyNotes, setVerifyNotes] = useState("");

  useEffect(() => {
    if (!params.id) return;
    Promise.all([getEvent(params.id as string), listMySocieties()])
      .then(([evt, socs]) => {
        setEvent(evt);
        const soc = socs.find((s) => s.id === evt.society_id);
        setSociety(soc || null);
        if (soc) {
          setQ((prev) => ({
            ...prev,
            university_id: soc.university_id,
            faculty_advisor: soc.faculty_advisor_name || "",
            department: soc.department || "",
          }));
        }
      })
      .catch(() => toast("Failed to load event", "error"))
      .finally(() => setLoading(false));
  }, [params.id, toast]);

  const handleUpload = async (uploadMode: "direct" | "prospectus") => {
    if (!file || !society) return;
    setProcessing(true);
    try {
      const result = await uploadPolicy(file, society.university_id, uploadMode, event?.id);
      setPolicy(result);
      setMode("review");
      toast("Policy extracted!", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Upload failed", "error");
    } finally {
      setProcessing(false);
    }
  };

  const handleQuestionnaire = async () => {
    if (!society) return;
    setProcessing(true);
    try {
      const result = await submitQuestionnaire({
        ...q,
        university_id: society.university_id,
        event_id: event?.id,
      });
      setPolicy(result);
      setMode("review");
      toast("Policy inferred!", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed", "error");
    } finally {
      setProcessing(false);
    }
  };

  const handleVerify = async () => {
    if (!policy) return;
    setProcessing(true);
    try {
      const result = await verifyPolicy(policy.id, {
        verification_notes: verifyNotes || undefined,
      });
      setPolicy(result);
      toast("Policy verified!", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Verification failed", "error");
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="animate-slide-up max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">University Policy Analysis</h1>
          <p className="text-slate-500 mt-1">{event?.title} — FR-002</p>
        </div>
        <Button variant="secondary" onClick={() => router.push(`/events/${params.id}`)}>
          Back to Event
        </Button>
      </div>

      {/* ===== MODE SELECT ===== */}
      {mode === "select" && (
        <>
          <p className="text-sm text-slate-600 mb-4">
            Choose how to provide your university&apos;s event policy. All modes produce the same structured output.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                key: "upload" as Mode,
                icon: "📄",
                title: "Upload Policy",
                desc: "Upload a PDF or DOCX of your university's event policy document",
                color: "indigo",
              },
              {
                key: "prospectus" as Mode,
                icon: "📚",
                title: "Upload Prospectus",
                desc: "AI will find event rules inside your full university handbook",
                color: "emerald",
              },
              {
                key: "questionnaire" as Mode,
                icon: "❓",
                title: "Answer Questions",
                desc: "5 quick questions to build a compliance checklist",
                color: "amber",
              },
            ].map((opt) => (
              <button
                key={opt.key}
                onClick={() => setMode(opt.key)}
                className="text-left group"
              >
                <Card className="hover:border-indigo-300 transition-colors h-full">
                  <CardBody className="py-6">
                    <span className="text-2xl mb-3 block">{opt.icon}</span>
                    <h3 className="font-semibold text-slate-900 mb-1">{opt.title}</h3>
                    <p className="text-sm text-slate-500">{opt.desc}</p>
                  </CardBody>
                </Card>
              </button>
            ))}
          </div>
        </>
      )}

      {/* ===== UPLOAD MODE ===== */}
      {(mode === "upload" || mode === "prospectus") && (
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-slate-900">
              {mode === "prospectus" ? "Upload University Prospectus" : "Upload Policy Document"}
            </h2>
            {mode === "prospectus" && (
              <p className="text-sm text-slate-500 mt-1">
                AI will identify and extract only the event-related sections — no need to find them yourself
              </p>
            )}
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-indigo-400 transition-colors">
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
                id="policy-file"
              />
              <label htmlFor="policy-file" className="cursor-pointer block">
                {file ? (
                  <div>
                    <p className="text-sm text-slate-700 font-medium">{file.name}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {(file.size / 1024).toFixed(0)} KB — Click to change
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-slate-500 mb-1">Click to upload PDF, DOCX, or TXT</p>
                    <p className="text-xs text-slate-400">Maximum 50 MB</p>
                  </div>
                )}
              </label>
            </div>
            <div className="flex items-center justify-between">
              <button onClick={() => { setMode("select"); setFile(null); }} className="text-sm text-slate-500 hover:text-slate-700">
                ← Back
              </button>
              <Button
                onClick={() => handleUpload(mode === "prospectus" ? "prospectus" : "direct")}
                loading={processing}
                disabled={!file}
              >
                {processing ? "Extracting policy..." : "Extract Policy"}
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* ===== QUESTIONNAIRE MODE ===== */}
      {mode === "questionnaire" && (
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-slate-900">Policy Questionnaire</h2>
            <p className="text-sm text-slate-500 mt-1">
              Answer 5 questions — results will be clearly labeled as inferred and unverified
            </p>
          </CardHeader>
          <CardBody className="space-y-4">
            <Input
              label="1. Who is your Faculty Advisor?"
              value={q.faculty_advisor}
              onChange={(e) => setQ({ ...q, faculty_advisor: e.target.value })}
              placeholder="Dr. Ali Ahmad"
            />
            <Input
              label="2. Which department is your society under?"
              value={q.department}
              onChange={(e) => setQ({ ...q, department: e.target.value })}
              placeholder="Computer Science"
            />
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                3. Does your society report to Student Affairs or the academic side?
              </label>
              <select
                value={q.reports_to}
                onChange={(e) => setQ({ ...q, reports_to: e.target.value as "academic" | "student_affairs" })}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="academic">Academic side (Department → Dean)</option>
                <option value="student_affairs">Student Affairs Office (direct)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                4. Have you organized events before? How far in advance did you submit?
              </label>
              <textarea
                value={q.previous_events}
                onChange={(e) => setQ({ ...q, previous_events: e.target.value })}
                rows={2}
                placeholder="We organized 2 hackathons last year, submitted about 3 weeks before..."
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                5. Have any past events been rejected? If so, why?
              </label>
              <textarea
                value={q.past_rejections}
                onChange={(e) => setQ({ ...q, past_rejections: e.target.value })}
                rows={2}
                placeholder="One seminar was rejected because we didn't include a budget plan..."
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              />
            </div>
            <div className="flex items-center justify-between pt-2">
              <button onClick={() => setMode("select")} className="text-sm text-slate-500 hover:text-slate-700">
                ← Back
              </button>
              <Button onClick={handleQuestionnaire} loading={processing}>
                {processing ? "Analyzing answers..." : "Generate Policy"}
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* ===== REVIEW MODE ===== */}
      {mode === "review" && policy && (
        <>
          {/* Confidence / Review Banner */}
          {policy.needs_review && !policy.is_verified && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-md text-sm mb-4">
              <strong>Human review recommended</strong> — Confidence score is{" "}
              {((policy.confidence_score || 0) * 100).toFixed(0)}% (below 70% threshold).
              Please verify before relying on this for event planning.
            </div>
          )}
          {policy.is_verified && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-md text-sm mb-4">
              <strong>Verified</strong> — This policy has been reviewed and confirmed.
              {policy.verification_notes && ` Notes: ${policy.verification_notes}`}
            </div>
          )}

          {/* Extraction Warnings */}
          {policy.extraction_warnings && policy.extraction_warnings.length > 0 && (
            <Card className="mb-4 border-amber-200 bg-amber-50">
              <CardBody>
                <h3 className="text-sm font-medium text-amber-800 mb-2">Extraction Notes</h3>
                <ul className="list-disc list-inside text-sm text-amber-700 space-y-1">
                  {policy.extraction_warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </CardBody>
            </Card>
          )}

          {/* Main Policy Card */}
          <Card className="mb-4">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-slate-900">Extracted Policy Data</h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Source: {policy.source_format}
                    {policy.source_filename && ` — ${policy.source_filename}`}
                    {policy.source_page_count && ` (${policy.source_page_count} pages)`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    policy.is_verified
                      ? "bg-emerald-100 text-emerald-700"
                      : policy.needs_review
                        ? "bg-amber-100 text-amber-700"
                        : "bg-slate-100 text-slate-600"
                  }`}>
                    {policy.is_verified ? "Verified" : policy.needs_review ? "Needs Review" : "Unverified"}
                  </span>
                  <span className="text-xs text-slate-400">
                    {((policy.confidence_score || 0) * 100).toFixed(0)}% confidence
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardBody className="space-y-5">
              {/* Approval Chain */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Approval Chain</h3>
                {policy.approval_chain?.steps && policy.approval_chain.steps.length > 0 ? (
                  <div className="space-y-2">
                    {policy.approval_chain.steps.map((step, i) => (
                      <div key={i} className="flex items-center gap-3 bg-slate-50 rounded-md p-3">
                        <span className="w-7 h-7 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-xs font-bold shrink-0">
                          {step.order}
                        </span>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-slate-800">{step.authority}</p>
                          {step.notes && (
                            <p className="text-xs text-slate-400">{step.notes}</p>
                          )}
                        </div>
                        <span className="text-xs text-slate-400 font-mono">{step.role}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400 italic">Not found in document</p>
                )}
              </div>

              {/* Lead Time */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700">Submission Lead Time</h3>
                <p className="text-sm text-slate-600 mt-1">
                  {policy.lead_time_days
                    ? `${policy.lead_time_days} days before event date`
                    : "Not specified"}
                </p>
              </div>

              {/* Required Documents */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-1">Required Documents</h3>
                {policy.required_documents && policy.required_documents.length > 0 ? (
                  <ul className="space-y-1">
                    {policy.required_documents.map((doc, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
                        <svg className="w-4 h-4 text-indigo-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        {doc}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400 italic">None specified</p>
                )}
              </div>

              {/* Sponsorship Rules */}
              {policy.sponsorship_rules && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700">Sponsorship Rules</h3>
                  <p className="text-sm text-slate-600 mt-1 leading-relaxed">{policy.sponsorship_rules}</p>
                </div>
              )}

              {/* Prohibitions */}
              {policy.prohibitions && policy.prohibitions.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-1">Prohibited Activities</h3>
                  <ul className="space-y-1">
                    {policy.prohibitions.map((p, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-red-600">
                        <span className="w-4 h-4 text-red-400 shrink-0">✕</span>
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Source References */}
              {policy.source_references && policy.source_references.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 mb-1">Source References</h3>
                  <div className="space-y-2">
                    {policy.source_references.map((ref, i) => (
                      <div key={i} className="bg-slate-50 rounded p-2 text-xs">
                        <span className="font-medium text-slate-600">{ref.source}</span>
                        {ref.excerpt && (
                          <p className="text-slate-400 mt-0.5 italic">&ldquo;{ref.excerpt}&rdquo;</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          {/* Verification section */}
          {!policy.is_verified && (
            <Card className="mb-4">
              <CardHeader>
                <h2 className="font-semibold text-slate-900">Verify Policy</h2>
              </CardHeader>
              <CardBody className="space-y-3">
                <p className="text-sm text-slate-500">
                  Review the extracted data above. If correct, verify to confirm.
                  You can also add notes about any corrections made.
                </p>
                <textarea
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  rows={2}
                  placeholder="Optional: verification notes (e.g., 'Checked against 2026 student handbook')"
                  className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </CardBody>
            </Card>
          )}

          {/* Action buttons */}
          <div className="flex items-center justify-between">
            <button onClick={() => { setMode("select"); setPolicy(null); }} className="text-sm text-slate-500 hover:text-slate-700">
              ← Re-analyze with different input
            </button>
            <div className="flex items-center gap-3">
              {!policy.is_verified && (
                <Button onClick={handleVerify} loading={processing}>
                  Verify &amp; Confirm
                </Button>
              )}
              <Button variant="secondary" onClick={() => router.push(`/events/${params.id}`)}>
                Done
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
