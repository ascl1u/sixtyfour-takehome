# Sixtyfour Workflow Engine

A simplified replica of Sixtyfour's Workflow Engine with a React frontend and Python FastAPI backend. Build and execute data enrichment workflows by connecting modular blocks.

## Features

- **Visual Workflow Builder**: Drag-and-drop interface for building workflows
- **5 Block Types**: Read CSV, Enrich Lead, Find Email, Filter, Save CSV
- **Real-time Progress**: Live progress tracking during workflow execution
- **Async Processing**: Parallel API calls with polling for long-running operations
- **Results Viewer**: View and download workflow results as CSV

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Sixtyfour API key

### Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Set your API key
export SIXTYFOUR_API_KEY=your_api_key_here

# Run the server
python -m uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000

## Architecture

```
├── backend/
│   ├── main.py              # FastAPI app + REST endpoints
│   ├── engine.py            # Workflow execution engine
│   ├── sixtyfour_client.py  # Sixtyfour API client
│   └── blocks/
│       ├── base.py          # Block base class
│       ├── csv_blocks.py    # ReadCSV, SaveCSV
│       ├── filter_block.py  # Filter
│       └── api_blocks.py    # EnrichLead, FindEmail
├── frontend/
│   └── src/
│       ├── components/      # React components
│       ├── store/           # Zustand state management
│       └── types/           # TypeScript types
└── data.csv                 # Sample data
```

## Block Types

| Block | Description | Configuration |
|-------|-------------|---------------|
| **Read CSV** | Load a CSV file | `file_path` |
| **Enrich Lead** | Enrich lead info via Sixtyfour API | `struct` (fields to enrich) |
| **Find Email** | Find email addresses | `mode`, `output_column` |
| **Filter** | Filter rows by condition | `column`, `operator`, `value` |
| **Save CSV** | Export to CSV | `file_name` |

## Example Workflows

### Basic Workflow
```
Read CSV → Enrich Lead → Save CSV
```

### Filtered Workflow
```
Read CSV → Filter (company contains 'Ariglad') → Enrich Lead → Save CSV
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/blocks` | GET | Get available block types |
| `/workflows/execute` | POST | Start workflow execution |
| `/workflows/{id}/status` | GET | Get workflow progress |
| `/workflows/{id}/results` | GET | Get workflow results |
| `/files` | GET | List available CSV files |
| `/files/upload` | POST | Upload a CSV file |

## Key Design Decisions

1. **Async-first approach**: Uses async endpoints for Sixtyfour API calls since they can take 5-10 minutes
2. **Server-side workflow state**: Workflow state is managed on the backend to survive page refreshes
3. **Pandas for DataFrame ops**: Natural fit for CSV manipulation and filtering
4. **React Flow for UI**: Battle-tested library for building workflow/node editors

## Discussion Topics

### How would you implement the enrich_company endpoint?
Similar to enrich_lead, using the company domain or name as input. Would add company-specific fields like industry, employee count, funding, and tech stack.

### How to prevent incompatible blocks from being chained?
- Add block metadata indicating input/output types (e.g., "requires DataFrame", "outputs DataFrame")
- Validate connections in the frontend before allowing edges
- Add backend validation when executing workflows

### How would you scale to thousands of rows?
- Batch API calls with rate limiting (500 req/min)
- Use connection pooling and persistent HTTP sessions
- Process rows in parallel with asyncio semaphores
- Consider streaming/chunked processing for very large files
- Add job queuing (Redis/Celery) for background processing

### Product decisions and tradeoffs
- **Simplicity over features**: Focused on core functionality for the takehome
- **In-memory state**: No database for simplicity, but limits persistence
- **Monospace font**: Chose JetBrains Mono for a developer-focused aesthetic
- **Dark theme**: Matches the reference design and reduces eye strain

