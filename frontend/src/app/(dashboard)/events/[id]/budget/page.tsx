"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getBudget, updateBudget, getExportUrl } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";

interface BudgetItem { description: string; quantity: number; unit_cost: number; total: number; }
interface BudgetCategory { name: string; items: BudgetItem[]; subtotal: number; }

export default function BudgetEditorPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const eventId = params.id as string;

  const [categories, setCategories] = useState<BudgetCategory[]>([]);
  const [contingency, setContingency] = useState(10);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [totalAmount, setTotalAmount] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getBudget(eventId)
      .then((data: Record<string, unknown>) => {
        setCategories(data.categories as BudgetCategory[] || []);
        setContingency((data as Record<string, unknown>).contingency_percent as number || 10);
        setWarnings(data.warnings as string[] || []);
        setTotalAmount(data.total_amount as Record<string, number> || {});
      })
      .catch(() => toast("No budget found — generate the event package first", "error"))
      .finally(() => setLoading(false));
  }, [eventId, toast]);

  const recalc = (cats: BudgetCategory[]) => {
    const updated = cats.map((cat) => ({
      ...cat,
      items: cat.items.map((item) => ({ ...item, total: item.quantity * item.unit_cost })),
      subtotal: cat.items.reduce((s, i) => s + i.quantity * i.unit_cost, 0),
    }));
    setCategories(updated);
  };

  const updateItem = (catIdx: number, itemIdx: number, field: keyof BudgetItem, value: string | number) => {
    const updated = [...categories];
    const item = { ...updated[catIdx].items[itemIdx] };
    if (field === "description") item.description = value as string;
    else item[field] = Number(value) || 0;
    item.total = item.quantity * item.unit_cost;
    updated[catIdx] = {
      ...updated[catIdx],
      items: updated[catIdx].items.map((it, i) => i === itemIdx ? item : it),
    };
    updated[catIdx].subtotal = updated[catIdx].items.reduce((s, i) => i === updated[catIdx].items[itemIdx] ? item.total + s - i.total + i.total : s + i.total, 0);
    recalc(updated);
  };

  const addItem = (catIdx: number) => {
    const updated = [...categories];
    updated[catIdx] = {
      ...updated[catIdx],
      items: [...updated[catIdx].items, { description: "", quantity: 1, unit_cost: 0, total: 0 }],
    };
    setCategories(updated);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const result = await updateBudget(eventId, { categories, contingency_percent: contingency });
      setTotalAmount(result.total_amount as Record<string, number> || {});
      setWarnings(result.warnings as string[] || []);
      toast("Budget saved!", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Save failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const subtotal = categories.reduce((s, c) => s + c.subtotal, 0);
  const contingencyAmt = subtotal * (contingency / 100);
  const grandTotal = subtotal + contingencyAmt;

  if (loading) {
    return <div className="flex items-center justify-center py-20"><div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" /></div>;
  }

  return (
    <div className="animate-slide-up max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Budget Editor</h1>
          <p className="text-sm text-slate-500">Edit line items — totals auto-calculate</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => window.open(getExportUrl(eventId, "budget/xlsx"))}>
            Export XLSX
          </Button>
          <Button onClick={handleSave} loading={saving}>Save</Button>
          <Button variant="ghost" onClick={() => router.push(`/events/${eventId}`)}>Back</Button>
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-md text-sm mb-4">
          {warnings.map((w, i) => <p key={i}>{w}</p>)}
        </div>
      )}

      {categories.map((cat, ci) => (
        <Card key={ci} className="mb-4">
          <CardHeader>
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">{cat.name}</h2>
              <span className="text-sm font-medium text-slate-600">PKR {cat.subtotal.toLocaleString()}</span>
            </div>
          </CardHeader>
          <CardBody>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b">
                  <th className="pb-2 font-medium">Description</th>
                  <th className="pb-2 font-medium w-20 text-right">Qty</th>
                  <th className="pb-2 font-medium w-32 text-right">Unit Cost</th>
                  <th className="pb-2 font-medium w-32 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {cat.items.map((item, ii) => (
                  <tr key={ii} className="border-b border-slate-100">
                    <td className="py-2">
                      <input value={item.description} onChange={(e) => updateItem(ci, ii, "description", e.target.value)}
                        className="w-full border border-slate-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                    </td>
                    <td className="py-2 text-right">
                      <input type="number" value={item.quantity} onChange={(e) => updateItem(ci, ii, "quantity", e.target.value)}
                        className="w-16 border border-slate-200 rounded px-2 py-1 text-sm text-right focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                    </td>
                    <td className="py-2 text-right">
                      <input type="number" value={item.unit_cost} onChange={(e) => updateItem(ci, ii, "unit_cost", e.target.value)}
                        className="w-28 border border-slate-200 rounded px-2 py-1 text-sm text-right focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                    </td>
                    <td className="py-2 text-right font-medium text-slate-700">
                      PKR {(item.quantity * item.unit_cost).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button onClick={() => addItem(ci)} className="text-xs text-indigo-600 hover:text-indigo-700 mt-2">
              + Add line item
            </button>
          </CardBody>
        </Card>
      ))}

      {/* Totals */}
      <Card>
        <CardBody>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-slate-600">Subtotal</span><span className="font-medium">PKR {subtotal.toLocaleString()}</span></div>
            <div className="flex justify-between items-center">
              <span className="text-slate-600">Contingency</span>
              <div className="flex items-center gap-2">
                <input type="number" value={contingency} onChange={(e) => setContingency(Number(e.target.value) || 0)}
                  className="w-16 border border-slate-200 rounded px-2 py-1 text-sm text-right focus:outline-none focus:ring-1 focus:ring-indigo-500" />
                <span className="text-slate-400">%</span>
                <span className="font-medium">PKR {contingencyAmt.toLocaleString()}</span>
              </div>
            </div>
            <div className="flex justify-between pt-2 border-t border-slate-200">
              <span className="font-bold text-slate-900">Grand Total</span>
              <span className="font-bold text-lg text-indigo-600">PKR {grandTotal.toLocaleString()}</span>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
