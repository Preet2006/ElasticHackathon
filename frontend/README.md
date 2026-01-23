# CodeJanitor Frontend 🛡️

A cyberpunk-themed Security Operations Center (SOC) interface for the CodeJanitor autonomous security agent.

## Tech Stack

- **Next.js 14** (App Router)
- **Tailwind CSS** (Styling)
- **Framer Motion** (Animations)
- **Lucide React** (Icons)
- **TypeScript** (Type Safety)

## Design System

### Color Palette
- **Background**: Deep Zinc (`bg-zinc-950`)
- **Panels**: `bg-zinc-900/50`
- **Success/System**: Neon Green (`text-green-400`)
- **Red Team/Critical**: Neon Red (`text-red-500`)
- **Blue Team/Defense**: Neon Blue (`text-blue-500`)

### Typography
- **UI**: Inter
- **Code/Logs**: JetBrains Mono

## Getting Started

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Features

### 1. Sidebar Navigation
- System status indicators (Docker, LLM, Network)
- Smooth page transitions
- Active state animations

### 2. Dashboard
- GitHub repository input with scan trigger
- Real-time statistics (Vulnerabilities, Critical Risks, Auto-Fix Rate)
- Vulnerability feed with severity badges
- One-click auto-remediation

### 3. Live Operations Mode
- **Red Team Terminal**: Real-time exploit streaming
- **Blue Team Terminal**: Defense protocol streaming
- Animated typing effect
- Color-coded terminal output

### 4. Terminal Stream Component
- Reusable terminal window
- Typing animation with realistic delays
- Blinking cursor
- Scanning effect overlay
- Custom scrollbar styling

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with sidebar
│   ├── page.tsx            # Main dashboard
│   └── globals.css         # Global styles & utilities
├── components/
│   ├── Sidebar.tsx         # Navigation sidebar
│   └── TerminalStream.tsx  # Animated terminal component
├── public/                 # Static assets
├── tailwind.config.ts      # Tailwind configuration
├── tsconfig.json          # TypeScript configuration
└── package.json           # Dependencies
```

## Key Components

### Sidebar.tsx
- Fixed left navigation
- System status indicators
- Glowing effects on active states

### TerminalStream.tsx
Props:
- `title`: Terminal window title
- `color`: 'red' | 'blue' | 'green'
- `logs`: Array of log strings
- `isActive`: Boolean for animation state

### page.tsx (Dashboard)
Features:
- Hero section with scan input
- Statistics grid
- Vulnerability feed
- Live operations split-view

## Mock Data

The dashboard includes mock vulnerabilities:
- SQL Injection
- Remote Code Execution
- Insecure Deserialization
- XXE Injection
- Path Traversal

## Customization

### Adding New Terminal Colors
Edit `TerminalStream.tsx`:

```typescript
const colorClasses = {
  // Add your custom color
  purple: {
    border: 'border-purple-500/20',
    text: 'text-purple-500',
    glow: 'glow-purple',
    shadow: 'shadow-[0_0_15px_rgba(168,85,247,0.1)]',
  },
};
```

### Adding New Vulnerabilities
Edit mock data in `page.tsx`:

```typescript
const mockVulnerabilities = [
  {
    id: 6,
    title: 'Your Vulnerability',
    severity: 'critical' | 'high' | 'medium' | 'low',
    file: 'path/to/file.py',
    line: 123,
    type: 'Vulnerability Type',
    status: 'detected',
  },
];
```

## Production Build

```bash
npm run build
npm start
```

## Integration with Backend

To connect to the Python backend:

1. Add API routes in `app/api/`
2. Update mock data fetching to use real API calls
3. Implement WebSocket for real-time terminal streaming

Example:
```typescript
// app/api/scan/route.ts
export async function POST(request: Request) {
  const { repoUrl } = await request.json();
  
  // Call Python backend
  const response = await fetch('http://localhost:8000/scan', {
    method: 'POST',
    body: JSON.stringify({ repo: repoUrl }),
  });
  
  return response;
}
```

## Performance

- Server-side rendering with Next.js
- Optimized animations with Framer Motion
- Lazy loading of heavy components
- Efficient re-renders with React hooks

## Hackathon Ready ✅

This UI is designed to be:
- **Visually Impressive**: Cyberpunk SOC aesthetic
- **Functional**: All interactions work with mock data
- **Responsive**: Works on different screen sizes
- **Animated**: Smooth transitions and effects
- **Professional**: Production-ready code quality

## License

MIT - Part of the CodeJanitor project
