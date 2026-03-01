/**
 * Replay job models matching backend Pydantic schemas
 */

export enum ReplayJobStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELLED = 'CANCELLED',
}

export interface ReplayJobFilter {
  key?: string;
  value?: string;
  operator?: 'equals' | 'contains' | 'regex';
}

export interface CreateReplayJobRequest {
  name: string;
  source_topic: string;
  target_topic: string;
  filters?: ReplayJobFilter[];
  enrichment_script?: string;
  batch_size?: number;
  dry_run?: boolean;
}

export interface UpdateReplayJobRequest {
  name?: string;
  filters?: ReplayJobFilter[];
  enrichment_script?: string;
  batch_size?: number;
}

export interface ReplayJobStatistics {
  messages_processed: number;
  messages_failed: number;
  messages_skipped: number;
  average_latency_ms: number;
  throughput_msg_per_sec: number;
}

export interface ReplayJobProgress {
  current_offset: number;
  total_offsets: number;
  percentage: number;
  estimated_time_remaining_sec?: number;
}

export interface ReplayJobResponse {
  job_id: string;
  name: string;
  source_topic: string;
  target_topic: string;
  status: ReplayJobStatus;
  filters?: ReplayJobFilter[];
  enrichment_script?: string;
  batch_size: number;
  dry_run: boolean;
  progress?: ReplayJobProgress;
  statistics?: ReplayJobStatistics;
  error_message?: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ReplayJobListResponse {
  items: ReplayJobResponse[];
  total: number;
  skip: number;
  limit: number;
}
