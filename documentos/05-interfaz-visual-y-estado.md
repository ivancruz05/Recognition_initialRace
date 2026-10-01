# Interfaz visual y estado del proyecto

## Estado visual observado

Existe el documento visual `mockups atletismo.pdf` con pantallas de dashboard, carga/procesamiento de pruebas, resultados, atletas, reportes, biblioteca y configuración. En el repositorio inspeccionado no hay un frontend separado ni archivos de interfaz web (`HTML`, `CSS`, JavaScript o TypeScript). La API de DRF no equivale a una interfaz visual propia.

Por tanto, hay una propuesta visual, pero la implementación frontend está **pendiente de incorporación al repositorio**.

## Qué puede diseñarse mientras llegan los datos

- Estructura de navegación y acceso por tipo de usuario, si los roles finales lo requieren.
- Pantallas de autenticación: registro, login y sesión actual.
- Vistas de atletas basadas en los campos existentes.
- Componentes reutilizables, diseño adaptable y accesibilidad.
- Estados de carga, errores, listas vacías y resultados aún no disponibles.
- Prototipos con contenido ficticio claramente identificado.

## Qué depende de las decisiones del proyecto

La tecnología frontend y la identidad visual deben definirse con el equipo. El núcleo visual del anteproyecto es la salida de arranque: carga de video/R3D, vista del proceso, ángulos biomecánicos, comparación con rangos y recomendaciones. Otras pantallas de los mockups (pruebas de otras distancias, biblioteca, reportes generales) deben priorizarse según el alcance aprobado.

Las pantallas muestran también velocidades, cadencia y zancada, mientras que el anteproyecto se centra en ángulos de la salida de arranque. Se deben validar esas métricas adicionales antes de incluirlas como indicadores del producto.

## Contrato con el backend

La interfaz debería consumir las rutas de `backend/config/urls.py` a través de una capa cliente, sin duplicar reglas del dominio. Para autenticación por sesión, se deberá coordinar el envío de cookies y CSRF. Los DTOs de análisis se definirán según el formato `results.json` propuesto y el dataset verificado, no solo por los valores de ejemplo de los mockups.

Las funciones representadas en los mockups pero aún no conectadas con backend están registradas en la [matriz de requisitos y trazabilidad](07-requisitos-y-trazabilidad.md).

## Estado global del repositorio

| Componente | Estado |
|---|---|
| Backend base y configuración Django | Implementado |
| Autenticación de cuentas por sesión | Implementada y con pruebas |
| Gestión básica de atletas | Implementada y con pruebas |
| Análisis de salida de arranque | Alcance académico definido en anteproyecto; pipeline de software pendiente de datos y diseño técnico |
| Frontend/parte visual | Pendiente de crear e integrar |
| Definición analítica basada en datos | Pendiente de recibir y estudiar los datos |
