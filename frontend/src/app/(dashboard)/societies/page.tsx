"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listMySocieties, listUniversities, createSociety } from "@/lib/api";
import type { Society, University, SocietyType } from "@/types";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

export default function SocietiesPage() {
  const [societies, setSocieties] = useState<Society[]>([]);
  const [universities, setUniversities] = useState<University[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const { toast } = useToast();

  // Form state
  const [name, setName] = useState("");
  const [universityId, setUniversityId] = useState("");
  const [department, setDepartment] = useState("");
  const [societyType, setSocietyType] = useState<SocietyType>("technical");
  const [advisorName, setAdvisorName] = useState("");
  const [advisorEmail, setAdvisorEmail] = useState("");

  useEffect(() => {
    Promise.all([listMySocieties(), listUniversities()])
      .then(([s, u]) => {
        setSocieties(s);
        setUniversities(u);
      })
      .catch(() => toast("Failed to load data", "error"))
      .finally(() => setLoading(false));
  }, [toast]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const society = await createSociety({
        name,
        university_id: universityId,
        department,
        society_type: societyType,
        faculty_advisor_name: advisorName || undefined,
        faculty_advisor_email: advisorEmail || undefined,
      });
      setSocieties((prev) => [...prev, society]);
      setShowForm(false);
      setName("");
      setDepartment("");
      setAdvisorName("");
      setAdvisorEmail("");
      toast("Society created!", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to create society", "error");
    } finally {
      setCreating(false);
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
    <div className="animate-slide-up max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Societies</h1>
          <p className="text-slate-500 mt-1">Manage your student society profiles</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "New Society"}
        </Button>
      </div>

      {/* Create form */}
      {showForm && (
        <Card className="mb-6">
          <CardHeader>
            <h2 className="font-semibold text-slate-900">Set Up Your Society</h2>
          </CardHeader>
          <CardBody>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  label="Society Name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="ACM Student Chapter"
                  required
                />
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    University
                  </label>
                  <select
                    value={universityId}
                    onChange={(e) => setUniversityId(e.target.value)}
                    required
                    className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select university...</option>
                    {universities.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name}
                      </option>
                    ))}
                  </select>
                </div>
                <Input
                  label="Department"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  placeholder="Computer Science"
                  required
                />
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Society Type
                  </label>
                  <select
                    value={societyType}
                    onChange={(e) => setSocietyType(e.target.value as SocietyType)}
                    className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="technical">Technical</option>
                    <option value="cultural">Cultural</option>
                    <option value="professional">Professional</option>
                  </select>
                </div>
                <Input
                  label="Faculty Advisor Name"
                  value={advisorName}
                  onChange={(e) => setAdvisorName(e.target.value)}
                  placeholder="Dr. Ali Ahmad"
                />
                <Input
                  label="Faculty Advisor Email"
                  type="email"
                  value={advisorEmail}
                  onChange={(e) => setAdvisorEmail(e.target.value)}
                  placeholder="advisor@university.edu.pk"
                />
              </div>
              <div className="flex justify-end">
                <Button type="submit" loading={creating}>
                  Create Society
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      {/* Society list */}
      {societies.length === 0 ? (
        <Card>
          <CardBody className="text-center py-12">
            <p className="text-slate-500 mb-2">No societies yet</p>
            <p className="text-sm text-slate-400">
              Create your first society to get started with event planning
            </p>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-4">
          {societies.map((s) => (
            <Link key={s.id} href={`/societies/${s.id}`}>
              <Card className="hover:border-indigo-300 transition-colors cursor-pointer">
                <CardBody className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-900">{s.name}</h3>
                    <p className="text-sm text-slate-500">
                      {s.department} &middot;{" "}
                      <span className="capitalize">{s.society_type}</span>
                    </p>
                    {s.faculty_advisor_name && (
                      <p className="text-sm text-slate-400 mt-1">
                        Advisor: {s.faculty_advisor_name}
                      </p>
                    )}
                  </div>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 capitalize">
                    {s.society_type}
                  </span>
                </CardBody>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
