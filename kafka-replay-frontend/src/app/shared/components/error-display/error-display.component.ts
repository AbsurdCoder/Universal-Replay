import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule } from '@angular/material/icon';
import { ErrorHandlerService, AppError } from '@core/services/error-handler.service';

/**
 * Error display component
 * Shows application errors using Material snack bar
 */
@Component({
  selector: 'app-error-display',
  standalone: true,
  imports: [CommonModule, MatSnackBarModule, MatIconModule],
  template: `
    <div *ngIf="errors$ | async as errors" class="error-container">
      <div *ngFor="let error of errors" class="error-item" [@slideIn]>
        <mat-icon class="error-icon">error</mat-icon>
        <div class="error-content">
          <div class="error-message">{{ error.message }}</div>
          <div *ngIf="error.code" class="error-code">{{ error.code }}</div>
        </div>
        <button (click)="removeError(error.id)" class="error-close">
          <mat-icon>close</mat-icon>
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .error-container {
        position: fixed;
        top: 16px;
        right: 16px;
        z-index: 1000;
      }

      .error-item {
        display: flex;
        align-items: center;
        gap: 12px;
        background-color: #f44336;
        color: white;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
      }

      .error-icon {
        flex-shrink: 0;
      }

      .error-content {
        flex: 1;
      }

      .error-message {
        font-weight: 500;
      }

      .error-code {
        font-size: 12px;
        opacity: 0.8;
      }

      .error-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        padding: 0;
        display: flex;
        align-items: center;
      }
    `,
  ],
})
export class ErrorDisplayComponent implements OnInit {
  errors$ = this.errorHandler.getErrors();

  constructor(private errorHandler: ErrorHandlerService) {}

  ngOnInit(): void {}

  removeError(id: string): void {
    this.errorHandler.removeError(id);
  }
}
