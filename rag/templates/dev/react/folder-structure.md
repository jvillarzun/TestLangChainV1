# React — Project Structure & Organization

## Recommended Folder Structure (Feature-based)

```
src/
├── app/                    # App-level setup
│   ├── App.tsx
│   ├── router.tsx          # React Router config
│   ├── store.ts            # Redux store (if used)
│   └── providers.tsx       # QueryClientProvider, ThemeProvider, etc.
│
├── features/               # One folder per domain feature
│   ├── auth/
│   │   ├── components/     # Feature-specific components
│   │   │   ├── LoginForm.tsx
│   │   │   └── LoginForm.test.tsx
│   │   ├── hooks/          # Custom hooks for this feature
│   │   │   └── useAuth.ts
│   │   ├── api/            # API calls (React Query / RTK Query)
│   │   │   └── authApi.ts
│   │   ├── types.ts        # Types/interfaces local to feature
│   │   └── index.ts        # Public API of the feature
│   │
│   └── products/
│       ├── components/
│       ├── hooks/
│       ├── api/
│       └── index.ts
│
├── shared/                 # Truly reusable across features
│   ├── components/
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   ├── Button.test.tsx
│   │   │   └── index.ts
│   │   └── ...
│   ├── hooks/              # useDebounce, useLocalStorage, etc.
│   ├── utils/              # Pure functions, formatters
│   ├── types/              # Global TS types/interfaces
│   └── constants/
│
├── pages/                  # Route-level components (thin wrappers)
│   ├── HomePage.tsx
│   └── ProductDetailPage.tsx
│
└── assets/                 # Static files
```

## Component Pattern

```tsx
// Prefer named exports
export interface ButtonProps {
  label: string
  onClick: () => void
  variant?: 'primary' | 'secondary' | 'ghost'
  disabled?: boolean
  isLoading?: boolean
}

export function Button({ label, onClick, variant = 'primary', disabled, isLoading }: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      className={cn(buttonVariants({ variant }), isLoading && 'opacity-70')}
    >
      {isLoading ? <Spinner /> : label}
    </button>
  )
}
```

## Custom Hook Pattern

```ts
// features/products/hooks/useProducts.ts
export function useProducts(categoryId: string) {
  return useQuery({
    queryKey: ['products', categoryId],
    queryFn: () => fetchProducts(categoryId),
    staleTime: 5 * 60 * 1000,
  })
}

// Mutation hook
export function useCreateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createProduct,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['products'] }),
  })
}
```

## State Management Rules
- **Local UI state**: `useState` / `useReducer` (keep it close)
- **Server state**: React Query or RTK Query (never duplicate in Redux)
- **Global client state**: Zustand (preferred) or Redux Toolkit
- **URL state**: React Router `useSearchParams` for filters/pagination
- Never store derived data in state — compute from existing state

## Key Conventions
- One component per file, filename = component name (PascalCase)
- Each feature exports only through its `index.ts` — no deep imports
- Colocate tests next to the file they test
- Prefix custom hooks with `use`
- Types go in `.ts` files, components in `.tsx`
