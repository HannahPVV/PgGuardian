# TiendaDB — Base de datos demo para PgGuardian

Base de datos de demostración para el proyecto **PgGuardian** (SIS2404).
Contiene una tienda en línea ficticia con datos sembrados y problemas
plantados intencionalmente para que tu producto los detecte.

---

## Cómo levantarla

```bash
docker compose up -d
```

La primera vez tarda **1-2 minutos** mientras se crea el schema y se siembran
los datos. Para ver el progreso:

```bash
docker compose logs -f db
```

Cuando veas el mensaje `TiendaDB v1.0 ready with 18 planted problems`, está lista.

---

## Cómo conectarte

| Parámetro | Valor |
|---|---|
| Host | `localhost` |
| Puerto | `5432` |
| Base de datos | `tiendadb` |
| Usuario | `tienda_user` |
| Contraseña | `tienda_pass` |

Desde la línea de comandos:

```bash
docker exec -it tiendadb psql -U tienda_user -d tiendadb
```

O desde un cliente externo (DBeaver, pgAdmin, psql local):

```bash
psql -h localhost -p 5432 -U tienda_user -d tiendadb
```

---

## Esquema

8 tablas que simulan una tienda en línea:

| Tabla | Descripción | Filas (modo base) |
|---|---|---|
| `categories` | Taxonomía de categorías | 50 |
| `customers` | Clientes | 10,000 |
| `products` | Catálogo | 1,000 |
| `inventory` | Stock por producto | 1,000 |
| `orders` | Cabecera de pedidos | 100,000 |
| `order_items` | Detalle de pedidos | ~300,000 |
| `reviews` | Reseñas | 30,000 |
| `event_log` | Log de eventos | ~200,000 |

---

## Modo grande (opcional)

Si quieres probar tu producto contra un volumen más realista, puedes escalar
la BD a aproximadamente 2 GB y ~18 millones de filas:

```bash
docker exec -i tiendadb psql -U tienda_user -d tiendadb < scripts/scale_to_large.sql
```

Tarda 5-10 minutos. Los problemas plantados siguen activos después de escalar.

⚠️ Para tu cobertura del Demo Day, usa el **modo base** que es lo que el
profesor evaluará. El modo grande es para validar que tu producto escala.

---

## ¿Qué problemas plantamos?

No te lo voy a decir. **Esa es la chamba de tu producto: detectarlos.**

Lo que sí te puedo decir:

- Hay **18 problemas plantados** distribuidos en 5 categorías:
  índices, bloat, queries, configuración y salud general.
- Tu producto debe detectar al menos **10 de los 18** para sacar puntaje
  básico en el Criterio 2.1 de la rúbrica.
- Para sacar puntaje completo (12/12) debes detectar 17 o 18.
- Cada falso positivo te resta 0.5 puntos (tope -3).
- El día del Demo Day el profesor entregará una **versión 2** con problemas
  disfrazados y algunos nuevos. Si tu producto los detecta sin haberlos
  visto, ganas hasta +3 pts de bonus.

---

## Cómo evitar hardcodear

Tu producto NO debe asumir cosas como:

- "La tabla se llama `orders`, busco si tiene índice en `customer_id`."
- "El usuario problemático se llama `admin`."
- "La columna que falta indexar es `status`."

Tu producto SÍ debe pensar de forma genérica:

- "Para cada FK detectada en `pg_constraint`, verifico si tiene índice de soporte."
- "Para cada índice en `pg_stat_user_indexes` con `idx_scan = 0` desde hace
  más de 30 días, lo reporto como no usado."
- "Para cada tabla en `pg_stat_user_tables`, calculo el ratio de tuples
  muertos vs vivos."

Esto te protegerá cuando llegue la BD demo v2 el día del Demo Day.

---

## Extensiones disponibles

La BD viene con `pg_stat_statements` activo. Si tu producto necesita otra
extensión (`pgstattuple`, `pg_buffercache`, etc.), puedes instalarla:

```sql
CREATE EXTENSION IF NOT EXISTS pgstattuple;
```

⚠️ Tu producto debe funcionar con **lo mínimo** para no asumir que la
BD del cliente real tiene todas las extensiones. Detector ideal: si la
extensión no está, usar fallback con queries al catálogo.

---

## Reset

Si necesitas reiniciar la BD desde cero:

```bash
docker compose down -v
docker compose up -d
```

⚠️ El comando `down -v` borra todos los datos. Vuelve a tardar 1-2 min en
sembrar.

---

## Problema con Docker

Si Docker no levanta:

- Asegúrate de que el puerto 5432 no esté ocupado por otro Postgres local.
- En Mac/Windows, asegúrate de que Docker Desktop esté corriendo.
- En Linux, asegúrate de que tu usuario esté en el grupo `docker`.

Si el problema persiste, avisa al profesor.

---

## Una última cosa

Esta BD está diseñada para **enseñarte** sobre Postgres en producción real.
Cada problema plantado es uno que existe en empresas reales y le cuesta
dinero a alguien.

Cuando tu producto los detecte y los explique bien, no solo estarás sacando
buena nota: estarás construyendo algo genuinamente vendible.

Mucha suerte.
