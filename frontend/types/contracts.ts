// Tipos compartidos del contrato de la API (Django REST backend).
// Fuente de verdad: contratos verificados en backend/apps/*/interfaces.

export type UserType = "admin" | "teacher" | "student";

export interface Profile {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  user_type: UserType;
  athlete_id: string | null;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  profile: Profile;
}

export interface AuthPayload {
  email: string;
  password: string;
}

export type VariableName = "posture" | "speed" | "stride" | "cadence";

export interface SeriesPoint {
  t: number;
  value: number;
}

export interface VariableDetail {
  name: string;
  value: number;
}

export interface Variable {
  name: VariableName;
  available: boolean;
  unit: string;
  value: number | null;
  peak?: number | null;
  series?: SeriesPoint[];
  parameter?: string;
  details?: VariableDetail[];
}

export interface SessionSource {
  source_system: string;
  schema_version: string | null;
  observation: string | null;
}

export interface SessionDetail {
  session_id: string;
  athlete_id: string;
  timestamp: string;
  test_type: string;
  source: SessionSource;
  variables: Variable[];
}

export interface SessionListItem {
  session_id: string;
  athlete_id: string;
  timestamp: string;
  test_type: string;
  available_variables: string[];
  source_system: string;
  schema_version: string | null;
}

export interface SessionFilters {
  athlete_id?: string;
  session_id?: string;
  test_type?: string;
  date_from?: string;
  date_to?: string;
}

export interface ComparisonPoint {
  session_id: string;
  available: boolean;
  value: number | null;
}

export interface ComparisonVariable {
  name: VariableName;
  unit: string;
  delta: number | null;
  points: ComparisonPoint[];
}

export interface Comparison {
  sessions: SessionListItem[];
  variables: ComparisonVariable[];
}

export interface Completeness {
  posture: number;
  speed: number;
  stride: number;
  cadence: number;
}

export interface Averages {
  posture: number | null;
  speed: number | null;
  stride: number | null;
  cadence: number | null;
}

export interface DashboardSummary {
  total_sessions: number;
  total_athletes: number;
  completeness: Completeness;
  averages: Averages;
  latest_session: SessionListItem | null;
  scope: string;
}

export interface IngestMetricPayload {
  value?: number;
  unit?: string;
  parameter?: string;
  avg?: number;
  max?: number;
  series?: { t: number; v: number }[];
}

export interface IngestContract {
  session_id: string;
  athlete_id: string;
  timestamp: string;
  test_type: string;
  metrics: {
    posture?: IngestMetricPayload | null;
    speed?: IngestMetricPayload | null;
    stride?: IngestMetricPayload | null;
    cadence?: IngestMetricPayload | null;
  };
  metadata: {
    source_system: string;
    schema_version: string;
    observation?: string;
  };
}

export interface IngestError {
  session_id: string | null;
  field: string;
  message: string;
}

export interface IngestResult {
  accepted: number;
  rejected: number;
  session_ids: string[];
  errors: IngestError[];
}

export type RecommendationStatus = "GENERATED" | "INSUFFICIENT_DATA";
export type ReviewState =
  | "PENDING_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "NOT_REQUIRED";
export type ReviewDecision = "APPROVED" | "REJECTED";

export interface Recommendation {
  recommendation_id: string;
  rule_id: string;
  message: string;
  evidence: string[];
  session_ids: string[];
  status: RecommendationStatus;
  review_state: ReviewState;
  limits: string;
  dataset_version: string;
  model_version: string | null;
  generated_at: string | null;
  reviewed_at: string | null;
  review?: {
    generated_by: number | null;
    reviewed_by: number | null;
    review_note: string | null;
  };
}

export interface DescriptiveStats {
  sessions_analyzed: number;
  athletes: string[];
  completeness: Completeness;
  averages: Averages;
  min_max: Record<string, [number, number] | null>;
}

export interface AnalyticsResult {
  descriptive: DescriptiveStats;
  recommendations: Recommendation[];
  execution_status: string;
  dataset_version: string;
  model_version: string | null;
  evaluation: { status: string; note: string };
  limits: string;
}

export interface Athlete {
  id: number;
  athlete_id: string;
  label: string | null;
  group: string | null;
  registered_at: string;
}
