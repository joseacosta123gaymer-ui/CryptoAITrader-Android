# App Android — Crypto AI Trader

Este módulo es el proyecto fuente nativo Android (Kotlin + Jetpack Compose). Se conecta al gateway HTTPS del servidor; no ejecuta Python ni Freqtrade dentro del teléfono.

## Compilar el APK

1. Instalar Android Studio estable, JDK 17 y Gradle 8.13 (o usar el workflow de GitHub Actions incluido).
2. Abrir con Android Studio la carpeta raíz `CryptoAITrader_Android` (la carpeta que contiene `settings.gradle.kts`).
3. Permitir que Gradle sincronice y descargue las dependencias.
4. Seleccionar `Build > Build Bundle(s) / APK(s) > Build APK(s)`.
5. Android Studio generará el APK de depuración en `app/build/outputs/apk/debug/`.

## Conectar

En la app, introducir la URL HTTPS configurada en `APP_DOMAIN` y el valor `APP_API_TOKEN` del `.env` del servidor.

El token se mantiene en memoria durante la sesión y no se guarda en texto plano. La app rechaza HTTP sin cifrar.

## Limitaciones explícitas de v0.2

- Es una app nativa de control y monitorización; el motor Freqtrade corre en el servidor.
- El control de Inicio/Pausa/Detener solo se habilita si el backend confirma `dry_run=true`.
- Esta versión no permite trading real ni configurar claves de exchange desde el móvil.
- No incluye todavía gráficos de velas interactivos ni consola de entrenamiento FreqAI.
