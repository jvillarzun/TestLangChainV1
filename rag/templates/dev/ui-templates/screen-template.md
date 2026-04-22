# Guía de Creación de Pantallas con DesignSystem

Para crear una nueva pantalla (ej. HomeScreen) dentro de este proyecto, sigue estos principios:

## 1. Estructura Base (`Screen`)

Usa siempre el componente `Screen` para manejar insets, barra de estado y top bar.

```kotlin
Screen(
    notchColor = Palette.Violet.at500,
    topBar = { Header(variant = HeaderVariant.HeaderMain(...)) }
) {
    // Contenido aquí (preferiblemente LazyColumn para scroll fluido)
}
```

## 2. Componentes de Cabecera y Balance

- **Balance**: Para mostrar el saldo principal o cupo utilizado.
- **BalanceResume**: Para resúmenes secundarios de facturación o ahorros.

## 3. Navegación y Acciones

- **CardButtonSmall / Medium**: Botones horizontales grandes para acciones de "Tarjetas".
- **ItemMenuShortcut**: Para cuadrículas de iconos de acciones rápidas. Usa `Symbol.codePoint` para el parámetro `symbol`.

## 4. Listados y Contenido Dinámico

- **ItemCashMovement**: Para historiales de transacciones.
- **Banner**: Para comunicaciones promocionales.

## 5. Foundations (Estilos)

- **Palette**: Usa colores definidos (ej. `Palette.Violet.at500`).
- **Dimens**: Usa espacios estándar (ej. `Dimens.at16`, `Dimens.at24`).
- **Typography**: Usa la jerarquía de texto (ej. `Typography.Label.large`, `Typography.Body.smallSemiBold`).

## Ejemplo de Mock rápido

```kotlin
item {
    Balance(
        name = "Nombre",
        detail = "Detalle",
        amount = "$ 0",
        style = BalanceStyle.Purple
    )
}
```
