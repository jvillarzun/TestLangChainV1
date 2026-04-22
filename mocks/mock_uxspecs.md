# UXSPECS.md

## 1. Principios de diseño

1. **Interactividad inmediata**: El contador debe actualizar el número de clics de manera instantánea para proporcionar una experiencia de interacción fluida.
2. **Simplicidad y claridad**: El diseño del contador debe ser minimalista y fácil de entender, evitando confusiones o sobrecarga de información.
3. **Responsividad universal**: El contador debe ser visible y funcional en todos los dispositivos y tamaños de pantalla, garantizando una experiencia óptima para todos los usuarios.
4. **Transparencia en la actualización**: El sistema debe proporcionar retroalimentación clara sobre el éxito o fracaso de la actualización del contador, asegurando que el usuario siempre esté informado.
5. **Coherencia con el diseño de MACHBank**: El contador debe integrarse de manera coherente con el diseño existente de la página principal de MACHBank, manteniendo la identidad visual de la marca.

## 2. Mapa de flujos

### US-01: Ver el contador
```
[Página principal] --carga del usuario--> [Página principal con contador visible] --usuario ve el número de clics--
```

### US-02: Incrementar el contador
```
[Página principal con contador visible] --usuario hace clic en el botón "Sumar +1"--> [Página principal con estado de carga] --sistema actualiza el contador--> [Página principal con contador actualizado]
```

### US-03: Actualización en tiempo real
```
[Página principal con contador visible] --sistema recibe actualización--> [Página principal con contador actualizado] --usuario ve el nuevo número de clics--
```

### US-04: Error en la actualización
```
[Página principal con contador visible] --usuario hace clic en el botón "Sumar +1"--> [Página principal con estado de error] --sistema muestra mensaje de error--> [Página principal con contador visible y mensaje de error]
```

### US-05: Estado vacío
```
[Página principal con contador visible] --no hay clics--> [Página principal con mensaje de "0 clics"]
```

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