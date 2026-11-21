"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getEventInsights } from "@/lib/api";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";

interface Insight {
  source_event: string;
  source_type: string;
  verification: string;
  lessons: string[];
  risk_flags: string[];
  success_factors: string[];
  metrics: Record<string, string | number>;
}

export default function InsightsPage() {
  const params = useParams();
  const router = useRouter();
  const eventId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<{
    insights: Insight[];
    recommendations: string[];
    total_historical_events: number;
  } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const result = await getEventInsights(eventId) as {
          insights: Insight[];
          recommendations: string[];
          total_historical_events: number;
        };
        setData(result);
      } catch {
        // No insights
      }
      setLoading(false);
    })();
  }, [eventId]);

  if (loading) return <div className="p-6">Loading insights...</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Historical Insights</h1>
          <p className="text-gray-500 mt-1">
            Lessons from {data?.total_historical_events || 0} previous events at this university
          </p>
        </div>
        <Button variant="ghost" onClick={() => router.push(`/events/${eventId}`)}>
          ← Back to Event
        </Button>
      </div>

      {/* Recommendations */}
      {data?.recommendations?.length ? (
        <Card>
          <div className="p-4">
            <h2 className="text-lg font-semibold mb-3">Recommendations</h2>
            <div className="space-y-2">
              {data.recommendations.map((rec, i) => (
                <div key={i} className="flex gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <span className="text-blue-600 font-bold shrink-0">💡</span>
                  <span className="text-sm">{rec}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      ) : null}

      {/* Individual Insights */}
      {data?.insights?.length ? (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Source Events</h2>
          {data.insights.map((insight, i) => (
            <Card key={i}>
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h3 className="font-semibold">{insight.source_event}</h3>
                    <span className="text-sm text-gray-500 capitalize">{insight.source_type}</span>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    insight.verification === "verified"
                      ? "bg-green-100 text-green-800"
                      : "bg-yellow-100 text-yellow-800"
                  }`}>
                    {insight.verification}
                  </span>
                </div>

                {/* Metrics */}
                {Object.keys(insight.metrics).length > 0 && (
                  <div className="flex gap-4 mb-3 text-sm">
                    {Object.entries(insight.metrics).map(([key, val]) => (
                      <div key={key} className="bg-gray-50 px-3 py-1 rounded">
                        <span className="text-gray-500">{key.replace(/_/g, " ")}:</span>{" "}
                        <span className="font-medium">{String(val)}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Lessons */}
                {insight.lessons.length > 0 && (
                  <div className="mb-2">
                    <span className="text-sm font-medium text-gray-600">Lessons:</span>
                    <ul className="mt-1 space-y-1">
                      {insight.lessons.map((l, j) => (
                        <li key={j} className="text-sm text-gray-700 pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-gray-400">
                          {l}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Success Factors */}
                {insight.success_factors.length > 0 && (
                  <div className="mb-2">
                    <span className="text-sm font-medium text-green-600">What worked:</span>
                    <ul className="mt-1 space-y-1">
                      {insight.success_factors.map((f, j) => (
                        <li key={j} className="text-sm text-green-700 pl-4 relative before:content-['✓'] before:absolute before:left-0">
                          {f}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Risk Flags */}
                {insight.risk_flags.length > 0 && (
                  <div>
                    <span className="text-sm font-medium text-red-600">Watch out:</span>
                    <ul className="mt-1 space-y-1">
                      {insight.risk_flags.map((f, j) => (
                        <li key={j} className="text-sm text-red-700 pl-4 relative before:content-['⚠'] before:absolute before:left-0">
                          {f}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <div className="p-8 text-center text-gray-500">
            <p className="text-lg mb-2">No historical data yet</p>
            <p className="text-sm">
              As events are completed and outcomes recorded, the AI will learn from past experiences
              to improve future event planning.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
