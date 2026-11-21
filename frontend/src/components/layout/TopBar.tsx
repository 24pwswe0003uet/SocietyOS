"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";

export default function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
      {/* Mobile logo */}
      <div className="flex items-center gap-2 lg:hidden">
        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">S</span>
        </div>
        <span className="font-semibold text-slate-900">SocietyOS</span>
      </div>

      {/* Page title area (can be enhanced with breadcrumbs later) */}
      <div className="hidden lg:block" />

      {/* User menu */}
      <div className="relative">
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex items-center gap-2 text-sm text-slate-700 hover:text-slate-900"
        >
          <div className="w-8 h-8 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-medium">
            {user?.full_name?.charAt(0) || "U"}
          </div>
          <span className="hidden sm:inline">{user?.full_name || "User"}</span>
        </button>

        {menuOpen && (
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-slate-200 py-1 z-50">
            <div className="px-4 py-2 text-xs text-slate-500 border-b border-slate-100">
              {user?.email}
            </div>
            <button
              onClick={handleLogout}
              className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
