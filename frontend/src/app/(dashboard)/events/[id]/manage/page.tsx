"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// We import accessToken through a simple module-level approach
let token = "";

interface DashboardData {
  event: Record<string, unknown>;
  society: { name: string } | null;
  documents: { has_proposal: boolean; has_budget: boolean; has_sponsorship: boolean };
  budget: { planned: number; allocated: number; currency: string; categories: { name: string; amount: number }[]; warnings: string[] } | null;
  approvals: { total: number; approved: number; steps: ApprovalStep[] };
  tasks: { total: number; completed: number; overdue: number; by_status: Record<string, number>; items: TaskItem[] };
  upcoming_deadlines: { type: string; title: string; date: string }[];
}

interface ApprovalStep {
  id: string; step_order: number; authority: string; role: string;
  deadline: string | null; status: string; rag: string; notes: string | null;
  required_documents: string[] | null;
}

interface TaskItem {
  id: string; title: string; description: string; team: string;
  assigned_to: string | null; due_date: string | null;
  priority: string; status: string; overdue: boolean;
}

type Tab = "overview" | "approvals" | "tasks" | "budget" | "timeline";

const RAG_COLORS = { green: "bg-emerald-500", amber: "bg-amber-500", red: "bg-red-500" };
const STATUS_BADGE: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700", submitted: "bg-blue-100 text-blue-700",
  approved: "bg-emerald-100 text-emerald-700", rejected: "bg-red-100 text-red-700",
  todo: "bg-slate-100 text-slate-700", in_progress: "bg-blue-100 text-blue-700",
  review: "bg-amber-100 text-amber-700", completed: "bg-emerald-100 text-emerald-700",
};
const PRIORITY_BADGE: Record<string, string> = {
  low: "text-slate-500", medium: "text-blue-600", high: "text-amber-600", urgent: "text-red-600",
};

export default function EventManagePage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const eventId = params.id as string;

  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");

  const fetchDashboard = async () => {
    try {
      // Get token from localStorage refresh token approach
      const stored = localStorage.getItem("refresh_token");
      if (stored) {
        const r = await fetch(`${API}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: stored }),
        });
        const j = await r.json();
        if (j.success) token = j.data.access_token;
      }

      const res = await fetch(`${API}/events/${eventId}/dashboard`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      if (json.success) setData(json.data);
    } catch {
      toast("Failed to load dashboard", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDashboard(); }, [eventId]);

  const updateTask = async (taskId: string, updates: Record<string, string>) => {
    try {
      await fetch(`${API}/events/${eventId}/tasks/${taskId}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      await fetchDashboard();
      toast("Task updated", "success");
    } catch { toast("Update failed", "error"); }
  };

  const updateApproval = async (stepId: string, status: string) => {
    try {
      await fetch(`${API}/events/${eventId}/approvals/${stepId}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      await fetchDashboard();
      toast("Approval updated", "success");
    } catch { toast("Update failed", "error"); }
  };

  if (loading || !data) {
    return <div className="flex items-center justify-center py-20"><div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" /></div>;
  }

  const e = data.event;
  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "overview", label: "Overview" },
    { key: "approvals", label: "Approvals", count: data.approvals.total },
    { key: "tasks", label: "Tasks", count: data.tasks.total },
    { key: "budget", label: "Budget" },
    { key: "timeline", label: "Timeline" },
  ];

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{e.title as string}</h1>
          <p className="text-sm text-slate-500">
            {data.society?.name} &middot; {(e.event_type as string)?.replace("_", " ")} &middot; {e.event_date as string || "Date TBD"}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => router.push(`/events/${eventId}`)}>Back</Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 mb-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key ? "border-indigo-600 text-indigo-700" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1.5 text-xs bg-slate-100 text-slate-600 rounded-full px-1.5">{t.count}</span>}
          </button>
        ))}
      </div>

      {/* TAB: Overview */}
      {tab === "overview" && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Card><CardBody><p className="text-xs text-slate-500">Approvals</p><p className="text-xl font-bold text-slate-900">{data.approvals.approved}/{data.approvals.total}</p></CardBody></Card>
            <Card><CardBody><p className="text-xs text-slate-500">Tasks Done</p><p className="text-xl font-bold text-slate-900">{data.tasks.completed}/{data.tasks.total}</p></CardBody></Card>
            <Card><CardBody><p className="text-xs text-slate-500">Overdue</p><p className={`text-xl font-bold ${data.tasks.overdue > 0 ? "text-red-600" : "text-slate-900"}`}>{data.tasks.overdue}</p></CardBody></Card>
            <Card><CardBody><p className="text-xs text-slate-500">Budget</p><p className="text-xl font-bold text-slate-900">{String(e.currency || "PKR")} {((e.budget_target as number) || 0).toLocaleString()}</p></CardBody></Card>
          </div>

          {/* Upcoming */}
          {data.upcoming_deadlines.length > 0 && (
            <Card>
              <CardHeader><h2 className="font-semibold text-slate-900 text-sm">Upcoming Deadlines</h2></CardHeader>
              <CardBody>
                <div className="space-y-2">
                  {data.upcoming_deadlines.slice(0, 5).map((d, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${d.type === "approval" ? "bg-indigo-500" : "bg-amber-500"}`} />
                        <span className="text-slate-700">{d.title}</span>
                      </div>
                      <span className="text-slate-400 text-xs">{d.date}</span>
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>
          )}

          {/* Documents */}
          <Card>
            <CardHeader><h2 className="font-semibold text-slate-900 text-sm">Documents</h2></CardHeader>
            <CardBody>
              <div className="flex gap-4 flex-wrap">
                {data.documents.has_proposal && <button onClick={() => router.push(`/events/${eventId}/proposal`)} className="text-sm text-indigo-600 hover:text-indigo-700">📄 Proposal</button>}
                {data.documents.has_budget && <button onClick={() => router.push(`/events/${eventId}/budget`)} className="text-sm text-indigo-600 hover:text-indigo-700">💰 Budget</button>}
                {data.documents.has_sponsorship && <button onClick={() => router.push(`/events/${eventId}/sponsorship`)} className="text-sm text-indigo-600 hover:text-indigo-700">🤝 Sponsorship</button>}
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* TAB: Approvals */}
      {tab === "approvals" && (
        <div className="space-y-3">
          {data.approvals.steps.map((step) => (
            <Card key={step.id}>
              <CardBody className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`w-3 h-3 rounded-full ${RAG_COLORS[step.rag as keyof typeof RAG_COLORS] || "bg-slate-300"}`} />
                  <div>
                    <p className="font-medium text-slate-900 text-sm">{step.step_order}. {step.authority}</p>
                    <p className="text-xs text-slate-400">{step.deadline ? `Due: ${step.deadline}` : "No deadline"}</p>
                    {step.required_documents && step.required_documents.length > 0 && (
                      <p className="text-xs text-slate-400 mt-0.5">Docs: {step.required_documents.join(", ")}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={step.status}
                    onChange={(e) => updateApproval(step.id, e.target.value)}
                    className={`text-xs rounded-full px-2 py-1 font-medium border-0 cursor-pointer ${STATUS_BADGE[step.status] || "bg-slate-100"}`}
                  >
                    <option value="pending">Pending</option>
                    <option value="submitted">Submitted</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* TAB: Tasks (Kanban) */}
      {tab === "tasks" && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {(["todo", "in_progress", "review", "completed"] as const).map((col) => {
            const colTasks = data.tasks.items.filter((t) => t.status === col);
            const colLabels = { todo: "To Do", in_progress: "In Progress", review: "Review", completed: "Completed" };
            return (
              <div key={col}>
                <h3 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                  {colLabels[col]} <span className="text-xs bg-slate-100 rounded-full px-1.5">{colTasks.length}</span>
                </h3>
                <div className="space-y-2">
                  {colTasks.map((task) => (
                    <Card key={task.id} className={task.overdue ? "border-red-300" : ""}>
                      <CardBody className="p-3">
                        <p className="text-sm font-medium text-slate-900">{task.title}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{task.team}{task.assigned_to ? ` · ${task.assigned_to}` : ""}</p>
                        <div className="flex items-center justify-between mt-2">
                          <span className={`text-xs font-medium ${PRIORITY_BADGE[task.priority] || ""}`}>{task.priority}</span>
                          {task.due_date && <span className={`text-xs ${task.overdue ? "text-red-600 font-medium" : "text-slate-400"}`}>{task.due_date}</span>}
                        </div>
                        {col !== "completed" && (
                          <div className="mt-2 flex gap-1">
                            {col === "todo" && <button onClick={() => updateTask(task.id, { status: "in_progress" })} className="text-xs text-indigo-600 hover:text-indigo-700">Start →</button>}
                            {col === "in_progress" && <button onClick={() => updateTask(task.id, { status: "review" })} className="text-xs text-indigo-600 hover:text-indigo-700">Review →</button>}
                            {col === "review" && <button onClick={() => updateTask(task.id, { status: "completed" })} className="text-xs text-emerald-600 hover:text-emerald-700">Complete ✓</button>}
                          </div>
                        )}
                      </CardBody>
                    </Card>
                  ))}
                  {colTasks.length === 0 && <p className="text-xs text-slate-400 text-center py-4">No tasks</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* TAB: Budget */}
      {tab === "budget" && data.budget && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card><CardBody><p className="text-xs text-slate-500">Planned</p><p className="text-xl font-bold text-slate-900">{data.budget.currency} {data.budget.planned.toLocaleString()}</p></CardBody></Card>
            <Card><CardBody><p className="text-xs text-slate-500">Allocated</p><p className="text-xl font-bold text-slate-900">{data.budget.currency} {data.budget.allocated.toLocaleString()}</p></CardBody></Card>
            <Card><CardBody><p className="text-xs text-slate-500">Remaining</p><p className="text-xl font-bold text-emerald-600">{data.budget.currency} {(data.budget.planned - data.budget.allocated).toLocaleString()}</p></CardBody></Card>
          </div>
          {data.budget.warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-md text-sm">
              {data.budget.warnings.map((w, i) => <p key={i}>{w}</p>)}
            </div>
          )}
          <Card>
            <CardHeader><h2 className="font-semibold text-slate-900 text-sm">Category Breakdown</h2></CardHeader>
            <CardBody>
              <div className="space-y-3">
                {data.budget.categories.map((cat, i) => {
                  const pct = data.budget!.allocated > 0 ? (cat.amount / data.budget!.allocated) * 100 : 0;
                  return (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-700">{cat.name}</span>
                        <span className="text-slate-600 font-medium">{data.budget!.currency} {cat.amount.toLocaleString()} ({pct.toFixed(0)}%)</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2">
                        <div className={`h-2 rounded-full ${pct > 40 ? "bg-amber-500" : "bg-indigo-500"}`} style={{ width: `${Math.min(pct, 100)}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardBody>
          </Card>
          <div className="flex justify-end">
            <Button variant="secondary" size="sm" onClick={() => router.push(`/events/${eventId}/budget`)}>Edit Budget →</Button>
          </div>
        </div>
      )}

      {/* TAB: Timeline */}
      {tab === "timeline" && (
        <Card>
          <CardHeader><h2 className="font-semibold text-slate-900 text-sm">Event Timeline</h2></CardHeader>
          <CardBody>
            <div className="relative">
              <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-200" />
              {[
                ...data.approvals.steps.map((s) => ({ type: "approval" as const, title: s.authority, date: s.deadline, status: s.status, rag: s.rag })),
                ...data.tasks.items.filter((t) => t.due_date).map((t) => ({ type: "task" as const, title: t.title, date: t.due_date, status: t.status, rag: t.overdue ? "red" : t.status === "completed" ? "green" : "amber" })),
              ]
                .sort((a, b) => (a.date || "9999").localeCompare(b.date || "9999"))
                .map((item, i) => (
                  <div key={i} className="relative pl-10 pb-4">
                    <span className={`absolute left-2.5 w-3 h-3 rounded-full border-2 border-white ${RAG_COLORS[item.rag as keyof typeof RAG_COLORS] || "bg-slate-300"}`} />
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-slate-800">{item.title}</p>
                        <p className="text-xs text-slate-400">{item.type === "approval" ? "Approval" : "Task"} · {item.status}</p>
                      </div>
                      <span className="text-xs text-slate-400">{item.date || "No date"}</span>
                    </div>
                  </div>
                ))}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
