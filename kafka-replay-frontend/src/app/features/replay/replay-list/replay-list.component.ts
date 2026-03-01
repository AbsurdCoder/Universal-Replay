import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { RouterModule } from '@angular/router';
import { ApiService } from '@core/services/api.service';
import { ReplayStore } from '@core/store/replay.store';
import { LoadingSpinnerComponent, StatusBadgeComponent } from '@shared/index';
import { DateFormatPipe, TruncatePipe } from '@shared/index';

/**
 * Replay job list component
 * Displays list of replay jobs with pagination
 */
@Component({
  selector: 'app-replay-list',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatPaginatorModule,
    RouterModule,
    LoadingSpinnerComponent,
    StatusBadgeComponent,
    DateFormatPipe,
    TruncatePipe,
  ],
  template: `
    <div class="replay-list-container">
      <div class="header">
        <h2>Replay Jobs</h2>
        <button mat-raised-button color="primary" routerLink="/replays/new">
          <mat-icon>add</mat-icon>
          New Job
        </button>
      </div>

      <app-loading-spinner [isLoading]="replayStore.loading()" message="Loading replay jobs..."></app-loading-spinner>

      <div *ngIf="!replayStore.loading() && replayStore.hasJobs()" class="jobs-table">
        <table mat-table [dataSource]="replayStore.jobs()" class="replay-table">
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Job Name</th>
            <td mat-cell *matCellDef="let element">{{ element.name | appTruncate: 30 }}</td>
          </ng-container>

          <ng-container matColumnDef="source_topic">
            <th mat-header-cell *matHeaderCellDef>Source Topic</th>
            <td mat-cell *matCellDef="let element">{{ element.source_topic }}</td>
          </ng-container>

          <ng-container matColumnDef="target_topic">
            <th mat-header-cell *matHeaderCellDef>Target Topic</th>
            <td mat-cell *matCellDef="let element">{{ element.target_topic }}</td>
          </ng-container>

          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let element">
              <app-status-badge [status]="element.status"></app-status-badge>
            </td>
          </ng-container>

          <ng-container matColumnDef="created_at">
            <th mat-header-cell *matHeaderCellDef>Created</th>
            <td mat-cell *matCellDef="let element">{{ element.created_at | appDateFormat: 'short' }}</td>
          </ng-container>

          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef>Actions</th>
            <td mat-cell *matCellDef="let element">
              <button mat-icon-button [routerLink]="['/replays', element.job_id]" matTooltip="View Details">
                <mat-icon>visibility</mat-icon>
              </button>
              <button mat-icon-button (click)="deleteJob(element.job_id)" matTooltip="Delete">
                <mat-icon>delete</mat-icon>
              </button>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
        </table>

        <mat-paginator
          [length]="replayStore.pagination().total"
          [pageSize]="replayStore.pagination().limit"
          [pageSizeOptions]="[5, 10, 25, 100]"
          (page)="onPageChange($event)"
        ></mat-paginator>
      </div>

      <div *ngIf="!replayStore.loading() && !replayStore.hasJobs()" class="empty-state">
        <mat-icon class="empty-icon">inbox</mat-icon>
        <p>No replay jobs yet</p>
        <button mat-raised-button color="primary" routerLink="/replays/new">
          Create First Job
        </button>
      </div>

      <div *ngIf="replayStore.error()" class="error-message">
        {{ replayStore.error() }}
      </div>
    </div>
  `,
  styles: [
    `
      .replay-list-container {
        padding: 16px;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
      }

      .header h2 {
        margin: 0;
      }

      .jobs-table {
        background: white;
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }

      .replay-table {
        width: 100%;
      }

      .empty-state {
        text-align: center;
        padding: 48px 16px;
        color: #999;
      }

      .empty-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: #ccc;
      }

      .error-message {
        padding: 16px;
        background-color: #ffebee;
        color: #c62828;
        border-radius: 4px;
      }
    `,
  ],
})
export class ReplayListComponent implements OnInit {
  displayedColumns: string[] = ['name', 'source_topic', 'target_topic', 'status', 'created_at', 'actions'];

  constructor(
    private api: ApiService,
    public replayStore: ReplayStore
  ) {}

  ngOnInit(): void {
    this.loadJobs();
  }

  loadJobs(skip: number = 0, limit: number = 10): void {
    this.replayStore.setLoading(true);
    this.replayStore.setError(null);

    this.api.listReplayJobs(skip, limit).subscribe({
      next: (response) => {
        this.replayStore.setJobs(response.items);
        this.replayStore.setPagination(skip, limit, response.total);
        this.replayStore.setLoading(false);
      },
      error: (error) => {
        this.replayStore.setError('Failed to load replay jobs');
        this.replayStore.setLoading(false);
        console.error('Error loading jobs:', error);
      },
    });
  }

  onPageChange(event: PageEvent): void {
    this.loadJobs(event.pageIndex * event.pageSize, event.pageSize);
  }

  deleteJob(jobId: string): void {
    if (confirm('Are you sure you want to delete this job?')) {
      this.api.deleteReplayJob(jobId).subscribe({
        next: () => {
          this.replayStore.removeJob(jobId);
        },
        error: (error) => {
          this.replayStore.setError('Failed to delete job');
          console.error('Error deleting job:', error);
        },
      });
    }
  }
}
