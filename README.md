# telegram-etf-news-bot

Bot gratuito de Telegram para seguir tu `SPDR MSCI World UCITS ETF` (`SPPW`, símbolo Yahoo `SPPW.DE`) con mensajes diarios, resumen claro y alertas de susto serio.

## Qué hace

- Envía un mensaje diario de apertura pensado para las `09:05` hora de España.
- Envía un mensaje diario de cierre pensado para las `17:40` hora de España.
- También manda mensaje en sábados, domingos y festivos, pero adaptado a que el mercado está cerrado.
- Usa fuentes gratuitas: Google News RSS, Reddit RSS, cobertura pública indexada y Yahoo Finance público.
- Separa el bloque de información en medios, foros/comunidad y pulso social.
- Resume noticias relevantes en español, marca cada una como positiva, negativa o neutra, y añade una lectura prudente de lo que parece estar haciendo “la pasta”.
- Usa IA gratuita/local tanto para los resúmenes como para “qué hacer con cabeza” y la conclusión final, con respaldo por reglas si esa ruta falla.
- Tiene un segundo modo de vigilancia para alertas fuertes durante el día.
- Puede funcionar aunque tu ordenador esté apagado si lo subes a GitHub y usas los workflows de GitHub Actions incluidos.

## Qué no hace

- No predice el mercado.
- No da órdenes de compra o venta.
- No sustituye asesoramiento financiero.
- No sabe con exactitud lo que hacen ricos, medianos y pequeños dentro del ETF: hace una aproximación con señales públicas.

## Cómo crear el bot en Telegram

1. Abre `@BotFather`.
2. Escribe `/newbot`.
3. Pon un nombre y un `username` terminado en `bot`.
4. Guarda el token que te da BotFather.

## Cómo sacar tu `chat_id`

1. Abre el bot en Telegram.
2. Escríbele `/start`.
3. Visita esta URL cambiando `TOKEN`:

   `https://api.telegram.org/bot<TOKEN>/getUpdates`

4. Busca algo como `"chat":{"id":123456789,...}`.
5. Ese número es tu `TELEGRAM_CHAT_ID`.

Si quieres usar un grupo, mete el bot en el grupo, envía un mensaje y vuelve a mirar `getUpdates`. El `chat_id` de grupo suele ser negativo, por ejemplo `-1001234567890`.

## Variables de entorno y secretos

Localmente puedes copiar `.env.example` a `.env`.

En GitHub crea estos secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Variables normales que puedes cambiar en el workflow o en `.env`:

- `ETF_NAME`
- `ETF_TICKER`
- `YAHOO_SYMBOL`
- `TIMEZONE`
- `RUN_MODE`
- `SECTION_NEWS_LIMIT`
- `AI_SUMMARIES_ENABLED`
- `AI_MODEL_NAME`
- `AI_TRANSLATION_MODEL`

## Instalación local

```bash
pip install -r requirements.txt
```

Para probar sin enviar a Telegram:

```bash
DRY_RUN=1 RUN_MODE=daily_open python bot.py
```

En PowerShell:

```powershell
$env:DRY_RUN="1"
$env:RUN_MODE="daily_open"
python .\bot.py
```

## Modos del script

- `daily_open`
- `daily_close`
- `catastrophe_watch`
- `auto`

`auto` se usa en el workflow diario y decide si toca apertura o cierre según la hora real en `Europe/Madrid`.

## Lógica de horarios con GitHub Actions

GitHub Actions usa cron en UTC, así que el workflow diario dispara cuatro veces:

- `07:05 UTC`
- `08:05 UTC`
- `15:40 UTC`
- `16:40 UTC`

Dentro de Python se comprueba la hora real en `Europe/Madrid` y solo se envía si encaja con la franja de `09:05` o `17:40`. Así se cubren horario de invierno y verano sin duplicar mensaje.

Para la vigilancia de catástrofes se usa un cron amplio:

- cada `15` minutos entre `05:00` y `21:59 UTC`

Y luego Python filtra para dejar solo la ventana aproximada de `07:00` a `22:00` hora España.

## Workflows incluidos

- `.github/workflows/etf_daily_bot.yml`
- `.github/workflows/etf_catastrophe_watch.yml`

Ambos tienen `workflow_dispatch` para probarlos manualmente.

## Cómo hacer que funcione con el ordenador apagado

Si lo ejecutas solo en tu PC, tu ordenador tiene que estar encendido.

Si quieres que mande mensajes aunque el ordenador esté apagado:

1. Sube esta carpeta a un repositorio de GitHub.
2. En GitHub añade los secrets `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
3. Activa la pestaña `Actions` del repositorio.
4. Deja que GitHub ejecute los workflows programados.

En ese modo, quien ejecuta el bot es GitHub en la nube, no tu ordenador.

## Cómo ejecutar un workflow manualmente

1. Sube este proyecto a su propio repositorio de GitHub.
2. Entra en la pestaña `Actions`.
3. Abre el workflow que quieras.
4. Pulsa `Run workflow`.
5. En el diario puedes elegir `auto`, `daily_open` o `daily_close`.

## Qué analiza el mensaje

- Estado del mercado Xetra.
- Precio aproximado del ETF si Yahoo Finance responde.
- Noticias de ETF, MSCI World, grandes tecnológicas, macro y mercado.
- Un bloque separado de medios, otro de foros/comunidad y otro de pulso social.
- Sentimiento aproximado por noticia: positivo, negativo o neutro.
- Señales aproximadas sobre:
  - dinero grande / institucional
  - dinero medio
  - dinero pequeño / tu caso

## Fuentes y limitaciones

- Google News RSS puede cambiar, fallar o devolver resultados raros.
- La parte de “pulso social” no usa la API oficial de X porque no es gratuita de forma estable; usa resultados públicos indexados, Reddit y otras fuentes abiertas, así que puede ser irregular.
- Yahoo Finance gratuito puede fallar o no devolver precio temporalmente.
- Si una fuente falla, el bot intenta seguir con las demás.
- Si una noticia está detrás de un muro de pago y no se puede extraer bien, el bot intenta buscar cobertura pública alternativa del mismo tema.
- El análisis de “ricos/medios/pequeños” es una heurística, no un dato exacto por tipo de inversor.
- La deduplicación de alertas graves guarda un pequeño historial en `.runtime/last_alert.json`. En GitHub Actions el workflow intenta restaurar y guardar ese estado con caché para evitar repetir la misma alerta cada 15 minutos.
- La deduplicación de noticias combina título, fuente, temas, empresas y palabras de evento para reducir titulares repetidos contados por varias fuentes.

## Festivos de mercado

El bot trae una lista simple de festivos Xetra para `2026` dentro de `bot.py`. Hay que revisarla y actualizarla cada año.

Para 2026 se han tomado como referencia los días no negociables publicados por Deutsche Börse / Xetra:

- Año Nuevo
- Viernes Santo
- Lunes de Pascua
- Día del Trabajo
- Nochebuena
- Navidad
- Nochevieja

## Qué puedes cambiar

- ETF y ticker: cambia `ETF_NAME`, `ETF_TICKER` y `YAHOO_SYMBOL`.
- Horarios: ajusta `DAILY_TARGETS` y los cron de GitHub Actions.
- Número de piezas por sección: cambia `SECTION_NEWS_LIMIT`.
- Palabras clave: edita `ETF_NEWS_QUERIES`, `VERY_IMPORTANT_KEYWORDS`, `IMPORTANT_KEYWORDS` y `CRISIS_KEYWORDS`.
- Fuentes RSS: modifica `_news_query_urls()`, `_forum_query_urls()` y `_social_query_urls()`.
- Festivos: actualiza `XETRA_HOLIDAYS_2026`.
- Umbrales de catástrofe: ajusta `detect_catastrophe()`.

## Tests

```bash
pytest
```

Los tests no dependen de internet y usan datos simulados.
