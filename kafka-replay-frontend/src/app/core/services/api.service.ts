import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '@environments/environment';
import {
  CreateReplayJobRequest,
  ReplayJobResponse,
  ReplayJobListResponse,
  UpdateReplayJobRequest,
} from '../models/replay.model';
import { TopicListResponse, TopicMetadata } from '../models/topic.model';

/**
 * HTTP API client for backend communication
 * Provides typed methods for all API endpoints
 */
@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly apiUrl = `${environment.apiUrl}/${environment.apiVersion}`;

  constructor(private http: HttpClient) {}

  // ============= Replay Jobs =============

  /**
   * Create a new replay job
   */
  createReplayJob(request: CreateReplayJobRequest): Observable<ReplayJobResponse> {
    return this.http.post<ReplayJobResponse>(`${this.apiUrl}/replays`, request);
  }

  /**
   * Get a specific replay job
   */
  getReplayJob(jobId: string): Observable<ReplayJobResponse> {
    return this.http.get<ReplayJobResponse>(`${this.apiUrl}/replays/${jobId}`);
  }

  /**
   * List all replay jobs with pagination
   */
  listReplayJobs(skip: number = 0, limit: number = 10): Observable<ReplayJobListResponse> {
    const params = new HttpParams().set('skip', skip).set('limit', limit);
    return this.http.get<ReplayJobListResponse>(`${this.apiUrl}/replays`, { params });
  }

  /**
   * Update a replay job
   */
  updateReplayJob(jobId: string, request: UpdateReplayJobRequest): Observable<ReplayJobResponse> {
    return this.http.patch<ReplayJobResponse>(`${this.apiUrl}/replays/${jobId}`, request);
  }

  /**
   * Delete a replay job
   */
  deleteReplayJob(jobId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/replays/${jobId}`);
  }

  // ============= Topics =============

  /**
   * List all available Kafka topics
   */
  listTopics(): Observable<TopicListResponse> {
    return this.http.get<TopicListResponse>(`${this.apiUrl}/topics`);
  }

  /**
   * Get metadata for a specific topic
   */
  getTopicMetadata(topicName: string): Observable<TopicMetadata> {
    return this.http.get<TopicMetadata>(`${this.apiUrl}/topics/${topicName}`);
  }

  // ============= Health =============

  /**
   * Health check endpoint
   */
  health(): Observable<{ status: string; timestamp: string }> {
    return this.http.get<{ status: string; timestamp: string }>(`${this.apiUrl}/health`);
  }

  /**
   * Readiness check endpoint
   */
  ready(): Observable<{ status: string; timestamp: string }> {
    return this.http.get<{ status: string; timestamp: string }>(`${this.apiUrl}/ready`);
  }
}
