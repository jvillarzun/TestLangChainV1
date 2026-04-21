# React Query — Patterns for Data Fetching

## Setup

```tsx
// app/providers.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,       // 1 min before refetch
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export function Providers({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
```

## Query Keys Convention

```ts
// features/products/api/queryKeys.ts
export const productKeys = {
  all:    ()           => ['products']               as const,
  lists:  ()           => [...productKeys.all(), 'list'] as const,
  list:   (filters: F) => [...productKeys.lists(), filters] as const,
  detail: (id: string) => [...productKeys.all(), 'detail', id] as const,
}
```

## Standard Query

```ts
export function useProduct(id: string) {
  return useQuery({
    queryKey: productKeys.detail(id),
    queryFn:  () => api.get<Product>(`/products/${id}`),
    enabled:  !!id,
  })
}
```

## Optimistic Update Pattern

```ts
export function useUpdateProduct() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Product> }) =>
      api.patch<Product>(`/products/${id}`, data),

    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: productKeys.detail(id) })
      const previous = queryClient.getQueryData(productKeys.detail(id))
      queryClient.setQueryData(productKeys.detail(id), (old: Product) => ({ ...old, ...data }))
      return { previous }
    },

    onError: (_err, { id }, context) => {
      queryClient.setQueryData(productKeys.detail(id), context?.previous)
    },

    onSettled: (_data, _err, { id }) => {
      queryClient.invalidateQueries({ queryKey: productKeys.detail(id) })
    },
  })
}
```

## Infinite Scroll

```ts
export function useInfiniteProducts() {
  return useInfiniteQuery({
    queryKey: productKeys.lists(),
    queryFn: ({ pageParam = 1 }) => api.get(`/products?page=${pageParam}`),
    getNextPageParam: (last) => last.hasNextPage ? last.page + 1 : undefined,
    initialPageParam: 1,
  })
}
```
