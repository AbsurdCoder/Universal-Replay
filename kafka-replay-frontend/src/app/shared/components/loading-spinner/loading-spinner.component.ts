import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

/**
 * Loading spinner component
 * Displays a centered loading indicator
 */
@Component({
  selector: 'app-loading-spinner',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule],
  template: `
    <div class="spinner-container" *ngIf="isLoading">
      <mat-spinner [diameter]="diameter" [strokeWidth]="strokeWidth"></mat-spinner>
      <p *ngIf="message" class="spinner-message">{{ message }}</p>
    </div>
  `,
  styles: [
    `
      .spinner-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 32px;
        gap: 16px;
      }

      .spinner-message {
        margin: 0;
        color: #666;
        font-size: 14px;
      }
    `,
  ],
})
export class LoadingSpinnerComponent {
  @Input() isLoading = true;
  @Input() message: string | null = null;
  @Input() diameter = 50;
  @Input() strokeWidth = 4;
}
