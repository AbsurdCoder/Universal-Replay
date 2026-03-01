import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { RouterOutlet } from '@angular/router';
import { NavbarComponent } from '../navbar/navbar.component';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { ErrorDisplayComponent } from '@shared/components/error-display/error-display.component';

/**
 * Main shell component
 * Provides layout structure with navbar, sidebar, and content area
 */
@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatSidenavModule,
    MatIconModule,
    MatButtonModule,
    RouterOutlet,
    NavbarComponent,
    SidebarComponent,
    ErrorDisplayComponent,
  ],
  template: `
    <mat-toolbar color="primary" class="app-toolbar">
      <button mat-icon-button (click)="sidenav.toggle()" class="menu-button">
        <mat-icon>menu</mat-icon>
      </button>
      <span class="app-title">Kafka Replay Tool</span>
      <span class="spacer"></span>
      <app-navbar></app-navbar>
    </mat-toolbar>

    <mat-sidenav-container class="sidenav-container">
      <mat-sidenav #sidenav class="sidenav" mode="side" [opened]="true">
        <app-sidebar></app-sidebar>
      </mat-sidenav>

      <mat-sidenav-content class="content">
        <router-outlet></router-outlet>
      </mat-sidenav-content>
    </mat-sidenav-container>

    <app-error-display></app-error-display>
  `,
  styles: [
    `
      .app-toolbar {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .app-title {
        font-size: 20px;
        font-weight: 500;
      }

      .spacer {
        flex: 1 1 auto;
      }

      .sidenav-container {
        height: calc(100vh - 64px);
      }

      .sidenav {
        width: 250px;
      }

      .content {
        padding: 16px;
        overflow-y: auto;
      }

      @media (max-width: 600px) {
        .sidenav {
          width: 200px;
        }

        .app-title {
          font-size: 16px;
        }
      }
    `,
  ],
})
export class ShellComponent {
  sidenav: any;
}
