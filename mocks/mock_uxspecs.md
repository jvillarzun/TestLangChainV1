# UXSPECS.md - Diseño del Generador de Tips

## 1. Principios de diseño
- Componente minimalista, centrado y con alto contraste.
- Feedback visual claro durante la simulación de carga.

## 2. Mapa de flujos
1. **Estado Inicial:** Se muestra solo el botón "Dame un Tip Financiero".
2. **Interacción:** El usuario hace clic. El botón se deshabilita temporalmente.
3. **Carga:** Aparece el texto "Buscando el mejor tip para ti...".
4. **Resultado:** El texto de carga es reemplazado por el tip financiero real.

## 3. Wireframes (Texto)

**Estado Inicial:**
```text
[ BOTÓN: Dame un Tip Financiero ]
```

**Estado Cargando:**

```text
[ BOTÓN: Buscando... ] (Deshabilitado)
Buscando el mejor tip para ti...
```

**Estado Final:**

```text
[ BOTÓN: Dame otro Tip ]
💡 Tip: "Paga tus tarjetas antes de la fecha de facturación."
```

## 4. Especificación de UI
- Botón: Usar la clase bg-mach-purple text-white px-4 py-2 rounded-lg.
- Texto del Tip: Mostrar en negrita (font-bold) con un ícono o emoji de un foco (💡) al lado.
- Ubicación: Insertar el componente en el archivo page.tsx antes del Footer.

status: READY_FOR_REVIEW
