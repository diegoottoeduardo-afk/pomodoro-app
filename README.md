# 🍅 Pomodoro Focus para Windows

Una aplicación moderna, intuitiva y personalizable para aplicar la técnica Pomodoro en tu computadora.

---

## 🚀 Cómo Iniciar la Aplicación

Tienes **tres formas fáciles** de usarla:

1. **Desde tu Escritorio (Recomendado):**
   - Ya se creó un acceso directo con icono de tomate llamado **`Pomodoro Focus`** en tu Escritorio de Windows.
   - Haz doble clic en él para abrir la aplicación directamente sin consolas negras ni ventanas adicionales.

2. **Desde la Carpeta:**
   - Haz doble clic en `iniciar_silencioso.vbs` o en `iniciar_pomodoro.bat`.

3. **Versión Web / Navegador:**
   - Si prefieres usarla en Google Chrome o Microsoft Edge, haz doble clic en `pomodoro.html`.

---

## ✨ Características Principales

- **Temporizador Inteligente:**
  - 🍅 **Enfoque:** 25 minutos por defecto.
  - ☕ **Pausa Corta:** 5 minutos.
  - 🌴 **Pausa Larga:** 15 minutos tras completar 4 ciclos de enfoque.
- **📌 Modo Siempre Visible (Always on Top):**
  - Haz clic en `📌 Fijar` para que la ventana permanezca visible sobre Word, PDFs, tu navegador o tu editor de código.
- **🗖 Modo Mini Flotante:**
  - Haz clic en `🗖 Mini` para contraer la aplicación en una barrita minimalista que no ocupa espacio en tu pantalla.
- **📋 Gestor de Tareas:**
  - Anota lo que tienes que hacer hoy, selecciona tu tarea activa y cuenta cuántos pomodoros te toma completarla.
- **🔔 Notificaciones y Sonidos Nativos:**
  - Recibe avisos en la esquina de Windows y acordes armónicos de campana al terminar cada intervalo.
- **📊 Estadísticas Diarias:**
  - Registra tus pomodoros completados hoy y tus minutos totales acumulados.
- **⌨️ Atajos de Teclado:**
  - `Espacio`: Iniciar / Pausar.
  - `R`: Reiniciar tiempo actual.
  - `S`: Saltar al siguiente bloque.
  - `M`: Alternar Modo Mini.
- **⚙️ Ajustes Personalizables:**
  - Configura los minutos que prefieras para cada etapa, activa o desactiva sonidos y alterna entre Modo Oscuro y Modo Claro.

---

## 📂 Archivos del Proyecto

- `pomodoro_app.py`: Código principal de la aplicación con CustomTkinter.
- `iniciar_silencioso.vbs`: Lanzador silencioso en segundo plano.
- `iniciar_pomodoro.bat`: Script de inicio rápido en lote.
- `crear_acceso_directo.ps1`: Script que generó el acceso directo en el Escritorio.
- `pomodoro.ico`: Icono de tomate personalizado de alta resolución.
- `pomodoro.html`: Versión web standalone con Web Audio y Notificaciones.
- `pomodoro_data.json`: Almacén automático de configuraciones, estadísticas y tareas.
