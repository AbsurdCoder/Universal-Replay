import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';

interface ValidationResult {
  isValid: boolean;
  encoding: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Encoding validator component
 * Validates message encoding and provides conversion utilities
 */
@Component({
  selector: 'app-encoding-validator',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
  ],
  template: `
    <div class="encoding-validator-container">
      <h2>Encoding Validator</h2>

      <mat-card class="validator-card">
        <mat-card-header>
          <mat-card-title>Validate Message Encoding</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <form [formGroup]="form">
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Input Encoding</mat-label>
              <mat-select formControlName="inputEncoding">
                <mat-option value="utf-8">UTF-8</mat-option>
                <mat-option value="utf-16">UTF-16</mat-option>
                <mat-option value="iso-8859-1">ISO-8859-1</mat-option>
                <mat-option value="ascii">ASCII</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Output Encoding</mat-label>
              <mat-select formControlName="outputEncoding">
                <mat-option value="utf-8">UTF-8</mat-option>
                <mat-option value="utf-16">UTF-16</mat-option>
                <mat-option value="iso-8859-1">ISO-8859-1</mat-option>
                <mat-option value="ascii">ASCII</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Message Content</mat-label>
              <textarea matInput formControlName="message" placeholder="Paste message content here" rows="8"></textarea>
            </mat-form-field>

            <div class="form-actions">
              <button mat-raised-button color="primary" type="button" (click)="validate()">
                <mat-icon>check</mat-icon>
                Validate
              </button>
              <button mat-button type="button" (click)="reset()">
                <mat-icon>clear</mat-icon>
                Clear
              </button>
            </div>
          </form>
        </mat-card-content>
      </mat-card>

      <mat-card *ngIf="validationResult" class="result-card" [ngClass]="validationResult.isValid ? 'valid' : 'invalid'">
        <mat-card-header>
          <mat-card-title>
            <mat-icon>{{ validationResult.isValid ? 'check_circle' : 'error' }}</mat-icon>
            {{ validationResult.isValid ? 'Valid' : 'Invalid' }} Encoding
          </mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p>{{ validationResult.message }}</p>
          <div *ngIf="validationResult.details" class="details">
            <div *ngFor="let key of getKeys(validationResult.details)" class="detail-item">
              <span class="detail-label">{{ key }}:</span>
              <span class="detail-value">{{ validationResult.details[key] }}</span>
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [
    `
      .encoding-validator-container {
        padding: 16px;
        max-width: 800px;
        margin: 0 auto;
      }

      .validator-card,
      .result-card {
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

      .result-card {
        margin-top: 24px;
      }

      .result-card.valid {
        border-left: 4px solid #4caf50;
      }

      .result-card.invalid {
        border-left: 4px solid #f44336;
      }

      .details {
        margin-top: 12px;
        padding: 12px;
        background-color: #f5f5f5;
        border-radius: 4px;
      }

      .detail-item {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
      }

      .detail-label {
        font-weight: 500;
        color: #666;
      }

      .detail-value {
        font-family: 'Courier New', monospace;
        font-size: 12px;
      }

      mat-card-title {
        display: flex;
        align-items: center;
        gap: 8px;
      }
    `,
  ],
})
export class EncodingValidatorComponent {
  form: FormGroup;
  validationResult: ValidationResult | null = null;

  constructor(private fb: FormBuilder) {
    this.form = this.fb.group({
      inputEncoding: ['utf-8', Validators.required],
      outputEncoding: ['utf-8', Validators.required],
      message: ['', Validators.required],
    });
  }

  validate(): void {
    if (this.form.invalid) {
      return;
    }

    const { inputEncoding, outputEncoding, message } = this.form.value;

    try {
      // Simulate encoding validation
      const isValid = this.isValidEncoding(message, inputEncoding);

      this.validationResult = {
        isValid,
        encoding: outputEncoding,
        message: isValid
          ? `Message is valid ${inputEncoding} and can be converted to ${outputEncoding}`
          : `Message contains invalid characters for ${inputEncoding} encoding`,
        details: {
          length: message.length,
          inputEncoding,
          outputEncoding,
          byteSize: new TextEncoder().encode(message).length,
        },
      };
    } catch (error) {
      this.validationResult = {
        isValid: false,
        encoding: inputEncoding,
        message: `Validation error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      };
    }
  }

  reset(): void {
    this.form.reset({
      inputEncoding: 'utf-8',
      outputEncoding: 'utf-8',
      message: '',
    });
    this.validationResult = null;
  }

  getKeys(obj: Record<string, unknown>): string[] {
    return Object.keys(obj);
  }

  private isValidEncoding(message: string, encoding: string): boolean {
    try {
      // Basic validation - in production, use proper encoding libraries
      if (encoding === 'ascii') {
        return /^[\x00-\x7F]*$/.test(message);
      }
      return true;
    } catch {
      return false;
    }
  }
}
