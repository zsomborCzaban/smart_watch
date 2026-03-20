# Hiking Tracker Frontend

A modern web-based interface for tracking hiking activities with real-time watch connectivity. Built with React, TypeScript, and Vite.

## Overview

The Hiking Tracker Frontend displays hiking session data from a smartwatch device, allowing users to monitor active sessions in real-time, review past activity history, and manage personal settings like body weight. The application maintains a live connection to the smartwatch via WebSocket for instant updates on session status.

## ✨ Features

### Active Session Tracking

- **Real-time session display** with up-to-date statistics
- **Step count** tracking throughout the hike
- **Calorie burned** calculation based on activity and weight
- **Distance walked** with precision to 2 decimal places (km)
- **Session duration** in HH:MM:SS format
- **Session status** indicator (Active/Paused)
- Auto-refresh when session status changes

### Past Sessions Management

- **Expandable session cards** with one-click access to details
- **Session sorting** by date (newest first)
- **Comprehensive statistics** per session:
  - Start and end times
  - Step count
  - Calories burned
  - Distance walked
  - Body weight at session time
- **Delete sessions** with one-click removal
- **Empty state** messaging when no past sessions exist

### Settings & Configuration

- **Collapsible settings panel** for easy access
- **Weight management** with decimal precision
- **Input validation** (positive numbers only)
- **Real-time updates** with API persistence
- **Error handling** with graceful fallbacks

### Watch Connection

- **Live connection status** indicator (Connected/Disconnected)
- **Visual feedback** with color-coded status
- **Automatic reconnection** with exponential backoff
- **WebSocket integration** for real-time updates

## 🏗️ Architecture

### Components

- **App** - Main orchestrator component managing app state and data flow
- **ActiveSession** - Displays current hiking session statistics
- **SessionList** - Expandable list of past sessions with delete functionality
- **Settings** - Weight configuration panel with validation

### Utilities

- **api.ts** - REST API communication layer
- **format.ts** - Date/time formatting and ISO 8601 duration parsing
- **types.ts** - TypeScript interface definitions

### Hooks

- **useWatchStatus** - Custom hook for WebSocket connection management and real-time updates

### Data Flow

```
App Component
├── useWatchStatus Hook (WebSocket)
├── API Calls (getAllSessions, getWeight)
├── State Management (sessions, weight)
├── Components
│   ├── ActiveSession (displays or "no session")
│   ├── SessionList (past sessions)
│   └── Settings (weight management)
└── Event Handlers
    ├── handleDelete (session deletion)
    └── handleWeightChange (weight updates)
```

## 🛠️ Tech Stack

- **Frontend Framework**: React 19
- **Language**: TypeScript 5.9
- **Build Tool**: Vite 7
- **Testing**: Vitest + React Testing Library
- **Styling**: CSS Modules
- **Code Quality**: ESLint

## 📦 Installation & Setup

### Prerequisites

- Node.js 16+
- npm 8+

### Development Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm build

# Preview production build
npm preview

# Run linting
npm run lint
```

## 🧪 Testing

This project includes comprehensive testing coverage.

### Running Tests

```bash
# Run all tests once
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with UI dashboard
npm test:ui

# Generate coverage report
npm test:coverage
```

### Test Coverage

- **Utility Functions**
  - Date/time formatting
  - API communication
  - WebSocket hook

- **Component Tests**
  - ActiveSession display
  - SessionList interactions
  - Settings form

- **Integration Tests**
  - App component workflows
  - Multi-step user flows
  - Error handling
  - Data persistence

## 🔄 API Integration

The application communicates with a backend API at `/api/` with the following endpoints:

### Sessions

- `GET /api/allSessions` - Fetch all hiking sessions
- `DELETE /api/session/:id` - Delete a specific session

### Weight Management

- `GET /api/weight` - Fetch current user weight
- `POST /api/setWeight` - Update user weight

### WebSocket

- `WS /api/ws` - Real-time session updates

## 📊 Data Models

### HikingSession

```typescript
interface HikingSession {
  isActive: boolean; // Session active status
  sessionId: string; // Unique session identifier
  startTime: string; // ISO 8601 start datetime
  endTime: string; // ISO 8601 end datetime
  stepCount: number; // Total steps
  burnedCalories: number; // Calories burned
  distanceWalked: number; // Distance in meters
  bodyWeightKg: number; // User weight in kg
  hikeSessionTime?: string; // ISO 8601 duration (PT format)
  isPaused?: boolean; // Session pause status
}
```

## 🎯 Key Use Cases

### 1. Monitor Active Hike

- User starts a hike on smartwatch
- Frontend receives WebSocket update with active session
- Real-time statistics displayed (steps, calories, distance, time)
- Auto-updates as data changes

### 2. View Session History

- User navigates to past sessions list
- Sessions sorted by date (newest first)
- Click to expand for detailed statistics
- Single-click delete option

### 3. Configure Personal Settings

- User updates weight in settings panel
- Change immediately persisted to backend
- Weight used in future calorie calculations
- Validation prevents invalid values

### 4. Monitor Watch Connection

- Live connection status always visible in header
- Automatic reconnection if connection lost
- Clear visual indicator (green/gray dot)

## ⚙️ Configuration

### WebSocket

- Auto-reconnects after 3 seconds on disconnect
- Handles malformed messages gracefully
- Processes session_update type messages

## 🐛 Error Handling

The application implements robust error handling:

- **API Errors**: Caught and logged without breaking UI
- **Validation Errors**: Prevent invalid input (negative weight, etc.)
- **Network Errors**: Automatic reconnection for WebSocket
- **Malformed Data**: Graceful fallback with sensible defaults

## 📈 Performance

- Fast test execution: ~2.6s for all tests
- Optimized component re-renders
- Minimal bundle size with tree-shaking
- CSS minimal footprint

## 🎨 UI/UX Features

- **Responsive Design**: Works on desktop and tablet
- **Intuitive Navigation**: Collapsible panels and expandable cards
- **Visual Feedback**: Status indicators and interactive elements
- **Accessibility**: Semantic HTML and keyboard-friendly
- **Clear Empty States**: Helpful messaging when no data available

## 🚀 Deployment

### Build

```bash
npm run build
```

Output: `dist/` directory with optimized production bundle

### Preview

```bash
npm run preview
```

Test the production build locally

## 📝 Code Quality

- **TypeScript**: Full type safety throughout codebase
- **ESLint**: Strict linting rules enforced
- **Testing**: Comprehensive tests with 0 errors
- **No `any` types**: Fully typed test mocks and utilities

## 🔗 Related Documentation

- [Backend API](../backend) - Backend service documentation
- [Smart Watch Device](../smartwatch) - Watch firmware details
