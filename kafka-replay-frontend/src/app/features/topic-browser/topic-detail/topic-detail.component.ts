import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { ApiService } from '@core/services/api.service';
import { TopicStore } from '@core/store/topic.store';
import { LoadingSpinnerComponent } from '@shared/components/loading-spinner/loading-spinner.component';
import { TopicMetadata } from '@core/models/topic.model';

/**
 * Topic detail component
 * Displays detailed information about a Kafka topic
 */
@Component({
  selector: 'app-topic-detail',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    RouterModule,
    LoadingSpinnerComponent,
  ],
  template: `
    <div class="topic-detail-container">
      <div class="header">
        <button mat-icon-button routerLink="/topics">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <h2>{{ topicStore.selectedTopicName() || 'Topic Details' }}</h2>
      </div>

      <app-loading-spinner [isLoading]="topicStore.loading()" message="Loading topic details..."></app-loading-spinner>

      <div *ngIf="!topicStore.loading() && topicStore.selectedTopic()" class="topic-info">
        <mat-card>
          <mat-card-header>
            <mat-card-title>Topic Information</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Partitions:</span>
                <span class="value">{{ topicStore.selectedTopicPartitionCount() }}</span>
              </div>
              <div class="info-item">
                <span class="label">Replication Factor:</span>
                <span class="value">{{ topicStore.selectedTopic()?.replication_factor }}</span>
              </div>
              <div class="info-item">
                <span class="label">Message Count:</span>
                <span class="value">{{ topicStore.selectedTopic()?.message_count | number }}</span>
              </div>
              <div class="info-item">
                <span class="label">Size (bytes):</span>
                <span class="value">{{ topicStore.selectedTopic()?.size_bytes | number }}</span>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="partitions-card">
          <mat-card-header>
            <mat-card-title>Partitions</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <table mat-table [dataSource]="topicStore.selectedTopic()?.partitions || []" class="partitions-table">
              <ng-container matColumnDef="partition_id">
                <th mat-header-cell *matHeaderCellDef>Partition</th>
                <td mat-cell *matCellDef="let element">{{ element.partition_id }}</td>
              </ng-container>

              <ng-container matColumnDef="leader">
                <th mat-header-cell *matHeaderCellDef>Leader</th>
                <td mat-cell *matCellDef="let element">{{ element.leader }}</td>
              </ng-container>

              <ng-container matColumnDef="replicas">
                <th mat-header-cell *matHeaderCellDef>Replicas</th>
                <td mat-cell *matCellDef="let element">{{ element.replicas.join(', ') }}</td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="['partition_id', 'leader', 'replicas']"></tr>
              <tr mat-row *matRowDef="let row; columns: ['partition_id', 'leader', 'replicas']"></tr>
            </table>
          </mat-card-content>
        </mat-card>
      </div>

      <div *ngIf="topicStore.error()" class="error-message">
        {{ topicStore.error() }}
      </div>
    </div>
  `,
  styles: [
    `
      .topic-detail-container {
        padding: 16px;
      }

      .header {
        display: flex;
        align-items: center;
        gap: 16px;
        margin-bottom: 24px;
      }

      .header h2 {
        margin: 0;
      }

      .topic-info {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
      }

      .info-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .label {
        font-weight: 500;
        color: #666;
        font-size: 12px;
      }

      .value {
        font-size: 16px;
        font-weight: 500;
      }

      .partitions-card {
        margin-top: 16px;
      }

      .partitions-table {
        width: 100%;
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
export class TopicDetailComponent implements OnInit {
  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    public topicStore: TopicStore
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params) => {
      const topicName = params['name'];
      if (topicName) {
        this.loadTopicDetails(topicName);
      }
    });
  }

  loadTopicDetails(topicName: string): void {
    this.topicStore.setLoading(true);
    this.topicStore.setError(null);

    this.api.getTopicMetadata(topicName).subscribe({
      next: (metadata: TopicMetadata) => {
        this.topicStore.setSelectedTopic(metadata);
        this.topicStore.setLoading(false);
      },
      error: (error) => {
        this.topicStore.setError('Failed to load topic details');
        this.topicStore.setLoading(false);
        console.error('Error loading topic details:', error);
      },
    });
  }
}
