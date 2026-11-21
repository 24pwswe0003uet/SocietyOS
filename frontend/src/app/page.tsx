import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">S</span>
            </div>
            <span className="font-semibold text-slate-900 text-lg">SocietyOS AI</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm font-medium text-slate-600 hover:text-slate-900"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="text-sm font-medium bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <main className="max-w-6xl mx-auto px-6">
        <div className="py-24 text-center">
          <div className="inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 text-sm font-medium px-3 py-1 rounded-full mb-6">
            <span className="w-2 h-2 bg-indigo-500 rounded-full" />
            Powered by AI
          </div>

          <h1 className="text-5xl font-bold text-slate-900 tracking-tight max-w-3xl mx-auto leading-tight">
            Turn an event idea into a complete plan in
            <span className="text-indigo-600"> 2 minutes</span>
          </h1>

          <p className="mt-6 text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
            SocietyOS AI transforms your natural-language event description into a
            submission-ready proposal, budget, compliance checklist, approval timeline,
            sponsorship package, and task board.
          </p>

          <div className="mt-10 flex items-center justify-center gap-4">
            <Link
              href="/register"
              className="bg-indigo-600 text-white px-8 py-3 rounded-md font-medium hover:bg-indigo-700 transition-colors text-base"
            >
              Start Free
            </Link>
            <Link
              href="/login"
              className="border border-slate-300 text-slate-700 px-8 py-3 rounded-md font-medium hover:bg-slate-50 transition-colors text-base"
            >
              Sign In
            </Link>
          </div>
        </div>

        {/* Features grid */}
        <div className="pb-24 grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              title: "Natural Language Input",
              desc: "Describe your event in plain language. AI extracts everything — type, size, budget, dates — and structures it for you.",
            },
            {
              title: "Policy Intelligence",
              desc: "Upload your university prospectus or answer 5 questions. SocietyOS builds your compliance checklist automatically.",
            },
            {
              title: "Complete Event Package",
              desc: "Proposal, budget, sponsorship tiers, approval timeline, and task board — generated in parallel by specialist AI agents.",
            },
            {
              title: "Professional Exports",
              desc: "Download submission-ready PDFs, Word docs, and Excel budgets that match university standards.",
            },
            {
              title: "Live Dashboard",
              desc: "Track approvals, tasks, budget burn, and sponsor pipeline in real-time. Share read-only links with advisors.",
            },
            {
              title: "Institutional Memory",
              desc: "Every completed event teaches the system. Future events get smarter budgets, better timelines, fewer rejections.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="bg-slate-50 rounded-lg p-6 border border-slate-200"
            >
              <h3 className="font-semibold text-slate-900 mb-2">{f.title}</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-8 text-center text-sm text-slate-500">
        SocietyOS AI — The Operating System for Society Events
      </footer>
    </div>
  );
}
