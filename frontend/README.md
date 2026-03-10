# PlanWeaver Frontend

React + TypeScript frontend for the PlanWeaver planning and execution engine.

## Overview

The PlanWeaver frontend provides an interactive web interface for:
- Creating planning sessions with user intents
- Answering clarifying questions from the AI planner
- Reviewing and selecting approach proposals
- Executing and monitoring plan execution
- Optimizing plans with AI-generated variants

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Animations
- **Lucide React** - Icons
- **Vitest** - Unit testing
- **Playwright** - End-to-end testing

## Project Structure

```
frontend/
├── src/
│   ├── components/         # React components
│   │   ├── NewPlanForm.tsx         # Session creation form
│   │   ├── QuestionPanel.tsx       # Clarifying questions UI
│   │   ├── ProposalPanel.tsx       # Proposal selection UI
│   │   ├── ExecutionPanel.tsx      # Execution status visualization
│   │   ├── PlanView.tsx            # Main plan dashboard
│   │   ├── OptimizerStage.tsx      # Plan optimizer interface
│   │   ├── ComparisonPanel.tsx     # Variant comparison UI
│   │   ├── PlanCard.tsx            # Plan card component
│   │   └── Toast.tsx               # Toast notifications
│   ├── api/                # API client
│   │   └── client.ts               # Axios-based API client
│   ├── hooks/              # Custom React hooks
│   │   └── useApi.ts               # API interaction hook
│   ├── App.tsx             # Root component
│   └── main.tsx            # Entry point
├── public/                 # Static assets
├── tests/                  # Playwright E2E tests
├── index.html              # HTML template
├── package.json            # Dependencies
├── tsconfig.json           # TypeScript config
├── vite.config.ts          # Vite configuration
└── playwright.config.ts    # Playwright E2E config
```

## Quick Start

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The dev server runs at `http://localhost:5173`

### Backend Connection

By default, the frontend connects to `http://localhost:8000`. To change:

```bash
# .env file
VITE_API_URL=http://your-backend-url:8000
```

## Component Architecture

### Core Components

#### NewPlanForm
- Captures user intent for planning sessions
- Optional scenario selection
- Model selection for planner and executor

#### QuestionPanel
- Displays clarifying questions from the planner
- Captures user answers
- Submits answers to refine the plan

#### ProposalPanel
- Shows multiple approach proposals
- Displays pros, cons, and analysis
- Allows user to select an approach

#### ExecutionPanel
- Visualizes execution graph (DAG)
- Shows step status (pending, in progress, completed, failed)
- Displays step outputs and errors

#### OptimizerStage
- Generates AI-optimized plan variants
- Compares plans side-by-side
- Multi-model rating interface

#### ComparisonPanel
- Displays variant comparisons
- Shows ratings from multiple AI models
- User feedback collection

#### PlanCard
- Displays plan summary
- Shows complexity, time, and cost estimates
- Risk factor highlighting

#### Toast
- Notification system for user feedback
- Success, error, and info messages

### Component Communication

Components communicate through:
- **Props** - Parent to child data flow
- **useApi hook** - Centralized API calls
- **React Router** - Navigation and URL state
- **Context** - Shared application state (if needed)

## Development Workflow

### Adding a New Component

1. Create component file:
   ```bash
   # src/components/MyComponent.tsx
   ```

2. Define component with TypeScript:
   ```tsx
   import React from 'react';

   interface MyComponentProps {
     title: string;
     onAction: () => void;
   }

   export const MyComponent: React.FC<MyComponentProps> = ({
     title,
     onAction
   }) => {
     return (
       <div className="p-4">
         <h2>{title}</h2>
         <button onClick={onAction}>Action</button>
       </div>
     );
   };
   ```

3. Use in parent component:
   ```tsx
   import { MyComponent } from './components/MyComponent';
   ```

### API Integration

Use the `useApi` hook for API calls:

```tsx
import { useApi } from '../hooks/useApi';

export const MyComponent = () => {
  const { data, loading, error, fetchData } = useApi();

  const handleCreateSession = async () => {
    await fetchData('/api/v1/sessions', {
      method: 'POST',
      data: { user_intent: 'My intent' }
    });
  };

  // ...
};
```

### Styling

PlanWeaver uses Tailwind CSS for styling:

```tsx
<div className="bg-white rounded-lg shadow-md p-6">
  <h2 className="text-xl font-bold text-gray-900">
    Title
  </h2>
  <p className="text-gray-600 mt-2">
    Description
  </p>
</div>
```

Common patterns:
- `p-{n}` - padding
- `m-{n}` - margin
- `text-{color}-{shade}` - text color
- `bg-{color}-{shade}` - background color
- `rounded-{size}` - border radius
- `shadow-{size}` - box shadow

### State Management

Current approach:
- **Local component state** - Component-specific state
- **URL state** - Session IDs in route params
- **Server state** - API response data

For complex state, consider:
- Zustand (lightweight)
- React Query (server state)
- Context API (global state)

## Testing

### Unit Tests (Vitest)

```bash
# Run tests
npm test

# Run with UI
npm run test:ui

# Run coverage
npm run test:coverage
```

Example test:
```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders title', () => {
    render(<MyComponent title="Test" onAction={() => {}} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

### E2E Tests (Playwright)

```bash
# Run E2E tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui

# Run headed mode
npm run test:e2e:headed
```

Example test:
```tsx
import { test, expect } from '@playwright/test';

test('creates a session', async ({ page }) => {
  await page.goto('http://localhost:5173');
  await page.fill('[data-testid="user-intent"]', 'Build a REST API');
  await page.click('[data-testid="submit-button"]');
  await expect(page.locator('[data-testid="session-id"]')).toBeVisible();
});
```

## Build and Deployment

### Production Build

```bash
npm run build
```

Build output is in `dist/` directory.

### Docker Deployment

```bash
# Build image
docker build -t planweaver-frontend .

# Run container
docker run -p 5173:5173 planweaver-frontend
```

### Nginx Configuration

For production, serve with nginx:

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
    }
}
```

## Performance Considerations

1. **Code Splitting**
   - React Router lazy loading
   - Dynamic imports for large components

2. **Memoization**
   - Use `React.memo` for expensive components
   - Use `useMemo` / `useCallback` for computations

3. **Asset Optimization**
   - Vite automatically optimizes
   - Images compressed and cached

4. **Bundle Size**
   - Monitor with `npm run build`
   - Tree-shaking removes unused code

## Accessibility

- Semantic HTML elements
- ARIA labels for interactive elements
- Keyboard navigation support
- Color contrast compliance
- Screen reader testing

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Troubleshooting

### Common Issues

**1. Vite dev server not starting**
```bash
# Clear cache
rm -rf node_modules/.vite
npm run dev
```

**2. TypeScript errors**
```bash
# Regenerate type definitions
npm run type-check
```

**3. Build failures**
```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
```

**4. API connection errors**
- Check backend is running on port 8000
- Verify `VITE_API_URL` environment variable
- Check CORS settings on backend

## Contributing

1. Follow existing code style
2. Add TypeScript types for all props
3. Write tests for new components
4. Update documentation
5. Run linting before committing:
   ```bash
   npm run lint
   npm run format
   ```

## Resources

- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Vitest](https://vitest.dev/)
- [Playwright](https://playwright.dev/)

## Support

For frontend-specific issues:
- Check the main [README.md](../README.md)
- See [deployment-guide.md](../docs/deployment-guide.md)
- Review [architecture.md](../docs/architecture.md)
