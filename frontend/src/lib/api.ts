/** Typed HTTP client for the SocietyOS backend API. */

import type {
  ApiSuccess,
  TokenPair,
  User,
  University,
  Society,
  EventRecord,
  ParsedEventData,
  CreateEventPayload,
  PolicyDataRecord,
  QuestionnaireInput,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ---------------------------------------------------------------------------
// Token storage (in-memory — never localStorage for access tokens)
// ---------------------------------------------------------------------------
let accessToken: string | null = null;
let refreshToken: string | null = null;

export function setTokens(tokens: TokenPair) {
  accessToken = tokens.access_token;
  refreshToken = tokens.refresh_token;
  // Persist refresh token only (access token is short-lived)
  if (typeof window !== "undefined") {
    localStorage.setItem("refresh_token", tokens.refresh_token);
  }
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("refresh_token");
  }
}

export function getStoredRefreshToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("refresh_token");
  }
  return null;
}

// ---------------------------------------------------------------------------
// Base fetch wrapper
// ---------------------------------------------------------------------------
async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiSuccess<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const json = await res.json();

  if (!res.ok || !json.success) {
    let msg = json.error?.message || `Request failed (${res.status})`;
    // Append validation details if present (422 errors from FastAPI)
    if (json.error?.details && Array.isArray(json.error.details)) {
      const fields = json.error.details
        .map((d: { loc?: string[]; msg?: string }) => {
          const field = d.loc?.slice(-1)[0] || "unknown";
          return `${field}: ${d.msg || "invalid"}`;
        })
        .join("; ");
      if (fields) msg += ` (${fields})`;
    }
    throw new Error(msg);
  }

  return json as ApiSuccess<T>;
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------
export async function register(
  email: string,
  password: string,
  fullName: string
): Promise<TokenPair> {
  const res = await apiFetch<TokenPair>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  setTokens(res.data);
  return res.data;
}

export async function login(
  email: string,
  password: string
): Promise<TokenPair> {
  const res = await apiFetch<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setTokens(res.data);
  return res.data;
}

export async function refreshAccessToken(): Promise<TokenPair | null> {
  const rt = refreshToken || getStoredRefreshToken();
  if (!rt) return null;

  try {
    const res = await apiFetch<TokenPair>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: rt }),
    });
    setTokens(res.data);
    return res.data;
  } catch {
    clearTokens();
    return null;
  }
}

export async function getMe(): Promise<User> {
  const res = await apiFetch<User>("/auth/me");
  return res.data;
}

export function logout() {
  clearTokens();
}

// ---------------------------------------------------------------------------
// Universities API
// ---------------------------------------------------------------------------
export async function listUniversities(): Promise<University[]> {
  const res = await apiFetch<University[]>("/universities");
  return res.data;
}

// ---------------------------------------------------------------------------
// Societies API
// ---------------------------------------------------------------------------
export async function createSociety(data: {
  name: string;
  university_id: string;
  department: string;
  society_type: string;
  faculty_advisor_name?: string;
  faculty_advisor_email?: string;
  description?: string;
}): Promise<Society> {
  const res = await apiFetch<Society>("/societies", {
    method: "POST",
    body: JSON.stringify(data),
  });
  return res.data;
}

export async function listMySocieties(): Promise<Society[]> {
  const res = await apiFetch<Society[]>("/societies");
  return res.data;
}

export async function getSociety(id: string): Promise<Society> {
  const res = await apiFetch<Society>(`/societies/${id}`);
  return res.data;
}

export async function updateSociety(
  id: string,
  data: Partial<Society>
): Promise<Society> {
  const res = await apiFetch<Society>(`/societies/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  return res.data;
}

// ---------------------------------------------------------------------------
// Events API
// ---------------------------------------------------------------------------
export async function parseEvent(
  description: string,
  societyId: string
): Promise<ParsedEventData> {
  const res = await apiFetch<ParsedEventData>("/events/parse", {
    method: "POST",
    body: JSON.stringify({ description, society_id: societyId }),
  });
  return res.data;
}

export async function createEvent(data: CreateEventPayload): Promise<EventRecord> {
  const res = await apiFetch<EventRecord>("/events", {
    method: "POST",
    body: JSON.stringify(data),
  });
  return res.data;
}

export async function listEvents(societyId?: string): Promise<EventRecord[]> {
  const qs = societyId ? `?society_id=${societyId}` : "";
  const res = await apiFetch<EventRecord[]>(`/events${qs}`);
  return res.data;
}

export async function getEvent(id: string): Promise<EventRecord> {
  const res = await apiFetch<EventRecord>(`/events/${id}`);
  return res.data;
}

export async function updateEvent(
  id: string,
  data: Partial<EventRecord>
): Promise<EventRecord> {
  const res = await apiFetch<EventRecord>(`/events/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  return res.data;
}

// ---------------------------------------------------------------------------
// Policy API (FR-002)
// ---------------------------------------------------------------------------
export async function uploadPolicy(
  file: File,
  universityId: string,
  mode: "direct" | "prospectus",
  eventId?: string
): Promise<PolicyDataRecord> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("university_id", universityId);
  formData.append("mode", mode);
  if (eventId) formData.append("event_id", eventId);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const res = await fetch(`${API}/policy/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken || ""}` },
    body: formData,
  });
  const json = await res.json();
  if (!res.ok || !json.success) throw new Error(json.error?.message || "Upload failed");
  return json.data as PolicyDataRecord;
}

export async function submitQuestionnaire(data: QuestionnaireInput): Promise<PolicyDataRecord> {
  // Send university_id and event_id as both query params AND in the JSON body
  // to handle all backend versions correctly
  const params = new URLSearchParams();
  if (data.university_id) params.set("university_id", data.university_id);
  if (data.event_id) params.set("event_id", data.event_id);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const res = await apiFetch<PolicyDataRecord>(`/policy/questionnaire${qs}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  return res.data;
}

export async function listPolicies(universityId: string): Promise<PolicyDataRecord[]> {
  const res = await apiFetch<PolicyDataRecord[]>(`/policy/university/${universityId}`);
  return res.data;
}

export async function getPolicy(id: string): Promise<PolicyDataRecord> {
  const res = await apiFetch<PolicyDataRecord>(`/policy/${id}`);
  return res.data;
}

export async function verifyPolicy(
  id: string,
  corrections?: Record<string, unknown>
): Promise<PolicyDataRecord> {
  const res = await apiFetch<PolicyDataRecord>(`/policy/${id}/verify`, {
    method: "PUT",
    body: JSON.stringify(corrections || {}),
  });
  return res.data;
}

// ---------------------------------------------------------------------------
// Generation API (Phase 4 — SSE streaming)
// ---------------------------------------------------------------------------
export interface GenerationUpdate {
  agent: string;
  status: "running" | "complete" | "error";
  message: string;
}

export async function generateAll(
  eventId: string,
  onUpdate: (update: GenerationUpdate) => void
): Promise<void> {
  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const res = await fetch(`${API}/events/${eventId}/generate-all`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken || ""}` },
  });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json.error?.message || "Generation failed");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response stream");
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          onUpdate(JSON.parse(line.slice(6)) as GenerationUpdate);
        } catch { /* skip malformed */ }
      }
    }
  }
}

// Retrieval for generated content
export async function getProposal(eventId: string) {
  return (await apiFetch<Record<string, unknown>>(`/events/${eventId}/proposal`)).data;
}
export async function getBudget(eventId: string) {
  return (await apiFetch<Record<string, unknown>>(`/events/${eventId}/budget`)).data;
}
export async function getSponsorship(eventId: string) {
  return (await apiFetch<Record<string, unknown>>(`/events/${eventId}/sponsorship`)).data;
}
export async function getApprovals(eventId: string) {
  return (await apiFetch<unknown[]>(`/events/${eventId}/approvals`)).data;
}
export async function getTasks(eventId: string) {
  return (await apiFetch<unknown[]>(`/events/${eventId}/tasks`)).data;
}

// Editing endpoints (Phase 5)
export async function updateProposal(eventId: string, sections: Record<string, string>) {
  return (await apiFetch<Record<string, unknown>>(`/events/${eventId}/proposal`, {
    method: "PUT", body: JSON.stringify({ sections }),
  })).data;
}
export async function updateBudget(eventId: string, data: Record<string, unknown>) {
  return (await apiFetch<Record<string, unknown>>(`/events/${eventId}/budget`, {
    method: "PUT", body: JSON.stringify(data),
  })).data;
}
export async function updateSponsorship(eventId: string, data: Record<string, unknown>) {
  return (await apiFetch<Record<string, unknown>>(`/events/${eventId}/sponsorship`, {
    method: "PUT", body: JSON.stringify(data),
  })).data;
}

// Export URLs (open in new tab)
export function getExportUrl(eventId: string, type: "proposal/pdf" | "proposal/docx" | "budget/xlsx" | "sponsorship/pdf") {
  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  return `${API}/exports/${eventId}/${type}`;
}

// ---------------------------------------------------------------------------
// Phase 7 — Institutional Memory & Learning
// ---------------------------------------------------------------------------

// Post-event outcomes
export async function submitOutcome(eventId: string, data: Record<string, unknown>) {
  return (await apiFetch<Record<string, unknown>>(`/memory/events/${eventId}/outcome`, {
    method: "POST", body: JSON.stringify(data),
  })).data;
}

export async function getOutcome(eventId: string) {
  return (await apiFetch<Record<string, unknown>>(`/memory/events/${eventId}/outcome`)).data;
}

export async function updateOutcome(eventId: string, data: Record<string, unknown>) {
  return (await apiFetch<Record<string, unknown>>(`/memory/events/${eventId}/outcome`, {
    method: "PUT", body: JSON.stringify(data),
  })).data;
}

export async function verifyOutcome(eventId: string) {
  return (await apiFetch<Record<string, unknown>>(`/memory/events/${eventId}/outcome/verify`, {
    method: "PUT",
  })).data;
}

// Historical insights
export async function getEventInsights(eventId: string) {
  return (await apiFetch<Record<string, unknown>>(`/memory/events/${eventId}/insights`)).data;
}

// University memories
export async function getUniversityMemories(universityId: string, params?: { event_type?: string; status?: string; limit?: number; offset?: number }) {
  const query = new URLSearchParams();
  if (params?.event_type) query.set("event_type", params.event_type);
  if (params?.status) query.set("status", params.status);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const qs = query.toString();
  return (await apiFetch<Record<string, unknown>>(`/memory/university/${universityId}/memories${qs ? `?${qs}` : ""}`)).data;
}

export async function updateMemory(memoryId: string, data: Record<string, unknown>) {
  return (await apiFetch<Record<string, unknown>>(`/memory/memories/${memoryId}`, {
    method: "PUT", body: JSON.stringify(data),
  })).data;
}

export async function getUniversityOutcomes(universityId: string, params?: { limit?: number; offset?: number }) {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const qs = query.toString();
  return (await apiFetch<Record<string, unknown>>(`/memory/university/${universityId}/outcomes${qs ? `?${qs}` : ""}`)).data;
}
