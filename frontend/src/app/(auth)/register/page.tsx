"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/components/ui/Toast";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { register } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      await register(email, password, fullName);
      toast("Account created!", "success");
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="text-center mb-8">
        <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center mx-auto mb-4">
          <span className="text-white font-bold text-lg">S</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
        <p className="text-sm text-slate-500 mt-1">
          Start organizing events smarter
        </p>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Full Name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Ahmed Khan"
            required
          />
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@university.edu.pk"
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Minimum 8 characters"
            required
          />

          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md">
              {error}
            </p>
          )}

          <Button type="submit" loading={loading} className="w-full">
            Create Account
          </Button>
        </form>
      </div>

      <p className="text-center text-sm text-slate-500 mt-4">
        Already have an account?{" "}
        <Link href="/login" className="text-indigo-600 font-medium hover:text-indigo-700">
          Sign in
        </Link>
      </p>
    </div>
  );
}
