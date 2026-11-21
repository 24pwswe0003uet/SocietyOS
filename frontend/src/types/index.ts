/** Shared TypeScript types matching backend Pydantic schemas. */

// --- API Envelopes ---
export interface ApiSuccess<T> {
  success: true;
  data: T;
  message: string;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details: string[];
  };
}

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

// --- Auth ---
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_university_admin: boolean;
}

// --- University ---
export interface University {
  id: string;
  name: string;
  city: string;
  country: string;
}

// --- Society ---
export type SocietyType = "technical" | "cultural" | "professional";
export type MemberRole =
  | "president"
  | "admin"
  | "event_organizer"
  | "sponsorship_lead"
  | "faculty_advisor"
  | "member";

export interface ApprovalStep {
  order: number;
  authority: string;
  role: string;
  notes?: string;
}

export interface Society {
  id: string;
  name: string;
  university_id: string;
  department: string;
  society_type: SocietyType;
  faculty_advisor_name: string | null;
  faculty_advisor_email: string | null;
  approval_chain: { steps: ApprovalStep[] } | null;
  description: string | null;
}

// --- Event ---
export type EventType =
  | "hackathon"
  | "workshop"
  | "conference"
  | "seminar"
  | "competition"
  | "speaker"
  | "other";

export type EventStatus =
  | "draft"
  | "generating"
  | "review"
  | "submitted"
  | "approved"
  | "rejected"
  | "completed";

export interface EventRecord {
  id: string;
  society_id: string;
  created_by: string;
  title: string;
  event_type: EventType;
  description: string | null;
  audience_size: number | null;
  event_date: string | null;
  duration_days: number;
  venue_type: string | null;
  budget_target: number | null;
  currency: string;
  status: EventStatus;
}

export interface ParsedEventData {
  title: string | null;
  event_type: EventType | null;
  description: string | null;
  audience_size: number | null;
  event_date: string | null;
  duration_days: number | null;
  venue_type: string | null;
  budget_target: number | null;
  currency: string;
  stakeholder_categories: string[];
  additional_requirements: string[];
  clarification_needed: string | null;
}

export interface CreateEventPayload {
  society_id: string;
  title: string;
  event_type: EventType;
  description?: string;
  audience_size?: number;
  event_date?: string;
  duration_days?: number;
  venue_type?: string;
  budget_target?: number;
  currency?: string;
  status?: EventStatus;
}

// --- Policy (FR-002) ---
export type PolicySourceFormat = "pdf" | "docx" | "url" | "prospectus" | "questionnaire";

export interface PolicyDataRecord {
  id: string;
  university_id: string;
  event_id: string | null;
  source_format: PolicySourceFormat;
  source_filename: string | null;
  source_page_count: number | null;
  source_text_length: number | null;
  approval_chain: { steps: ApprovalStep[] } | null;
  lead_time_days: number | null;
  required_documents: string[] | null;
  sponsorship_rules: string | null;
  prohibitions: string[] | null;
  additional_rules: { rule: string; source: string }[] | null;
  confidence_score: number | null;
  extraction_warnings: string[] | null;
  source_references: { field: string; source: string; excerpt?: string }[] | null;
  is_verified: boolean;
  verified_at: string | null;
  verification_notes: string | null;
  needs_review: boolean;
  extracted_at: string;
}

export interface QuestionnaireInput {
  university_id: string;
  event_id?: string;
  faculty_advisor: string;
  department: string;
  reports_to: "student_affairs" | "academic";
  previous_events: string;
  past_rejections: string;
}
