# PRDSPECS.md - Generador de Tips Financieros

## 1. Resumen ejecutivo
Se requiere un botón simple en la página principal que, al ser presionado, entregue un consejo financiero rápido a los usuarios. El objetivo es probar la interactividad básica y la simulación de servicios.

## 2. Solución propuesta
Un componente con un botón y un área de texto. Al hacer clic, se debe simular una llamada a una API (Mock-Driven Development) que tarde medio segundo y luego devuelva un texto al azar.

## 3. User Stories
- **US-01:** Como usuario, quiero ver un botón que diga "Dame un Tip Financiero".
- **US-02:** Como usuario, quiero ver un texto que diga "Cargando..." mientras el sistema "busca" el tip.
- **US-03:** Como usuario, quiero leer el consejo una vez que la carga finalice.

## 4. Requisitos Técnicos (Mock)
- El Agente Dev debe crear un array estático con al menos 3 tips financieros (ej. "Evita los gastos hormiga").
- Debe existir una función asíncrona simulada (`setTimeout`) que devuelva uno de estos tips.

status: READY_FOR_REVIEW