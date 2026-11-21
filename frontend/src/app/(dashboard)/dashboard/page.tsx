"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { listMySocieties } from "@/lib/api";
import type { Society } from "@/types";
import Card, { CardBody } from "@/components/ui/Card";

export default function DashboardPage() {
  const { user } = useAuth();
  const [societies, setSocieties] = useState<Society[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listMySocieties()
      .then(setSocieties)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="animate-slide-up">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Welcome back, {user?.full_name?.split(" ")[0]}
        </h1>
        <p className="text-slate-500 mt-1">
          Here&apos;s what&apos;s happening with your societies
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardBody>
            <p className="text-sm text-slate-500">My Societies</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">
              {loading ? "—" : societies.length}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-sm text-slate-500">Active Events</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">0</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="text-sm text-slate-500">Pending Approvals</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">0</p>
          </CardBody>
        </Card>
      </div>

      {/* Quick actions */}
      <h2 className="text-lg font-semibold text-slate-900 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {societies.length === 0 ? (
          <Card>
            <CardBody className="text-center py-8">
              <p className="text-slate-500 mb-4">You haven&apos;t joined a society yet.</p>
              <Link
                href="/societies"
                className="inline-flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
              >
                Set Up Your Society
              </Link>
            </CardBody>
          </Card>
        ) : (
          <>
            <Link href="/events">
              <Card className="hover:border-indigo-300 transition-colors cursor-pointer">
                <CardBody className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-indigo-100 text-indigo-700 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Create Event</p>
                    <p className="text-sm text-slate-500">Describe your event in natural language</p>
                  </div>
                </CardBody>
              </Card>
            </Link>
            <Link href="/societies">
              <Card className="hover:border-indigo-300 transition-colors cursor-pointer">
                <CardBody className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-emerald-100 text-emerald-700 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">Manage Societies</p>
                    <p className="text-sm text-slate-500">View and manage your society profiles</p>
                  </div>
                </CardBody>
              </Card>
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
