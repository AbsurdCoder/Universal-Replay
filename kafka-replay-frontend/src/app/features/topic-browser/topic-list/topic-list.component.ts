import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';
import { ApiService } from '@core/services/api.service';
import { TopicStore } from '@core/store/topic.store';
import { LoadingSpinnerComponent } from '@shared/components/loading-spinner/loading-spinner.component';

/**
 * Topic browser list component
 * Displays list of available Kafka topics
 */
@Component({
  selector: 'app-topic-list',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    RouterModule,
    LoadingSpinnerComponent,
  ],
  template: `
    <div class="topic-list-container">
      <div class="header">
        <h2>Kafka Topics</h2>
        <button mat-raised-button color="primary" (click)="refreshTopics()">
          <mat-icon>refresh</mat-icon>
          Refresh
        </button>
      </div>

      <app-loading-spinner [isLoading]="topicStore.loading()" message="Loading topics..."></app-loading-spinner>

      <div *ngIf="!topicStore.loading() && topicStore.hasTopics()" class="topics-grid">
        <div *ngFor="let topic of topicStore.topics()" class="topic-card" [routerLink]="['/topics', topic]">
          <div class="topic-name">{{ topic }}</div>
          <mat-icon class="topic-icon">topic</mat-icon>
        </div>
      </div>

      <div *ngIf="!topicStore.loading() && !topicStore.hasTopics()" class="empty-state">
        <mat-icon class="empty-icon">inbox</mat-icon>
        <p>No topics available</p>
      </div>

      <div *ngIf="topicStore.error()" class="error-message">
        {{ topicStore.error() }}
      </div>
    </div>
  `,
  styles: [
    `
      .topic-list-container {
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

      .topics-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 16px;
      }

      .topic-card {
        padding: 16px;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .topic-card:hover {
        background-color: #f5f5f5;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }

      .topic-name {
        font-weight: 500;
      }

      .topic-icon {
        color: #1976d2;
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
export class TopicListComponent implements OnInit {
  constructor(
    private api: ApiService,
    public topicStore: TopicStore
  ) {}

  ngOnInit(): void {
    this.loadTopics();
  }

  loadTopics(): void {
    this.topicStore.setLoading(true);
    this.topicStore.setError(null);

    this.api.listTopics().subscribe({
      next: (response) => {
        this.topicStore.setTopics(response.topics);
        this.topicStore.setLoading(false);
      },
      error: (error) => {
        this.topicStore.setError('Failed to load topics');
        this.topicStore.setLoading(false);
        console.error('Error loading topics:', error);
      },
    });
  }

  refreshTopics(): void {
    this.loadTopics();
  }
}
