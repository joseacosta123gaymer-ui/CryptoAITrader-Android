# Crypto AI Trader Android — adaptación de Freqtrade

**Versión del paquete: 0.2.0**

Este proyecto convierte el Freqtrade que compartiste en la base de un sistema controlable desde una app Android nativa. El motor Python no se ejecuta en el teléfono: corre en un servidor Linux mediante Docker. Android se conecta por HTTPS a un gateway propio y protegido.

## Qué incluye

- El código fuente de Freqtrade del ZIP que compartiste, conservado dentro de `freqtrade/`.
- Imagen Docker basada en ese código, con las dependencias opcionales de FreqAI instaladas.
- Configuración inicial generada de forma segura: **Spot, Dry-run, cartera virtual de 1.000 USDT, 10 pares, máximo 3 posiciones y bot inicialmente detenido**.
- Estrategia inicial educativa `CryptoAIBaseline` (EMA 12/26 + RSI), para validar el flujo de Dry-run. No promete rentabilidad.
- Gateway FastAPI que solo permite consultar el dashboard, posiciones, historial, pares y velas, además de iniciar/pausar/detener el bot.
- Gateway protegido por token propio; la contraseña interna de Freqtrade nunca se entrega a Android.
- Caddy como proxy HTTPS automático. La API de Freqtrade no publica puertos al exterior.
- App Android nativa escrita en Kotlin + Jetpack Compose.
- Workflow de GitHub Actions para compilar el APK de depuración al subir el proyecto a GitHub.
- Pruebas automatizadas del gateway y del generador de configuración.

**FreqAI queda instalado como dependencia, pero no está activado para tomar decisiones en esta versión.** Antes de usar un modelo de aprendizaje real hay que preparar una estrategia FreqAI específica, descargar datos, entrenar y validar resultados fuera de muestra. La estrategia inicial es una referencia de simulación, no un modelo que aprende por sí mismo.

## Arquitectura

```text
App Android (Kotlin / HTTPS)
          |
          v
Caddy (TLS automático, 443)
          |
          v
Gateway FastAPI (token de app)
          |
          | red privada Docker + Basic Auth interno
          v
Freqtrade + FreqAI (Dry-run / Spot)
          |
          v
Exchange (solo datos públicos en la configuración inicial)
```

El puerto 8080 de Freqtrade y el 8000 del gateway no se publican directamente a Internet. Solo Caddy publica 80/443. La documentación oficial de Freqtrade recomienda no exponer su API directamente a Internet y proteger el acceso remoto mediante VPN o proxy seguro: https://docs.freqtrade.io/en/stable/rest-api/.

## Requisitos del servidor

- VPS o servidor Linux con Docker Engine y Docker Compose plugin.
- Un dominio o subdominio cuyo registro DNS A apunte a la IP pública del servidor.
- Puertos TCP 80 y 443 accesibles desde Internet para que Caddy emita y renueve TLS.
- Conexión a Internet saliente para descargar imagen/dependencias y consultar mercados.
- Espacio de disco y memoria suficientes para la imagen de Freqtrade y las dependencias de FreqAI. El entrenamiento de modelos puede consumir bastante memoria; comenzar con backtesting/Dry-run y dimensionar el servidor según el modelo elegido.

**No se puede completar el despliegue remoto sin un VPS y un dominio configurados por vos.** El ZIP contiene los archivos de despliegue, pero no incluye un servidor contratado ni credenciales de infraestructura.

## Preparar el servidor

1. Copiá esta carpeta completa al VPS y entrá en ella.
2. Asegurá que el DNS de tu dominio apunte al VPS.
3. Ejecutá el generador de secretos:

   ```bash
   python3 deploy/init_env.py
   ```

   Escribí el dominio cuando lo solicite. Se creará `.env` con contraseñas y tokens aleatorios. No compartas ese archivo ni lo subas a GitHub.

4. Asegurá permisos de escritura para el usuario no-root del contenedor (UID 1000):

   ```bash
   sudo chown -R 1000:1000 server/user_data
   ```

5. Construí la imagen y levantá los servicios:

   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

6. Revisá el arranque:

   ```bash
   docker compose ps
   docker compose logs -f freqtrade gateway caddy
   ```

7. La API del gateway estará disponible en `https://TU_DOMINIO/healthz`. Ese endpoint solo comprueba que el gateway vive; para el dashboard se necesita el token.

### Datos y configuración

- Configuración generada en `server/user_data/config.json`.
- Base de datos de operaciones en `server/user_data/tradesv3.sqlite`.
- Logs en `server/user_data/logs/`.
- La configuración se genera al arrancar y mantiene `dry_run: true`, `trading_mode: spot`, `initial_state: stopped` y `force_entry_enable: false`.
- No hace falta introducir API keys del exchange para consultar datos públicos y practicar Dry-run. No agregues claves con permisos de retiro.

Para reiniciar:

```bash
docker compose restart freqtrade gateway caddy
```

Para detener servicios:

```bash
docker compose down
```

## Compilar la app Android

El proyecto Android está en `android/`, pero usa los archivos Gradle del nivel raíz. Abrí en Android Studio la carpeta raíz de este paquete (la que contiene `settings.gradle.kts`). Requisitos: Android Studio estable, JDK 17 y Gradle 8.13 (el workflow de GitHub lo instala automáticamente). El módulo usa Android Gradle Plugin 8.9.1 y compileSdk 35.

Luego:

1. Esperá a que Gradle sincronice las dependencias.
2. Elegí `Build > Build Bundle(s) / APK(s) > Build APK(s)`.
3. El APK de depuración queda en `android/app/build/outputs/apk/debug/app-debug.apk`.

### Compilación con GitHub Actions

El workflow `.github/workflows/android.yml` compila el APK de depuración cuando se ejecuta manualmente o al modificar el código Android. Subí el proyecto a un repositorio GitHub y ejecutá el workflow `Android debug APK`; descargá el artefacto `crypto-ai-trader-debug-apk` desde la ejecución.

El entorno actual de preparación no tiene Android SDK, Gradle ni Docker instalados, por eso no afirmo que el APK ni la imagen Docker hayan sido compilados aquí. El código Android y el despliegue están incluidos como fuentes para compilar en Android Studio o mediante Actions.

## Conectar Android al servidor

En la app instalada:

- URL: `https://` seguido del dominio que elegiste al crear `.env`.
- Token: el valor `APP_API_TOKEN` del archivo `.env` del servidor.

La app exige HTTPS y mantiene el token solo en memoria mientras está abierta. Si cerrás la aplicación, tendrás que ingresarlo nuevamente.

El dashboard muestra estado del bot, simulación, resultado, saldo, cantidad de operaciones y posiciones abiertas. Los controles móviles permiten iniciar, pausar o detener solo cuando el backend verifica `dry_run=true`.

## Comprobaciones locales del gateway

Desde la raíz del proyecto, con Python 3.11+:

```bash
python -m pip install -r server/requirements.txt pytest
python -m pytest -q tests
```

También se puede comprobar la sintaxis Python con:

```bash
python -m compileall -q server tests
```

## Seguridad y límites de esta versión

- No hay modo de trading real en la app.
- No hay endpoint móvil para cambiar `dry_run`, cargar claves de exchange, forzar compras/ventas ni activar apalancamiento.
- El backend valida nuevamente `dry_run` antes de aceptar inicio, pausa o detención.
- El token del gateway es secreto: quien lo tenga puede controlar el bot de simulación.
- No publiques el puerto 8080 de Freqtrade ni el 8000 del gateway.
- No uses claves de exchange con permisos de retiro. Para futuras pruebas live, habría que diseñar una etapa separada con autorización explícita y protecciones adicionales.
- Las simulaciones pueden diferir de operaciones reales por comisiones, spread, liquidez, latencia y deslizamiento.

## Licencia

Freqtrade es un proyecto de código abierto distribuido bajo la licencia que se incluye en `freqtrade/LICENSE`. Se conserva el aviso de licencia original. La app Android y el gateway de esta adaptación se incluyen como código adicional de este paquete.
