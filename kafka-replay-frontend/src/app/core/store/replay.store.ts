import { Injectable } from '@angular/core';
import { signalStore, withState, withComputed, withMethods, patchState } from '@ngrx/signals';
import { computed } from '@angular/core';
import { ReplayJobResponse, ReplayJobStatus } from '../models/replay.model';

interface ReplayState {
  jobs: ReplayJobResponse[];
  selectedJob: ReplayJobResponse | null;
  loading: boolean;
  error: string | null;
  pagination: {
    skip: number;
    limit: number;
    total: number;
  };
}

const initialState: ReplayState = {
  jobs: [],
  selectedJob: null,
  loading: false,
  error: null,
  pagination: {
    skip: 0,
    limit: 10,
    total: 0,
  },
};

/**
 * Replay job state store using NgRx Signals
 * Manages all replay job related state
 */
@Injectable({
  providedIn: 'root',
})
export class ReplayStore extends signalStore(
  withState(initialState),
  withComputed(({ jobs, selectedJob }) => ({
    jobCount: computed(() => jobs().length),
    hasJobs: computed(() => jobs().length > 0),
    selectedJobStatus: computed(() => selectedJob()?.status),
    pendingJobs: computed(() => jobs().filter((j) => j.status === ReplayJobStatus.PENDING)),
    runningJobs: computed(() => jobs().filter((j) => j.status === ReplayJobStatus.RUNNING)),
    completedJobs: computed(() => jobs().filter((j) => j.status === ReplayJobStatus.COMPLETED)),
    failedJobs: computed(() => jobs().filter((j) => j.status === ReplayJobStatus.FAILED)),
  })),
  withMethods((store) => ({
    setJobs(jobs: ReplayJobResponse[]): void {
      patchState(store, { jobs });
    },

    addJob(job: ReplayJobResponse): void {
      patchState(store, { jobs: [job, ...store.jobs()] });
    },

    updateJob(job: ReplayJobResponse): void {
      const jobs = store.jobs().map((j) => (j.job_id === job.job_id ? job : j));
      patchState(store, { jobs });
    },

    removeJob(jobId: string): void {
      const jobs = store.jobs().filter((j) => j.job_id !== jobId);
      patchState(store, { jobs });
    },

    setSelectedJob(job: ReplayJobResponse | null): void {
      patchState(store, { selectedJob: job });
    },

    setLoading(loading: boolean): void {
      patchState(store, { loading });
    },

    setError(error: string | null): void {
      patchState(store, { error });
    },

    setPagination(skip: number, limit: number, total: number): void {
      patchState(store, {
        pagination: { skip, limit, total },
      });
    },

    clearError(): void {
      patchState(store, { error: null });
    },

    reset(): void {
      patchState(store, initialState);
    },
  }))
) {
  constructor() {
    super();
  }
}
