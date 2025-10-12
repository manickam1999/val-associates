# Vel PDF Web

Modern web application for converting Malaysian STR PDFs to Excel format with real-time progress tracking.

## Features

- 🎨 Modern UI with Next.js 15 + React 19
- 🎭 Dark/Light mode with system preference detection
- 📤 Drag-and-drop file upload
- 📦 Support for single/multiple PDFs and ZIP files
- ⚡ Real-time progress updates via WebSocket
- 📊 Download consolidated Excel output
- 🎯 Responsive design with Tailwind CSS v4
- 🧩 Beautiful components with shadcn/ui

## Tech Stack

- **Next.js 15.5** - React framework with App Router
- **React 19** - Latest React features
- **TypeScript** - Type safety
- **Tailwind CSS v4** - Utility-first styling
- **shadcn/ui** - High-quality UI components
- **next-themes** - Theme management
- **lucide-react** - Beautiful icons

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Environment Configuration

Copy `.env.local.example` to `.env.local`:

```bash
cp .env.local.example .env.local
```

Configure the backend URLs:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 3. Run Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Project Structure

```
vel-pdf-web/
├── app/
│   ├── layout.tsx          # Root layout with theme provider
│   ├── page.tsx             # Main upload page
│   └── globals.css          # Global styles
├── components/
│   ├── upload-zone.tsx      # Drag-drop upload component
│   ├── progress-display.tsx # Progress tracker
│   ├── theme-toggle.tsx     # Dark/light mode toggle
│   ├── theme-provider.tsx   # Theme context provider
│   └── ui/                  # shadcn/ui components
├── lib/
│   ├── utils.ts             # Utility functions
│   └── api-client.ts        # Backend API client
└── .env.local               # Environment variables
```

## Usage

1. **Upload Files**: Drag PDFs or ZIP files onto the upload zone, or click to browse
2. **Monitor Progress**: Watch real-time progress as files are processed
3. **Download Excel**: Click download when processing completes
4. **Toggle Theme**: Use the sun/moon icon to switch between light/dark mode

## API Integration

The frontend connects to the backend via:
- **REST API** for file uploads
- **WebSocket** for real-time progress updates

See `lib/api-client.ts` for implementation details.

## Development

### Adding shadcn/ui Components

```bash
npx shadcn@latest add <component-name>
```

### Building for Production

```bash
npm run build
npm start
```

## Scripts

- `npm run dev` - Start development server with Turbopack
- `npm run build` - Build for production
- `npm start` - Start production server

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT
