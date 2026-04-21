# Jetpack Compose — Patterns & Best Practices

## Component Design Rules

- **Stateless composables** receive state as params, emit events via lambdas — never read ViewModel directly
- **Hoisting**: state lives in the highest composable that needs it
- **Slots**: use `content: @Composable () -> Unit` params for flexible layouts
- Prefix internal composables with `private` or put in same file as the screen

## Reusable Component Template

```kotlin
@Composable
fun AppButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isLoading: Boolean = false,
) {
    Button(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled && !isLoading,
    ) {
        if (isLoading) {
            CircularProgressIndicator(
                modifier = Modifier.size(16.dp),
                strokeWidth = 2.dp,
                color = MaterialTheme.colorScheme.onPrimary,
            )
        } else {
            Text(text)
        }
    }
}
```

## LazyColumn Best Practices

```kotlin
@Composable
fun ItemList(
    items: List<Item>,
    onItemClick: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier,
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(
            items = items,
            key = { it.id },  // ALWAYS provide stable keys
        ) { item ->
            ItemCard(item = item, onClick = { onItemClick(item.id) })
        }
    }
}
```

## Side Effects

```kotlin
// Launch once when composable enters composition
LaunchedEffect(Unit) {
    viewModel.loadData()
}

// React to state changes
LaunchedEffect(uiState.error) {
    uiState.error?.let { snackbarHostState.showSnackbar(it) }
}

// Cleanup on dispose
DisposableEffect(lifecycleOwner) {
    val observer = LifecycleEventObserver { _, event -> ... }
    lifecycleOwner.lifecycle.addObserver(observer)
    onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
}
```

## Theme Setup

```kotlin
// ui/theme/Color.kt
val MachBlue = Color(0xFF1565C0)
val MachBlueContainer = Color(0xFFD0E4FF)

// ui/theme/Theme.kt
@Composable
fun AppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) darkColorScheme(
        primary = MachBlue,
        primaryContainer = MachBlueContainer,
    ) else lightColorScheme(
        primary = MachBlue,
        primaryContainer = MachBlueContainer,
    )
    MaterialTheme(colorScheme = colorScheme, content = content)
}
```

## Adaptive Layouts

```kotlin
@Composable
fun AdaptiveHomeScreen() {
    val windowSize = calculateWindowSizeClass(LocalActivity.current)
    when (windowSize.widthSizeClass) {
        WindowWidthSizeClass.Compact  -> HomePhoneLayout()
        WindowWidthSizeClass.Medium   -> HomeTabletLayout()
        WindowWidthSizeClass.Expanded -> HomeDesktopLayout()
    }
}
```

## Performance Tips
- `remember` + `derivedStateOf` for computed values derived from state
- `key()` in `LazyColumn` to preserve item state across recompositions
- `@Stable` / `@Immutable` on data classes passed to composables
- Avoid reading `State` inside lambdas that run during composition (use `rememberUpdatedState`)
- Use `Modifier.graphicsLayer` for animations instead of rebuilding the tree
