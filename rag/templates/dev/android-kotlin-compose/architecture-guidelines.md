# Android Kotlin Compose — Architecture Guidelines

## Project Structure (Clean Architecture + MVVM)

```
app/
├── data/
│   ├── local/          # Room DB, DataStore
│   │   ├── dao/
│   │   ├── entity/
│   │   └── AppDatabase.kt
│   ├── remote/         # Retrofit, API
│   │   ├── api/
│   │   ├── dto/
│   │   └── NetworkModule.kt
│   └── repository/     # Repository implementations
├── domain/
│   ├── model/          # Domain models (pure Kotlin, no Android)
│   ├── repository/     # Repository interfaces
│   └── usecase/        # One class per use case
├── presentation/
│   ├── ui/
│   │   ├── screen/     # One folder per screen
│   │   │   ├── HomeScreen.kt
│   │   │   ├── HomeViewModel.kt
│   │   │   └── HomeUiState.kt
│   │   ├── components/ # Reusable composables
│   │   └── theme/      # MaterialTheme, Colors, Typography
│   └── navigation/
│       └── AppNavGraph.kt
└── di/                 # Hilt modules
```

## ViewModel Pattern

```kotlin
@HiltViewModel
class HomeViewModel @Inject constructor(
    private val getItemsUseCase: GetItemsUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        loadItems()
    }

    private fun loadItems() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            getItemsUseCase()
                .onSuccess { items -> _uiState.update { it.copy(items = items, isLoading = false) } }
                .onFailure { error -> _uiState.update { it.copy(error = error.message, isLoading = false) } }
        }
    }
}

data class HomeUiState(
    val items: List<Item> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)
```

## Screen Pattern

```kotlin
@Composable
fun HomeScreen(
    viewModel: HomeViewModel = hiltViewModel(),
    onNavigateToDetail: (String) -> Unit,
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    HomeContent(
        uiState = uiState,
        onItemClick = onNavigateToDetail,
    )
}

@Composable
private fun HomeContent(
    uiState: HomeUiState,
    onItemClick: (String) -> Unit,
) {
    when {
        uiState.isLoading -> LoadingIndicator()
        uiState.error != null -> ErrorMessage(uiState.error)
        else -> ItemList(items = uiState.items, onItemClick = onItemClick)
    }
}
```

## Navigation (Type-safe Nav)

```kotlin
@Serializable object HomeRoute
@Serializable data class DetailRoute(val id: String)

@Composable
fun AppNavGraph(navController: NavHostController) {
    NavHost(navController, startDestination = HomeRoute) {
        composable<HomeRoute> {
            HomeScreen(onNavigateToDetail = { id ->
                navController.navigate(DetailRoute(id))
            })
        }
        composable<DetailRoute> { backStackEntry ->
            val route: DetailRoute = backStackEntry.toRoute()
            DetailScreen(id = route.id)
        }
    }
}
```

## Dependency Injection (Hilt)

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides @Singleton
    fun provideRetrofit(): Retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.BASE_URL)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    @Provides @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService =
        retrofit.create(ApiService::class.java)
}
```

## Key Rules
- No Android imports in domain layer
- ViewModels never hold references to Context or View
- Use `StateFlow` + `collectAsStateWithLifecycle()` (not `collectAsState()`)
- Repository implementations live in data layer, interfaces in domain
- Each screen has its own UiState sealed class or data class
- Hilt for DI — no manual service locators
