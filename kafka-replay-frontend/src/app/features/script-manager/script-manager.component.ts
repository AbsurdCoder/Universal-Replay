import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';

/**
 * Script manager component
 * Manages enrichment scripts for replay jobs
 */
@Component({
  selector: 'app-script-manager',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
  template: `
    <div class="script-manager-container">
      <h2>Script Manager</h2>

      <mat-card class="script-form-card">
        <mat-card-header>
          <mat-card-title>Register Enrichment Script</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <form [formGroup]="form" (ngSubmit)="onSubmit()">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Script Name</mat-label>
              <input matInput formControlName="name" placeholder="e.g., add_timestamp" />
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Script Code</mat-label>
              <textarea matInput formControlName="code" placeholder="def enrich(message):" rows="10"></textarea>
            </mat-form-field>

            <div class="form-actions">
              <button mat-raised-button color="primary" type="submit" [disabled]="!form.valid">
                <mat-icon>save</mat-icon>
                Register Script
              </button>
            </div>
          </form>
        </mat-card-content>
      </mat-card>

      <mat-card class="info-card">
        <mat-card-header>
          <mat-card-title>Script Template</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <pre><code>{{ scriptTemplate }}</code></pre>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .script-manager-container {
        padding: 16px;
        max-width: 800px;
        margin: 0 auto;
      }

      .script-form-card,
      .info-card {
        margin-bottom: 16px;
      }

      .full-width {
        width: 100%;
        margin-bottom: 16px;
      }

      .form-actions {
        display: flex;
        gap: 8px;
        margin-top: 16px;
      }

      pre {
        background-color: #f5f5f5;
        padding: 12px;
        border-radius: 4px;
        overflow-x: auto;
      }

      code {
        font-family: 'Courier New', monospace;
        font-size: 12px;
      }
    `,
  ],
})
export class ScriptManagerComponent {
  form: FormGroup;

  scriptTemplate = `def enrich(message):
    """
    Enrichment function template.
    
    Args:
        message: Dictionary containing Kafka message data
        
    Returns:
        Enriched message dictionary
    """
    # Add your enrichment logic here
    message['enriched'] = True
    return message`;

  constructor(private fb: FormBuilder) {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(3)]],
      code: ['', [Validators.required, Validators.minLength(10)]],
    });
  }

  onSubmit(): void {
    if (this.form.invalid) {
      return;
    }

    const formValue = this.form.value;
    console.log('Registering script:', formValue);
    // TODO: Implement script registration via API
  }
}
