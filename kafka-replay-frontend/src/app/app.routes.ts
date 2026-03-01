import { Routes } from '@angular/router';
import { ShellComponent } from '@layout/shell/shell.component';
import { TopicListComponent, TopicDetailComponent } from '@features/topic-browser/index';
import { ReplayListComponent, ReplayFormComponent } from '@features/replay/index';
import { ScriptManagerComponent } from '@features/script-manager/script-manager.component';
import { EncodingValidatorComponent } from '@features/encoding-validator/encoding-validator.component';

export const routes: Routes = [
  {
    path: '',
    component: ShellComponent,
    children: [
      {
        path: 'topics',
        children: [
          {
            path: '',
            component: TopicListComponent,
          },
          {
            path: ':name',
            component: TopicDetailComponent,
          },
        ],
      },
      {
        path: 'replays',
        children: [
          {
            path: '',
            component: ReplayListComponent,
          },
          {
            path: 'new',
            component: ReplayFormComponent,
          },
          {
            path: ':id',
            component: ReplayListComponent, // TODO: Create detail component
          },
        ],
      },
      {
        path: 'scripts',
        component: ScriptManagerComponent,
      },
      {
        path: 'encoding',
        component: EncodingValidatorComponent,
      },
      {
        path: '',
        redirectTo: '/topics',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: '**',
    redirectTo: '/topics',
  },
];
