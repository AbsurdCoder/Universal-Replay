# Universal Replay Tool - Frontend

This is a production-grade Angular 17+ frontend for a Kafka replay tool, built with standalone components, NgRx Signals for state management, and Angular Material for UI components.

## Features

- **Angular 17+**: Modern Angular with standalone components.

- **NgRx Signals**: Lightweight, reactive state management.

- **Angular Material**: Comprehensive UI component library.

- **Typed HTTP Client**: API client with models matching backend schemas.

- **Feature Modules**: Organized by feature (topic browser, replay, etc.).

- **Shared Components**: Reusable components, pipes, and directives.

- **Environment Configuration**: Separate configurations for dev and prod.

- **Linting & Formatting**: ESLint and Prettier configured.

- **Proxy Support**: Backend proxy for local development.

## Project Structure

```
/frontend
├── src/
│   ├── app/
│   │   ├── core/           → App-level services, models, state
│   │   ├── shared/         → Shared components, pipes, directives
│   │   ├── features/       → Feature modules
│   │   │   ├── topic-browser/
│   │   │   ├── replay/
│   │   │   ├── script-manager/
│   │   │   └── encoding-validator/
│   │   ├── layout/         → Shell, nav, sidebar
│   │   ├── app.component.ts
│   │   ├── app.config.ts
│   │   └── app.routes.ts
│   ├── assets/
│   ├── environments/
│   ├── main.ts
│   ├── index.html
│   └── styles.scss
├── .eslintrc.json
├── .prettierrc.json
├── angular.json
├── package.json
├── tsconfig.json
└── proxy.conf.json
```

## Getting Started

### Prerequisites

- Node.js 18+

- Angular CLI 17+

### 1. Install Dependencies

```bash
npm install
```

### 2. Start Development Server

```bash
npm start
```

The application will be available at `http://localhost:4200`.

## Build

### Development Build

```bash
npm run build
```

### Production Build

```bash
npm run build:prod
```

## Code Quality

### Linting

```bash
npm run lint
```

### Formatting

```bash
npm run format
```

## Key Components

### Core Module

- **ApiService**: Typed HTTP client for backend communication.

- **ErrorHandlerService**: Global error handling and notifications.

- **NgRx Signals Stores**: State management for replay jobs and topics.

- **Typed Models**: Interfaces matching backend Pydantic schemas.

### Shared Module

- **ErrorDisplayComponent**: Displays application errors.

- **LoadingSpinnerComponent**: Centered loading indicator.

- **StatusBadgeComponent**: Displays status with appropriate styling.

- **DateFormatPipe**: Formats ISO date strings.

- **TruncatePipe**: Truncates text to a specified length.

### Feature Modules

- **Topic Browser**: Browse Kafka topics and view metadata.

- **Replay**: Create, manage, and monitor replay jobs.

- **Script Manager**: Manage enrichment scripts.

- **Encoding Validator**: Validate message encoding.

## State Management

- **NgRx Signals**: Used for reactive state management.

- **`signalStore`**: Creates type-safe, feature-based stores.

- **`withState`**: Defines the initial state of the store.

- **`withComputed`**: Creates computed signals from state.

- **`withMethods`**: Defines methods for updating state.

## Development Workflow

1. **Create a new component**: `ng generate component features/my-feature/my-component --standalone`

1. **Add to routes**: Update `app.routes.ts` with the new component.

1. **Use stores**: Inject stores to manage state.

1. **Use services**: Inject services for API calls.

1. **Use shared components**: Use shared components for common UI elements.

## Contributing

Contributions are welcome! Please follow standard Git workflow (fork, branch, PR ).

