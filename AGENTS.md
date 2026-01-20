# Agent Guidelines for pHdockUI

This document provides guidelines for AI coding agents working in the pHdockUI codebase - a pH-aware molecular docking suite with a Next.js frontend and Python backend.

## Project Structure

```
pHdockUI/
├── website/           # Next.js 15 frontend (React 19, TypeScript)
│   ├── app/          # Next.js App Router pages & API routes
│   ├── components/   # React components
│   └── backend/      # Backend integration utilities
├── src/              # Python backend modules
├── replicate/        # Replicate deployment configuration
└── *.py             # Python scripts for data processing & model training
```

## Build & Development Commands

### Frontend (Next.js)
```bash
# Install dependencies
cd website && npm install

# Development server
cd website && npm run dev

# Production build
cd website && npm run build

# Start production server
cd website && npm start

# Lint check
cd website && npm run lint

# Lint fix
cd website && npm run lint -- --fix
```

### Python Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run main pipeline
python main.py --input molecules.smi --mode pka_prediction

# Run FastAPI backend (from website/backend)
cd website/backend && uvicorn main:app --reload
```

### Testing
- **Frontend**: No test framework currently configured
- **Python**: No pytest configuration found; tests exist in `test_*.py` files
  - Run individual test: `python test_final_models.py`
  - Run all tests: `python -m pytest` (if pytest is installed)

## Code Style Guidelines

### TypeScript/React (Frontend)

#### File Organization
- **Components**: `PascalCase.tsx` (e.g., `MoleculeInterface.tsx`)
- **Pages**: `page.tsx` (Next.js convention)
- **API Routes**: `route.ts` (Next.js convention)
- One component per file, default export

#### Import Order
```typescript
// 1. Next.js framework imports
import { NextRequest, NextResponse } from "next/server";
import type { Metadata } from "next";

// 2. External libraries
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import axios from "axios";

// 3. Internal components (use @ alias)
import MoleculeViewer from "@/components/MoleculeViewer";
import ResultsPanel from "@/components/ResultsPanel";

// 4. Styles
import "./globals.css";
```

#### TypeScript Patterns
- **Interfaces over types**: Always use `interface` for data structures and props
- **Props naming**: Suffix with `Props` (e.g., `interface ResultsPanelProps {}`)
- **Type imports**: Use `import type` for type-only imports
- **Optional properties**: Use `?` liberally for optional fields
- **Generic types**: Explicitly type hooks and queries
  ```typescript
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const { data } = useQuery<JobData>({ queryKey: ["jobs"] });
  ```

#### Component Structure
```typescript
"use client"; // For interactive components only

import { useState } from "react";

// Interface definitions at top
interface ComponentProps {
  value: string;
  onChange: (val: string) => void;
  optional?: boolean;
}

// Default export functional component
export default function ComponentName({ value, onChange, optional }: ComponentProps) {
  // 1. State hooks
  const [localState, setLocalState] = useState("");
  
  // 2. Data fetching hooks (React Query)
  const { data, isLoading } = useQuery({ ... });
  
  // 3. Mutations
  const mutation = useMutation({ ... });
  
  // 4. Event handlers (prefix with 'handle')
  const handleSubmit = async () => { ... };
  
  return (
    // JSX
  );
}
```

#### Naming Conventions
- **Variables/Functions**: `camelCase`
- **Components**: `PascalCase`
- **Constants**: `SCREAMING_SNAKE_CASE` (env vars only)
- **Booleans**: Prefix with `is`, `has`, `show`
- **Handlers**: Prefix with `handle` (e.g., `handleSubmit`, `handleFileUpload`)
- **Interfaces**: `PascalCase`, props suffix with `Props`

#### Error Handling (API Routes)
```typescript
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const response = await fetch(`${BACKEND_URL}/api/endpoint`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Backend returned ${response.status}`);
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Unknown error";
    console.error("Operation error:", e);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
```

#### Environment Variables
- **Client-side**: Prefix with `NEXT_PUBLIC_`
- **Server-side**: No prefix (API routes only)
- Always provide fallback defaults
  ```typescript
  const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
  ```

### Python (Backend)

#### Import Order
```python
"""Module docstring."""

# 1. Standard library
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# 2. Third-party libraries
import numpy as np
import pandas as pd
from rdkit import Chem

# 3. Local imports (relative)
from .module_name import ClassName
# Or absolute for scripts
from src.module_name import ClassName
```

#### Naming Conventions
- **Files**: `snake_case.py`
- **Classes**: `PascalCase` or `PascalCaseCamelCase` (e.g., `pKaPredictionModel`, `GNNpKaPredictor`)
- **Functions/Variables**: `snake_case`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Private**: Prefix with `_` (e.g., `_initialize_model`)

#### Type Hints
Always use type hints for function signatures:
```python
def process_molecule(smiles: str, 
                     ph_value: float = 7.4,
                     num_conformers: int = 50) -> Optional[Chem.Mol]:
    """
    Process molecule and generate conformers.
    
    Args:
        smiles: SMILES string representation
        ph_value: Target pH value (default: 7.4)
        num_conformers: Number of conformers to generate (default: 50)
        
    Returns:
        RDKit Mol object or None if processing fails
    """
    pass
```

#### Docstrings
Use Google-style docstrings for all public functions and classes:
```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description (one line).
    
    Longer description if needed, explaining the function's purpose,
    behavior, and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When invalid input is provided
    """
    pass
```

#### Error Handling
```python
try:
    result = process_data(input_data)
except ValueError as e:
    logger.error(f"Validation error: {e}")
    raise
except Exception as e:
    logger.exception(f"Unexpected error processing data: {e}")
    return None
```

#### Class Structure
```python
class ModelName:
    """Brief class description."""
    
    def __init__(self, param: str, option: bool = True):
        """Initialize with parameters."""
        self.param = param
        self.option = option
        self.logger = logging.getLogger(__name__)
        self._private_var = None
        
    def public_method(self, arg: int) -> str:
        """Public method description."""
        return self._private_method(arg)
        
    def _private_method(self, arg: int) -> str:
        """Private helper method."""
        return str(arg)
```

## Key Architectural Patterns

### Frontend
- **Server Components**: Default in Next.js 15 (no directive)
- **Client Components**: Add `"use client"` directive at top
- **Data Fetching**: Use React Query for all API calls
- **State Management**: React Query for server state, useState for UI state
- **API Routes**: Proxy to Python backend (fetch + forward pattern)
- **Styling**: Tailwind CSS with inline classes

### Backend
- All API routes in `website/app/api/**/route.ts` proxy to Python FastAPI backend
- Python backend serves ML models and computational endpoints
- Environment-based configuration with sensible defaults

## Common Pitfalls to Avoid

1. **Next.js 15 Params**: Dynamic route params are now async
   ```typescript
   // Correct
   const { id } = await params;
   
   // Incorrect
   const { id } = params;
   ```

2. **Don't mix state patterns**: Use React Query for server state, not useState

3. **Path aliases**: Always use `@/` for internal imports in frontend

4. **Error responses**: Always include type guard for Error instances

5. **Client directives**: Don't add `"use client"` to server components unnecessarily

6. **Python imports**: Use try/except for relative imports to support both module and script usage

## File Creation Guidelines

- **Avoid creating files unless necessary**: Prefer editing existing files
- **No markdown files**: Don't create README.md or documentation files unless explicitly requested
- **Component files**: Create in `website/components/` with PascalCase names
- **API routes**: Follow Next.js App Router conventions (`route.ts` files)
- **Python modules**: Add to `src/` directory with descriptive names

## Version Information

- **Node.js**: >=18 (specified in package.json)
- **Next.js**: 15.4.10
- **React**: 19.1.0
- **TypeScript**: 5.x
- **Python**: 3.x (with RDKit, PyTorch, XGBoost, FastAPI)
