"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listEvents } from "@/lib/api";
import type { EventRecord } from "@/types";
import Card, { CardBody } from "@/components/ui/Card";
import Button from "@/components/ui/Button";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700",
  generating: "bg-amber-100 text-amber-700",
  review: "bg-blue-100 text-blue-700",
  submitted: "bg-indigo-100 text-indigo-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-red-100 text-red-700",
  completed: "bg-slate-100 text-slate-700",
};

export default function EventsPage() {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listEvents()
      .then(setEvents)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="animate-slide-up max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Events</h1>
          <p className="text-slate-500 mt-1">Create and manage your society events</p>
        </div>
        <Link href="/events/new">
          <Button>New Event</Button>
        </Link>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full" />
        </div>
      ) : events.length === 0 ? (
        <Card>
          <CardBody className="text-center py-16">
            <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
              </svg>
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">No events yet</h3>
            <p className="text-sm text-slate-500 mb-4">
              Describe your event in natural language and let AI do the rest.
            </p>
            <Link href="/events/new">
              <Button>Create Your First Event</Button>
            </Link>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-3">
          {events.map((event) => (
            <Link key={event.id} href={`/events/${event.id}`}>
              <Card className="hover:border-indigo-300 transition-colors cursor-pointer mb-3">
                <CardBody className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-900">{event.title}</h3>
                    <p className="text-sm text-slate-500">
                      <span className="capitalize">{event.event_type}</span>
                      {event.event_date && ` · ${event.event_date}`}
                      {event.audience_size && ` · ${event.audience_size} attendees`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {event.budget_target && (
                      <span className="text-sm text-slate-600 font-medium">
                        {event.currency} {Number(event.budget_target).toLocaleString()}
                      </span>
                    )}
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[event.status] || ""}`}>
                      {event.status}
                    </span>
                  </div>
                </CardBody>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
