"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listMySocieties, parseEvent, createEvent } from "@/lib/api";
import type { Society, ParsedEventData, EventType } from "@/types";
import { useToast } from "@/components/ui/Toast";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

const EVENT_TYPES: { value: EventType; label: string }[] = [
  { value: "hackathon", label: "Hackathon" },
  { value: "workshop", label: "Workshop" },
  { value: "conference", label: "Conference" },
  { value: "seminar", label: "Seminar" },
  { value: "competition", label: "Competition" },
  { value: "speaker", label: "Speaker Event" },
  { value: "other", label: "Other" },
];

type Step = "input" | "review";

export default function NewEventPage() {
  const router = useRouter();
  const { toast } = useToast();

  // Step state
  const [step, setStep] = useState<Step>("input");

  // Data
  const [societies, setSocieties] = useState<Society[]>([]);
  const [selectedSociety, setSelectedSociety] = useState("");
  const [nlInput, setNlInput] = useState("");
  const [parsing, setParsing] = useState(false);
  const [creating, setCreating] = useState(false);

  // Review fields (editable after AI extraction)
  const [title, setTitle] = useState("");
  const [eventType, setEventType] = useState<EventType>("other");
  const [description, setDescription] = useState("");
  const [audienceSize, setAudienceSize] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [durationDays, setDurationDays] = useState("1");
  const [venueType, setVenueType] = useState("");
  const [budgetTarget, setBudgetTarget] = useState("");
  const [currency, setCurrency] = useState("PKR");
  const [clarification, setClarification] = useState<string | null>(null);

  useEffect(() => {
    listMySocieties().then((s) => {
      setSocieties(s);
      if (s.length === 1) setSelectedSociety(s[0].id);
    });
  }, []);

  const handleParse = async () => {
    if (!selectedSociety) {
      toast("Please select a society first", "error");
      return;
    }
    if (nlInput.trim().length < 10) {
      toast("Please describe your event in more detail", "error");
      return;
    }

    setParsing(true);
    setClarification(null);
    try {
      const parsed: ParsedEventData = await parseEvent(nlInput, selectedSociety);

      // Populate review fields
      if (parsed.title) setTitle(parsed.title);
      if (parsed.event_type) setEventType(parsed.event_type);
      if (parsed.description) setDescription(parsed.description);
      if (parsed.audience_size) setAudienceSize(String(parsed.audience_size));
      if (parsed.event_date) setEventDate(parsed.event_date);
      if (parsed.duration_days) setDurationDays(String(parsed.duration_days));
      if (parsed.venue_type) setVenueType(parsed.venue_type);
      if (parsed.budget_target) setBudgetTarget(String(parsed.budget_target));
      if (parsed.currency) setCurrency(parsed.currency);
      if (parsed.clarification_needed) setClarification(parsed.clarification_needed);

      setStep("review");
      toast("Event details extracted! Review and edit below.", "success");
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to parse event", "error");
    } finally {
      setParsing(false);
    }
  };

  const handleCreate = async (asDraft: boolean = true) => {
    if (!title.trim()) {
      toast("Event title is required", "error");
      return;
    }

    setCreating(true);
    try {
      const event = await createEvent({
        society_id: selectedSociety,
        title,
        event_type: eventType,
        description: description || undefined,
        audience_size: audienceSize ? Number(audienceSize) : undefined,
        event_date: eventDate || undefined,
        duration_days: Number(durationDays) || 1,
        venue_type: venueType || undefined,
        budget_target: budgetTarget ? Number(budgetTarget) : undefined,
        currency,
        status: asDraft ? "draft" : "review",
      });
      toast("Event created!", "success");
      router.push(`/events/${event.id}`);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to create event", "error");
    } finally {
      setCreating(false);
    }
  };

  const handleSkipAI = () => {
    setStep("review");
  };

  return (
    <div className="animate-slide-up max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Create New Event</h1>
        <p className="text-slate-500 mt-1">
          {step === "input"
            ? "Describe your event in natural language and let AI extract the details"
            : "Review and edit the extracted event details"}
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-4 mb-6">
        <div className={`flex items-center gap-2 text-sm font-medium ${step === "input" ? "text-indigo-700" : "text-slate-400"}`}>
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step === "input" ? "bg-indigo-600 text-white" : "bg-slate-200 text-slate-500"}`}>
            1
          </span>
          Describe
        </div>
        <div className="w-8 h-px bg-slate-300" />
        <div className={`flex items-center gap-2 text-sm font-medium ${step === "review" ? "text-indigo-700" : "text-slate-400"}`}>
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step === "review" ? "bg-indigo-600 text-white" : "bg-slate-200 text-slate-500"}`}>
            2
          </span>
          Review &amp; Create
        </div>
      </div>

      {/* STEP 1: Natural Language Input */}
      {step === "input" && (
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-slate-900">Describe Your Event</h2>
          </CardHeader>
          <CardBody className="space-y-4">
            {/* Society selector */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Society
              </label>
              <select
                value={selectedSociety}
                onChange={(e) => setSelectedSociety(e.target.value)}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required
              >
                <option value="">Select your society...</option>
                {societies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* NL text area */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Event Description
              </label>
              <textarea
                value={nlInput}
                onChange={(e) => setNlInput(e.target.value)}
                placeholder='Example: "Organize a 200-person AI Hackathon next month with a PKR 500,000 budget. We need a large auditorium with WiFi and projectors."'
                rows={5}
                className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              />
              <p className="text-xs text-slate-400 mt-1">
                Include event type, size, date, budget, venue needs — AI will extract the rest
              </p>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                onClick={handleSkipAI}
                className="text-sm text-slate-500 hover:text-slate-700"
              >
                Skip AI — fill manually
              </button>
              <Button onClick={handleParse} loading={parsing} disabled={!selectedSociety}>
                {parsing ? "AI is extracting..." : "Extract with AI"}
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* STEP 2: Review & Edit */}
      {step === "review" && (
        <>
          {/* Clarification warning */}
          {clarification && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-md text-sm mb-4">
              <strong>AI Note:</strong> {clarification}
            </div>
          )}

          <Card className="mb-4">
            <CardHeader>
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-slate-900">Event Details</h2>
                <button
                  onClick={() => setStep("input")}
                  className="text-sm text-indigo-600 hover:text-indigo-700"
                >
                  ← Back to description
                </button>
              </div>
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <Input
                    label="Event Title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="AI Hackathon 2026"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Event Type
                  </label>
                  <select
                    value={eventType}
                    onChange={(e) => setEventType(e.target.value as EventType)}
                    className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    {EVENT_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
                <Input
                  label="Audience Size"
                  type="number"
                  value={audienceSize}
                  onChange={(e) => setAudienceSize(e.target.value)}
                  placeholder="200"
                />
                <Input
                  label="Event Date"
                  type="date"
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                />
                <Input
                  label="Duration (days)"
                  type="number"
                  value={durationDays}
                  onChange={(e) => setDurationDays(e.target.value)}
                  placeholder="1"
                />
                <Input
                  label="Venue Requirements"
                  value={venueType}
                  onChange={(e) => setVenueType(e.target.value)}
                  placeholder="Auditorium with WiFi"
                />
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Input
                      label="Budget"
                      type="number"
                      value={budgetTarget}
                      onChange={(e) => setBudgetTarget(e.target.value)}
                      placeholder="500000"
                    />
                  </div>
                  <div className="w-24">
                    <Input
                      label="Currency"
                      value={currency}
                      onChange={(e) => setCurrency(e.target.value)}
                    />
                  </div>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                    placeholder="Event description..."
                    className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                  />
                </div>
              </div>
            </CardBody>
          </Card>

          <div className="flex items-center justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => handleCreate(true)}
              loading={creating}
            >
              Save as Draft
            </Button>
            <Button onClick={() => handleCreate(false)} loading={creating}>
              Create Event
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
