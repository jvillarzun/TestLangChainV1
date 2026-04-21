# Android CLI & Onboarding — Developer Guide

## Project Setup via CLI

```bash
# New project with Android Studio CLI
sdkmanager --install "platforms;android-35" "build-tools;35.0.0"

# Gradle wrapper commands
./gradlew assembleDebug          # build debug APK
./gradlew assembleRelease        # build release APK
./gradlew installDebug           # install on connected device
./gradlew test                   # run unit tests
./gradlew connectedAndroidTest   # run instrumented tests
./gradlew lint                   # run lint checks
./gradlew ktlintCheck            # kotlin style check
./gradlew ktlintFormat           # auto-format kotlin
```

## ADB Essential Commands

```bash
# Device management
adb devices                          # list connected devices
adb -s emulator-5554 shell          # shell into specific device

# App management
adb install -r app-debug.apk        # install (replace existing)
adb uninstall com.company.app       # uninstall
adb shell am start -n com.company.app/.MainActivity  # launch activity

# Logs
adb logcat -s "MyTag"               # filter by tag
adb logcat *:E                      # errors only
adb logcat | grep -i "exception"    # filter exceptions

# File transfer
adb push localfile.txt /sdcard/     # host → device
adb pull /sdcard/file.txt ./        # device → host

# Screen recording
adb shell screenrecord /sdcard/demo.mp4
adb pull /sdcard/demo.mp4 ./

# Network
adb reverse tcp:8080 tcp:8080       # reverse proxy for local API testing
```

## Onboarding Screen Template (Compose)

```kotlin
// OnboardingScreen.kt
data class OnboardingPage(
    val title: String,
    val description: String,
    val illustration: Int,  // drawable res
)

val ONBOARDING_PAGES = listOf(
    OnboardingPage("Bienvenido", "Gestiona tus pagos en segundos", R.drawable.il_welcome),
    OnboardingPage("Seguro",     "Tu dinero protegido 24/7",       R.drawable.il_security),
    OnboardingPage("Rápido",     "Transfiere en un tap",           R.drawable.il_fast),
)

@Composable
fun OnboardingScreen(onFinish: () -> Unit) {
    val pagerState = rememberPagerState(pageCount = { ONBOARDING_PAGES.size })
    val scope = rememberCoroutineScope()

    Column(modifier = Modifier.fillMaxSize()) {
        HorizontalPager(
            state = pagerState,
            modifier = Modifier.weight(1f),
        ) { page ->
            OnboardingPage(page = ONBOARDING_PAGES[page])
        }

        // Dots indicator
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.Center,
        ) {
            repeat(ONBOARDING_PAGES.size) { i ->
                Box(
                    modifier = Modifier
                        .padding(4.dp)
                        .size(if (pagerState.currentPage == i) 10.dp else 6.dp)
                        .clip(CircleShape)
                        .background(
                            if (pagerState.currentPage == i) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.surfaceVariant
                        )
                        .animateContentSize()
                )
            }
        }

        // CTA Button
        Button(
            onClick = {
                if (pagerState.currentPage < ONBOARDING_PAGES.size - 1) {
                    scope.launch { pagerState.animateScrollToPage(pagerState.currentPage + 1) }
                } else {
                    onFinish()
                }
            },
            modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp, vertical = 16.dp),
        ) {
            Text(if (pagerState.currentPage < ONBOARDING_PAGES.size - 1) "Siguiente" else "Comenzar")
        }
    }
}
```

## Feature Module Structure

```
features/onboarding/
├── data/
│   └── OnboardingPreferences.kt   # DataStore: hasSeenOnboarding
├── domain/
│   └── ShouldShowOnboardingUseCase.kt
├── presentation/
│   ├── OnboardingScreen.kt
│   ├── OnboardingViewModel.kt
│   └── OnboardingUiState.kt
└── navigation/
    └── OnboardingNavigation.kt     # addOnboardingGraph(navController)
```

## Navigation Integration

```kotlin
// In AppNavGraph, add before main graph:
fun NavGraphBuilder.addOnboardingGraph(
    navController: NavController,
    onOnboardingComplete: () -> Unit,
) {
    navigation(startDestination = OnboardingRoute, route = "onboarding_graph") {
        composable<OnboardingRoute> {
            OnboardingScreen(onFinish = {
                onOnboardingComplete()
                navController.navigate(HomeRoute) {
                    popUpTo("onboarding_graph") { inclusive = true }
                }
            })
        }
    }
}

// Decide at app start:
val startRoute = if (shouldShowOnboarding) "onboarding_graph" else HomeRoute
NavHost(navController, startDestination = startRoute) { ... }
```

## HTML Onboarding Preview Template

When you need to show an onboarding web preview for stakeholders or web app:

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Onboarding Preview</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, sans-serif; background: #0f172a; color: white; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .phone { width: 375px; min-height: 667px; background: white; border-radius: 40px; padding: 48px 24px 32px; box-shadow: 0 40px 80px rgba(0,0,0,0.5); position: relative; overflow: hidden; }
  .slide { display: none; text-align: center; flex-direction: column; align-items: center; justify-content: center; height: 100%; }
  .slide.active { display: flex; }
  .illustration { width: 200px; height: 200px; border-radius: 50%; margin-bottom: 32px; display: flex; align-items: center; justify-content: center; font-size: 80px; }
  h2 { font-size: 28px; font-weight: 700; color: #1e293b; margin-bottom: 12px; }
  p  { font-size: 16px; color: #64748b; line-height: 1.6; max-width: 280px; }
  .dots { display: flex; gap: 8px; margin: 32px 0; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #e2e8f0; transition: all 0.3s; }
  .dot.active { width: 24px; background: #6366f1; border-radius: 4px; }
  .btn { width: 100%; padding: 16px; background: #6366f1; color: white; border: none; border-radius: 16px; font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.1s; }
  .btn:active { transform: scale(0.98); }
</style>
</head>
<body>
<div class="phone">
  <div class="slide active" id="slide-0">
    <div class="illustration" style="background:#ede9fe">👋</div>
    <h2>Bienvenido</h2>
    <p>Gestiona tus pagos y transferencias en segundos.</p>
  </div>
  <div class="slide" id="slide-1">
    <div class="illustration" style="background:#dcfce7">🔒</div>
    <h2>100% Seguro</h2>
    <p>Tu dinero protegido con cifrado de nivel bancario.</p>
  </div>
  <div class="slide" id="slide-2">
    <div class="illustration" style="background:#fef3c7">⚡</div>
    <h2>Ultra Rápido</h2>
    <p>Transfiere en un tap. Disponible 24/7.</p>
  </div>
  <div class="dots">
    <div class="dot active" id="d0"></div>
    <div class="dot" id="d1"></div>
    <div class="dot" id="d2"></div>
  </div>
  <button class="btn" onclick="next()">Siguiente</button>
</div>
<script>
  let cur = 0;
  const total = 3;
  function next() {
    document.getElementById('slide-'+cur).classList.remove('active');
    document.getElementById('d'+cur).classList.remove('active');
    cur = (cur + 1) % total;
    document.getElementById('slide-'+cur).classList.add('active');
    document.getElementById('d'+cur).classList.add('active');
    if (cur === total - 1) document.querySelector('.btn').textContent = 'Comenzar';
  }
</script>
</body>
</html>
```
