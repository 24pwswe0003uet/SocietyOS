"use client";

import { useAuth } from "@/hooks/useAuth";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="animate-slide-up max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 mt-1">Manage your account</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-slate-900">Profile</h2>
        </CardHeader>
        <CardBody className="space-y-3">
          <div>
            <p className="text-sm text-slate-500">Full Name</p>
            <p className="text-slate-900">{user?.full_name}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Email</p>
            <p className="text-slate-900">{user?.email}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Role</p>
            <p className="text-slate-900">
              {user?.is_university_admin ? "University Administrator" : "Society Member"}
            </p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
