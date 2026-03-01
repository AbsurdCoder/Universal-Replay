import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { RouterModule } from '@angular/router';

/**
 * Navbar component
 * Top navigation bar with user menu and actions
 */
@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatMenuModule, RouterModule],
  template: `
    <div class="navbar">
      <button mat-icon-button [matMenuTriggerFor]="menu" class="user-menu">
        <mat-icon>account_circle</mat-icon>
      </button>
      <mat-menu #menu="matMenu">
        <button mat-menu-item>
          <mat-icon>settings</mat-icon>
          <span>Settings</span>
        </button>
        <button mat-menu-item>
          <mat-icon>help</mat-icon>
          <span>Help</span>
        </button>
        <mat-divider></mat-divider>
        <button mat-menu-item>
          <mat-icon>logout</mat-icon>
          <span>Logout</span>
        </button>
      </mat-menu>
    </div>
  `,
  styles: [
    `
      .navbar {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .user-menu {
        cursor: pointer;
      }
    `,
  ],
})
export class NavbarComponent {}
