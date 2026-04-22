# UXSPECS.md — Contador Interactivo MACHBank

## 1. Principios de diseño

**Alineados con el PRD del proyecto de Contador Interactivo**

1. **Interactividad Inmediata**: El contador debe actualizar el número de clics de manera instantánea (<200ms) para proporcionar una experiencia de interacción fluida y satisfactoria. La respuesta visual debe ser inmediata, con feedback táctil/visual al hacer clic.

2. **Minimalismo y Claridad**: El diseño del contador debe ser simple y autoexplicativo, evitando confusiones o sobrecarga cognitiva. El usuario debe entender instantáneamente qué hace el contador y cómo interactuar con él sin instrucciones adicionales.

3. **Responsividad Universal**: El contador debe ser visible, táctil y funcional en todos los dispositivos (mobile, tablet, desktop) y tamaños de pantalla, garantizando una experiencia óptima desde smartwatches hasta pantallas 4K.

4. **Integración No-Disruptiva**: El contador debe incorporarse de manera orgánica en la página principal de MACHBank sin alterar el flujo de navegación existente ni competir visualmente con CTAs principales. Debe sentirse como una extensión natural del diseño actual.

5. **Escalabilidad y Performance**: El diseño debe soportar altos volúmenes de interacción (objetivo: 1000+ clics/mes) sin degradación de la experiencia. Las animaciones deben ser fluidas incluso con tráfico concurrente.

6. **Feedback Transparente**: Proporcionar retroalimentación clara sobre el éxito o error en la actualización del contador mediante microinteracciones, íconos de estado y mensajes contextuales sin modales intrusivos.

## 2. Mapa de flujos de usuario

**Basados en User Stories del PRD**

### US-01: Visualización inicial del contador
```
[Usuario carga página principal] 
    ↓ 
[Sistema carga contador desde backend] 
    ↓ 
[Contador visible con número actual de clics] 
    ↓ 
[Usuario comprende el contador inmediatamente]
```
**Tiempo objetivo**: <500ms desde carga de página
**Criterio de aceptación**: CA-01-01

---

### US-02: Interacción — Incrementar el contador
```
[Usuario ve contador] 
    ↓ 
[Usuario hace clic en botón "Sumar +1"] 
    ↓ 
[Feedback visual inmediato: botón presionado + animación] 
    ↓ 
[Petición al backend (optimistic update)] 
    ↓ 
[Con3.1. Desktop — Página principal con contador (Estado normal)
```
┌─────────────────────────────────────────────────────────────────────┐
│ [Logo MACHBank]    [Productos] [Empresas] [Ayuda]    [Avatar] [🔔] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   [Banner principal/Hero section]                                   │
│                                                                     │
│   ┌─────────────────────────────────────┐                          │
│   │  📊 Contador Interactivo             │  ← Widget del contador  │
│   │                                      │                          │
│   │  Total de clics realizados:          │                          │
│   │  ┌──────────┐                        │                          │
│   │  │   1,247  │  ← Número con formato │                          │
│   │  └──────────┘                        │                          │
│   │                                      │                          │
│   │  [  +  Sumar +1  ]  ← Botón CTA     │                          │
│   │     (Primary button)                 │                          │
│   │                                      │                          │
│   │  Actualizado hace 2s  ← Timestamp   │                          │
│   └─────────────────────────────────────┘                          │
│                                                                     │
│   [Resto del contenido de la página principal]                     │
│                                                                     │
│ [Footer con links]                                                  │
└─────────────────────────────────────────────────────────────────────┘
```
**Ubicación**: Widget flotante o integrado en hero section
**Diseño**: Card con sombra sutil, padding 24px, border-radius 12px

---

### 3.2. Desktop — Estado de carga (Optimistic update)
```
┌─────────────────────────────────────────────────────────────────────┐
│ [Logo MACHBank]    [Productos] [Empresas] [Ayuda]    [Avatar] [🔔] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────┐                          │
│   │  📊 Contador Interactivo             │                          │
│   │                                      │                          │
│   │  Total de clics realizados:          │                          │
│   │  ┌──────────┐                        │                          │
│   │  │   1,248  │  ← Ya incrementado     │                          │
│   │  └──────────┘     (optimistic)       │                          │
│   │                                      │                          │
│   │  [  ⏳  Guardando...  ]  ← Disabled │                          │
│   │     (Loading spinner)                │                          │
│   │                                      │                          │
│   │  Actualizando...  ← Feedback        │                          │
│   └─────────────────────────────────────┘                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```
**Duración**: <200ms (imperceptible si la red es rápida)
**Feedback**: Botón con spinner, texto "Guardando..."

---

### 3.3. Desktop — Confirmación exitosa
```
┌─────────────────────────────────────────────────────────────────────┐
│   ┌─────────────────────────────────────┐                          │
│   │  📊 Contador Interactivo             │                          │
│   │                                      │                          │
│   │  Total de clics realizados:          │                          │
│   │  ┌──────────┐  ✓  ← Checkmark verde│                          │
│   │  │   1,248  │     (fade out 1s)     │                          │
│   │  └──────────┘                        │                          │
│   │       ↑ Animación de "count up"     │                          │
│   │                                      │                          │
│   │  [  +  Sumar +1  ]  ← Re-enabled    │                          │
│   │                                      │                          │
│   │  Actualizado ahora  ← Timestamp     │                          │
│   └─────────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────┘
```
**Microinteracción**: 
- Número se anima de 1,247 → 1,248 con efecto de "count up"
- Checkmark verde aparece y desaparece en 1 segundo
- Botón vuelve a estado normal

---

### 3.4. Desktop — Error en actualización
```
┌─────────────────────────────────────────────────────────────────────┐
│   ┌─────────────────────────────────────┐                          │
│   │  📊 Contador Interactivo             │                          │
│   │                                      │                          │
│   │  Total de clics realizados:          │                          │
│   │  ┌──────────┐                        │                          │
│   │  │   1,247  │  ← Revertido al valor │                          │
│   │  └──────────┘     anterior           │                          │
│   │                                      │                          │
│   │  [  +  Sumar +1  ]                  │                          │
│   │                                      │                          │
│   │  ⚠️  Error al actualizar. [Reintentar] ← Toast temporal (5s)  │
│   └─────────────────────────────────────┘                          │
│   Toast notification (bottom-right):                                │
│   ┌────────────────────────────────┐                               │
│   │ ⚠️  No se pudo actualizar      │                               │
│   │    el contador. Intenta de     │                               │
│   │    nuevo o recarga la página.  │                               │
│   │                   [ ✕ Cerrar ] │                               │
│   └────────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```
**Fe4.1. CounterWidget (Componente principal)
**Nombre del componente**: `CounterWidget`

**Props**:
- `initialCount: number` — Valor inicial del contador desde el backend
- `onIncrement: () => Promise<number>` — Función async para incrementar el contador
- `updateInterval?: number` — Intervalo de polling en ms (default: 5000)
- `enableRealtime?: boolean` — Si true, usa WebSockets en lugar de polling

**Estados internos**:
- `count: number` — Valor actual del contador
- `isLoading: boolean` — true durante la petición de incremento
- `error: string | null` — Mensaje de error si la petición falla
- `lastUpdated: Date` — Timestamp de última actualización

**Eventos**:
- `onClickSuccess` — Se dispara cuando el incremento se confirma
- `onClickError` — Se dispara cuando falla la petición

**Variantes**:
- `default` — Card con sombra y padding estándar
- `compact` — Versión más pequeña para sidebars
- `minimal` — Solo número y botón, sin decoraciones

**Comportamiento responsive**:
- Desktop (>768px): Card de 400px de ancho, padding 24px
- Tablet (768px-1024px): Card de 90% ancho, padding 20px
- Mobile (<768px): Card full-width, padding 16px, botón full-width

---

### 4.2. CounterDisplay (Sub-componente)
**Nombre del componente**: `CounterDisplay`

**Props**:
- `value: number` — Número a mostrar
- `isAnimating: boolean` — Si true, anima el cambio de valor
- `size?: 'small' | 'medium' | 'large'` — Tamaño del número

**Animaciones**:
- `countUp`: Anima de valor anterior a nuevo valor (duración: 300ms, easing: ease-out)
- `pulse`: Efecto de "pulse" cuando se actualiza por otro usuario (duración: 600ms)

**Formato**:
- Números >999: Separador de miles (ej: 1,247)
- Números >999,999: Formato abreviado (ej: 1.2M)

**Estilos**:
- Font: Monospace (para evitar layout shift)
- Size large: 48px/3rem
- Size medium: 32px/2rem
- Size small: 24px/1.5rem

---

### 4.3. IncrementButton (Sub-componente)
**Nombre del componente**: `IncrementButton`

**Props**:
- `onClick: () => void` — Handler del clic
- `isLoading: boolean` — Muestra spinner cuando true
- `disabled: boolean` — Deshabilita el botón
- `variant?: 'primary' | 'secondary'` — Estilo del botón

**Estados visuales**:
- `idle`: Color primario de MACHBank, hover con efecto de elevación
- `loading`: Spinner animado, cursor wait, disabled
- `disabled`: Opacidad 50%, cursor not-allowed
- `success`: Checkmark verde efímero (1s)

**Dimensiones**:
- Desktop: 160px × 48px
- Mobile: 100% × 56px (para cumplir touch target de 48px mínimo)

**Accesibilidad**:
- `aria-label`: "Incrementar contador"
- `aria-pressed`: true cuando isLoading
- `aria-disabled`: true cuando disabled
- Focus visible con outline de alto contraste

---

### 4.4. ErrorToast (Sub-componente)
**Nombre del componente**: `ErrorToast`

**Props**:
- `message: string` — Texto del error
- `onRetry?: () => void` — Callback para botón "Reintentar"
- `onClose: () => void` — Callback para cerrar el toast
- `duration?: number` — Auto-cierre en ms (default: 5000)

**Comportamiento**:
- Aparece con animación slide-in desde bottom-right
- Auto-cierre después de `duration` ms
- Cierre manual con botón "✕"
- Se apila si hay múltiples errores (máximo 3 visibles)

**Estilos**:
- Fondo: `#FEE2E2` (red-100)
- Borde: `#DC2626` (red-600)
- Ícono: ⚠️ en color `#DC2626`
- Shadow: `0 4px 12px rgba(0,0,0,0.15)`

---

### 4.5. TimestampLabel (Sub-componente)
**Nombre del componente**: `TimestampLabel`

**Props**:
- `date: Date` — Fecha de última actualización
- `format?: 'relative' | 'absolute'` — Formato del timestamp

**Formato relativo**:
- Hace <1 min: "Actualizado ahora"
- Hace 1-59 min: "Actualizado hace X min"
- Hace 1-23 hrs: "Actualizado hace X hrs"
- Hace >24 hrs: "Actualizado hace X días"
icrocopy

### Textos principales
- **Título del widget**: "Contador Interactivo" o "Contador de Clics Comunitario"
- **Label del contador**: "Total de clics realizados:" (desktop) / "Total de clics:" (mobile)
- **Texto del botón**: "+ Sumar +1" (desktop) / "+ 1" (mobile, si es muy estrecho)
- **Estado vacío (0 clics)**: "0 clics — Sé el primero en hacer clic"

### Feedback de estado
- **Cargando**: "Guardando..." (dentro del botón)
- **Éxito**: Checkmark verde sin texto (visual feedback)
- **Timestamp reciente**: "Actualizado ahora"
- **Timestamp >1 min**: "Actualizado hace 5 min"

### Mensajes de error
- **Error genérico**: "No se pudo actualizar el contador. Intenta de nuevo o recarga la página."
- **Error de red**: "Sin conexión a internet. Revisa tu conexión e intenta nuevamente."
- **Error del servidor**: "El servidor no responde. Estamos trabajando en solucionarlo."
- **Timeout**: "La petición tardó demasiado. Por favor, intenta de nuevo."

### Tooltips (hover/long-press)
- **Botón "+1"**: "Incrementa el contador en 1 clic"
- **Número del contador**: "Clics totales de todos los usuarios"
- **Timestamp**: "Última actualización del contador"

### CTAs y enlaces
- **Botón "Reintentar"**: "Reintentar" (texto inline en mensaje de error)
- **Cerrar error**: "✕" (ícono, con aria-label "Cerrar mensaje")

### Tono y voz
- **Tono**: Amigable, directo, sin jerga técnica
- **Voz**: Primera persona plural ("Estamos trabajando...") para errores del sistema
- **Principio**: Mensajes cortos (<20 palabras), accionables, sin culpar al usuario

---

## 6. Accesibilidad (WCAG 2.1 AA)

### Contraste de color
- **Texto principal**: Ratio mínimo 4.5:1 con el fondo (cumple AA)
- **Números del contador**: Ratio mínimo 7:1 (cumple AAA para legibilidad crítica)
- **Botones**: Ratio mínimo 4.5:1 en todos los estados (normal, hover, disabled)
- **Mensajes de error**: Fondo y texto con ratio >4.5:1

### Navegación por teclado
- **Tab order**: Botón "+1" debe ser alcanzable con Tab
- **Enter/Space**: Activan el botón de incremento
- **Focus visible**: Outline de 2px con color de alto contraste (#2563EB)
- **Escape**: Cierra el toast de error si está visible
- **Skip links**: Permitir saltar el contador si el usuario no quiere interactuar

### ARIA y semántica
```html
<div role="region" aria-label="Contador interactivo de clics">
  <div role="status" aria-live="polite" aria-atomic="true">
    <span id="counter-label">Total de clics realizados:</span>
    <span aria-labelledby="counter-label">1,247</span>
  </div>
  
  <button 
    aria-label="Incrementar contador en 1"
    aria-pressed="false"
    aria-disabled="false">
    + Sumar +1
  </button>
  
  <div role="timer" aria-live="off">
    Actualizado hace 2 minutos
  </div>
</div>
```

**Atributos clave**:
- `aria-live="polite"` en el número para anunciar cambios a screen readers
- `role="status"` para actualizaciones de estado
- `aria-pressed` para indicar estado del botón durante loading
- `aria-disabled` en lugar de `disabled` HTML para mantener focusable

### Reducción de movimiento
- **`prefers-reduced-motion: reduce`**: Desactivar todas las animaciones
- Reemplazar animaciones de "count up" con cambio instantáneo
- Eliminar efectos de "pulse" y transiciones
- Mantener feedback visual estático (checkmark sin fade)

### Lectores de pantalla
- Anunciar incrementos: "Contador actualizado a 1,248 clics"
- Anunciar errores: "Error: No se pudo actualizar el contador. Reintentar disponible."
- No anunciar actualizaciones de otros usuarios (evitar spam)

### Touch targets (Mobile)
- **Tamaño mínimo**: 48px × 48px (cumple WCAG 2.5.5)
- **Espaciado**: Mínimo 8px entre elementos interactivos
- **Área de toque**: Botón ocupa 100% del ancho en mobile para facilitar tapping

### Estados de alta legibilidad
- **Modo de alto contraste**: Respetar configuración del sistema
- **Font scaling**: Soportar zoom hasta 200% sin pérdida de funcionalidad
- **Dark mode**: Ajustar colores para mantener contraste en tema oscuro

---

## 7. Consideraciones de diseño técnico

### Performance
- **Lazy loading**: Cargar el widget solo cuando sea visible en viewport
- **Debouncing**: Prevenir spam de clics (máximo 1 clic por segundo)
- **Optimistic updates**: Actualizar UI antes de confirmar con backend
- **Caching**: Cachear el último valor conocido en localStorage

### Animaciones eficientes
- **Hardware acceleration**: Usar `transform` y `opacity` en lugar de `top/left`
- **RequestAnimationFrame**: Para animaciones smooth
- **CSS animations**: Preferir sobre JavaScript cuando sea posible

### Estados de red
- **Offline detection**: Mostrar badge "Sin conexión" si no hay internet
- **Retry automático**: Reintentar peticiones fallidas con exponential backoff
- **Timeout**: 5 segundos máximo por petición

### Analytics y métricas
- **Eventos a trackear**:
  - `counter_viewed`: Cuando el widget entra en viewport
  - `counter_clicked`: Cuando el usuario hace clic (antes de petición)
  - `counter_success`: Cuando el incremento se confirma
  - `counter_error`: Cuando falla la petición (incluir tipo de error)
  - `counter_time_to_update`: Latencia desde clic hasta confirmación

---
│  │   └────────┘             ││
│  │                          ││
│  │  [ + Sumar +1 ]          ││
│  │  (Botón full-width)      ││
│  │                          ││
│  │  Actualizado hace 5s     ││
│  └──────────────────────────┘│
│                              │
│  [Contenido principal]       │
│                              │
└──────────────────────────────┘
```
**Adaptaciones mobile**:
- Botón full-width para fácil tapping (mínimo 48px altura)
- Número más grande y legible
- Card ocupa 90% del ancho de pantalla
- Padding reducido pero mantiene respiro visualestra "0 clics"] 
    ↓ 
[Tooltip/CTA: "Sé el primero en hacer clic"] 
    ↓ 
[Animación sutil de "call-to-action"]
```
**Propósito**: Gamificación para incentivar primera interacción

## 3. Wireframes en texto

### Página principal con contador visible
```
┌──────────────────────────────────┐
│ [Logo]        [Nav] [Avatar]     │
├──────────────────────────────────┤
│ Contador de clics: 0           │
│ [Botón "Sumar +1"]              │
│                                  │
│ [Footer]                        │
└──────────────────────────────────┘
```

### Página principal con estado de carga
```
┌──────────────────────────────────┐
│ [Logo]        [Nav] [Avatar]     │
├──────────────────────────────────┤
│ Contador de clics: ...          │
│ [Icono de carga]                │
│                                  │
│ [Footer]                        │
└──────────────────────────────────┘
```

### Página principal con contador actualizado
```
┌──────────────────────────────────┐
│ [Logo]        [Nav] [Avatar]     │
├──────────────────────────────────┤
│ Contador de clics: X           │
│ [Botón "Sumar +1"]              │
│                                  │
│ [Footer]                        │
└──────────────────────────────────┘
```

### Página principal con mensaje de error
```
┌──────────────────────────────────┐
│ [Logo]        [Nav] [Avatar]     │
├──────────────────────────────────┤
│ Error al actualizar el contador│
│ [Mensaje de error]              │
│                                  │
│ [Botón "Intentar de nuevo"]    │
│ [Footer]                        │
└──────────────────────────────────┘
```

## 4. Especificación de componentes

### Contador
- Nombre: `Counter`
- Props:
  - `count`: número de clics actuales
  - `onIncrement`: función a llamar cuando se hace clic en el botón "Sumar +1"
- Estados:
  - `loading`: muestra un icono de carga
  - `error`: muestra un mensaje de error
- Comportamiento en mobile vs desktop: el contador se ajusta al ancho de la pantalla, manteniendo la proporción y la legibilidad.

### Botón "Sumar +1"
- Nombre: `IncrementButton`
- Props:
  - `onClick`: función a llamar cuando se hace clic en el botón
- Estados:
  - `disabled`: deshabilita el botón y cambia el color
- Comportamiento en mobile vs desktop: el botón se ajusta al ancho de la pantalla, manteniendo la proporción y la legibilidad.

## 5. Copy y mensajes de error

- Mensaje de éxito: "Contador actualizado con éxito"
- Mensaje de error: "Error al actualizar el contador. Por favor, inténtelo de nuevo"
- Label del contador: "Contador de clics: X"
- Tooltip del botón "Sumar +1": "Incrementa el contador en 1"
- Mensaje de estado vacío: "0 clics"

## 6. Accesibilidad

- Contraste de color: el texto y los elementos interactivos tienen un contraste de color mínimo de 4.5:1 con el fondo.
- Navegación por teclado: el contador y el botón "Sumar +1" pueden ser navegados y activados mediante el teclado.
- ARIA labels para screen readers: el contador y el botón "Sumar +1" tienen etiquetas ARIA para ser leídos por lectores de pantalla.

status: READY_FOR_REVIEW