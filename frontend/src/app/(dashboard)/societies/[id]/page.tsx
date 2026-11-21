"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getSociety, updateSociety } from "@/lib/api";
import type { Society, ApprovalStep } from "@/types";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

export default function SocietyProfilePage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const [society, setSociety] = useState<Society | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Editable fields
  const [advisorName, setAdvisorName] = useState("");
  const [advisorEmail, setAdvisorEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [description, setDescription] = useState("");
  const [chain, setChain] = useState<ApprovalStep[]>([]);

  useEffect(() => {
    if (!params.id) return;
    getSociety(params.id as string)
      .then((s) => {
        setSociety(s);
        setAdvisorName(s.faculty_advisor_name || "");
        setAdvisorEmail(s.faculty_advisor_email || "");
        setDepartment(s.department);
        setDescription(s.description || "");
        setChain(s.approval_chain?.steps || []);
      })
      .catch(() => toast("Failed to load society", "error"))
      .finally(() => setLoading(false));
  }, [params.id, toast]);

  const handleSave = async () => {
    if (!society) return;
    setSaving(true);
    try {
      const updated = await updateSociety(society.id, {
        faculty_advisor_name: advisorName || undefined,
        faculty_advisor_email: advisorEmail || undefined,
        department,
        description: description || undefined,
        approval_chain: { steps: chain },
      } as Partial<Society>);
      setSociety(updated);
      toast("Society profile updated!", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Update failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const addStep = () => {
    setChain((prev) => [
      ...prev,
      { order: prev.length + 1, authority: "", role: "" },
    ]);
  };

  const removeStep = (index: number) => {
    setChain((prev) =>
      prev.filter((_, i) => i !== index).map((s, i) => ({ ...s, order: i + 1 }))
    );
  };

  const updateStep = (index: number, field: keyof ApprovalStep, value: string | number) => {
    setChain((prev) =>
      prev.map((s, i) => (i === index ? { ...s, [field]: value } : s))
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!society) {
    return <p className="text-slate-500 py-10 text-center">Society not found.</p>;
  }

  return (
    <div className="animate-slide-up max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{society.name}</h1>
          <p className="text-slate-500 capitalize">{society.society_type} society</p>
        </div>
        <Button variant="secondary" onClick={() => router.push("/societies")}>
          Back
        </Button>
      </div>

      {/* Profile Details */}
      <Card className="mb-6">
        <CardHeader>
          <h2 className="font-semibold text-slate-900">Society Profile</h2>
        </CardHeader>
        <CardBody>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Department"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            />
            <Input
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of your society"
            />
            <Input
              label="Faculty Advisor Name"
              value={advisorName}
              onChange={(e) => setAdvisorName(e.target.value)}
            />
            <Input
              label="Faculty Advisor Email"
              type="email"
              value={advisorEmail}
              onChange={(e) => setAdvisorEmail(e.target.value)}
            />
          </div>
        </CardBody>
      </Card>

      {/* Approval Chain Editor */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-slate-900">Approval Chain</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Customize who approves your events and in what order
              </p>
            </div>
            <Button variant="secondary" size="sm" onClick={addStep}>
              Add Step
            </Button>
          </div>
        </CardHeader>
        <CardBody>
          {chain.length === 0 ? (
            <p className="text-sm text-slate-500 text-center py-4">
              No approval steps defined. Click &quot;Add Step&quot; to start.
            </p>
          ) : (
            <div className="space-y-3">
              {chain.map((step, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 bg-slate-50 rounded-md p-3"
                >
                  <span className="w-7 h-7 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center text-sm font-medium shrink-0">
                    {step.order}
                  </span>
                  <input
                    className="flex-1 text-sm border border-slate-200 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Authority name (e.g. Faculty Advisor)"
                    value={step.authority}
                    onChange={(e) => updateStep(i, "authority", e.target.value)}
                  />
                  <input
                    className="w-40 text-sm border border-slate-200 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Role key"
                    value={step.role}
                    onChange={(e) => updateStep(i, "role", e.target.value)}
                  />
                  <button
                    onClick={() => removeStep(i)}
                    className="text-red-500 hover:text-red-700 shrink-0"
                    title="Remove step"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} loading={saving}>
          Save Profile
        </Button>
      </div>
    </div>
  );
}
