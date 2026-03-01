import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatChipsModule } from '@angular/material/chips';
import { ReplayJobStatus } from '@core/models/replay.model';

/**
 * Status badge component
 * Displays status with appropriate styling
 */
@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule, MatChipsModule],
  template: `
    <mat-chip [ngClass]="'status-' + (status | lowercase)">
      {{ status }}
    </mat-chip>
  `,
  styles: [
    `
      mat-chip {
        font-weight: 500;
      }

      .status-pending {
        background-color: #ffc107 !important;
        color: #000 !important;
      }

      .status-running {
        background-color: #2196f3 !important;
        color: #fff !important;
      }

      .status-completed {
        background-color: #4caf50 !important;
        color: #fff !important;
      }

      .status-failed {
        background-color: #f44336 !important;
        color: #fff !important;
      }

      .status-cancelled {
        background-color: #9e9e9e !important;
        color: #fff !important;
      }
    `,
  ],
})
export class StatusBadgeComponent {
  @Input() status: ReplayJobStatus = ReplayJobStatus.PENDING;
}
