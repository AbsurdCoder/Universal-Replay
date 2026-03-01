import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';

interface NavItem {
  label: string;
  icon: string;
  route: string;
}

/**
 * Sidebar component
 * Navigation sidebar with feature links
 */
@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, MatListModule, MatIconModule, RouterModule],
  template: `
    <div class="sidebar">
      <div class="sidebar-header">
        <h2>Navigation</h2>
      </div>

      <mat-nav-list>
        <mat-list-item *ngFor="let item of navItems" [routerLink]="item.route" routerLinkActive="active">
          <mat-icon matListItemIcon>{{ item.icon }}</mat-icon>
          <span matListItemTitle>{{ item.label }}</span>
        </mat-list-item>
      </mat-nav-list>
    </div>
  `,
  styles: [
    `
      .sidebar {
        height: 100%;
        display: flex;
        flex-direction: column;
        background-color: #f5f5f5;
      }

      .sidebar-header {
        padding: 16px;
        border-bottom: 1px solid #e0e0e0;
      }

      .sidebar-header h2 {
        margin: 0;
        font-size: 16px;
        font-weight: 500;
      }

      mat-nav-list {
        flex: 1;
        overflow-y: auto;
      }

      mat-list-item {
        cursor: pointer;
      }

      mat-list-item.active {
        background-color: #e3f2fd;
      }
    `,
  ],
})
export class SidebarComponent {
  navItems: NavItem[] = [
    {
      label: 'Topic Browser',
      icon: 'topic',
      route: '/topics',
    },
    {
      label: 'Replay Jobs',
      icon: 'replay',
      route: '/replays',
    },
    {
      label: 'Script Manager',
      icon: 'code',
      route: '/scripts',
    },
    {
      label: 'Encoding Validator',
      icon: 'check_circle',
      route: '/encoding',
    },
  ];
}
