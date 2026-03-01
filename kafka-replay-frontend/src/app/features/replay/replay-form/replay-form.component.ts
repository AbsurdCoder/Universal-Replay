import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { Router, RouterModule } from '@angular/router';
import { ApiService } from '@core/services/api.service';
import { ReplayStore } from '@core/store/replay.store';
import { TopicStore } from '@core/store/topic.store';
import { CreateReplayJobRequest } from '@core/models/replay.model';

/**
 * Replay job form component
 * Form for creating new replay jobs
 */
@Component({
  selector: 'app-replay-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatIconModule,
    RouterModule,
  ],
  template: `
    <div class="replay-form-container">
      <div class="header">
        <button mat-icon-button routerLink="/replays">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <h2>Create Replay Job</h2>
      </div>

      <mat-card>
        <mat-card-content>
          <form [formGroup]="form" (ngSubmit)="onSubmit()">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Job Name</mat-label>
              <input matInput formControlName="name" placeholder="Enter job name" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Source Topic</mat-label>
              <mat-select formControlName="source_topic">
                <mat-option *ngFor="let topic of topicStore.topics()" [value]="topic">
                  {{ topic }}
                </mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Target Topic</mat-label>
              <input matInput formControlName="target_topic" placeholder="Enter target topic name" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Batch Size</mat-label>
              <input matInput type="number" formControlName="batch_size" placeholder="Default: 100" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Enrichment Script (Optional)</mat-label>
              <input matInput formControlName="enrichment_script" placeholder="Script name" />
            </mat-form-field>

            <div class="checkbox-group">
              <mat-checkbox formControlName="dry_run">Dry Run (validate without replaying)</mat-checkbox>
            </div>

            <div class="form-actions">
              <button mat-raised-button color="primary" type="submit" [disabled]="!form.valid || isSubmitting">
                <mat-icon *ngIf="!isSubmitting">check</mat-icon>
                <mat-icon *ngIf="isSubmitting">hourglass_empty</mat-icon>
                {{ isSubmitting ? 'Creating...' : 'Create Job' }}
              </button>
              <button mat-button type="button" routerLink="/replays">Cancel</button>
            </div>
          </form>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .replay-form-container {
        padding: 16px;
        max-width: 600px;
        margin: 0 auto;
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

      .full-width {
        width: 100%;
        margin-bottom: 16px;
      }

      .checkbox-group {
        margin: 16px 0;
      }

      .form-actions {
        display: flex;
        gap: 8px;
        margin-top: 24px;
      }

      mat-card {
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }
    `,
  ],
})
export class ReplayFormComponent implements OnInit {
  form: FormGroup;
  isSubmitting = false;

  constructor(
    private fb: FormBuilder,
    private api: ApiService,
    private router: Router,
    public replayStore: ReplayStore,
    public topicStore: TopicStore
  ) {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(3)]],
      source_topic: ['', Validators.required],
      target_topic: ['', Validators.required],
      batch_size: [100, [Validators.required, Validators.min(1)]],
      enrichment_script: [''],
      dry_run: [false],
    });
  }

  ngOnInit(): void {
    this.loadTopics();
  }

  loadTopics(): void {
    if (this.topicStore.topics().length === 0) {
      this.topicStore.setLoading(true);
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
  }

  onSubmit(): void {
    if (this.form.invalid) {
      return;
    }

    this.isSubmitting = true;
    const request: CreateReplayJobRequest = this.form.value;

    this.api.createReplayJob(request).subscribe({
      next: (job) => {
        this.replayStore.addJob(job);
        this.isSubmitting = false;
        this.router.navigate(['/replays', job.job_id]);
      },
      error: (error) => {
        this.replayStore.setError('Failed to create replay job');
        this.isSubmitting = false;
        console.error('Error creating job:', error);
      },
    });
  }
}
