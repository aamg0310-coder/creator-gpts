# Guía paso a paso — Desplegar en Render

## Antes de empezar (local)

```bash
# 1. Confirma que todo está limpio
git add -A
git commit -m "deploy: render.yaml + production settings + ssl central"
git push origin main
```

> Si no tienes repo en GitHub: crea uno, conecta remotes y sube.

---

## Paso 1: Crear servicio en Render

1. Entra a [render.com](https://render.com) y conecta con GitHub.
2. Click **New +** → **Web Service**.
3. Selecciona tu repositorio `creator-gpts`.
4. Configura:

| Campo | Valor recomendado |
|---|---|
| **Name** | `creator-gpts` (o tu dominio) |
| **Region** | `Oregon` (o más cerca a tu audiencia) |
| **Branch** | `main` |
| **Runtime** | `Python` |
| **Build Command** | `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate` |
| **Start Command** | `gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --access-logfile - --error-logfile -` |
| **Plan** | `Starter` (subes luego) |

5. Click **Create Web Service**.

---

## Paso 2: Crear base PostgreSQL (REQUIRED antes de deploy)

En Render Dashboard, en la misma cuenta:

1. **New +** → **PostgreSQL**.
2. Configura:

| Campo | Valor |
|---|---|
| **Name** | `creator-gpts-db` (debe coincidir con `render.yaml`) |
| **Region** | Mismo que el web service (`Oregon`) |
| **Plan** | `Starter` / `Free` (según disponibilidad) |
| **PostgreSQL Version** | 15+ (Recomendado para pgvector si lo usas) |

3. Click **Create Database**.

4. Copia el **Internal Database URL** o **Connection String** que aparecerá.

---

## Paso 3: Variables de entorno (Dashboard → tu servicio → Environment)

Añade **todas** las de esta lista. Puedes copiar desde `.env.render.template`.

| Variable | Valor / Cómo obtener |
|---|---|
| `SECRET_KEY` | Genera: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` → pega aquí |
| `DEBUG` | `False` |
| `DJANGO_SETTINGS_MODULE` | `core.settings.production` |
| `ALLOWED_HOSTS` | `creator-gpts.onrender.com,localhost,127.0.0.1` (o tu dominio custom) |
| `APP_URL` | `https://creator-gpts.onrender.com` (o tu dominio) |
| `DATABASE_URL` | Pega el **connection string** de la DB del Paso 2 |
| `OPENROUTER_API_KEY` | Tu clave de OpenRouter (`sk-or-v1-...`) |
| `INSFORGE_MODEL_GATEWAY_URL` | `https://openrouter.ai/api/v1` |
| `INSFORGE_PROJECT_ID` | Tu ID del proyecto InsForge |
| `INSFORGE_BASE_URL` | `https://885xdbkm.us-east.insforge.app` (o tu URL) |
| `INSFORGE_ANON_KEY` | Tu clave real de InsForge (reemplaza `ACTUAL_ANON_KEY_AQUI`) |
| `CORS_ALLOWED_ORIGINS` | `https://creator-gpts.onrender.com` (o tu dominio) |

> **Importante:** No pongas `.env.local` en GitHub. Render usa el Dashboard.

---

## Paso 4: Configurar `render.yaml` (opcional pero recomendado)

Ya lo creé en la raíz del proyecto (`render.yaml`). Si usas **Render Blueprint** (infraestructura como código), Render lo detectará automáticamente cuando conectes el repo.

Si prefieres configurar manualmente (como en Paso 1), el `render.yaml` sirve como referencia de build/start commands.

---

## Paso 5: Deploy y primer build

Una vez configuradas las variables:

1. En tu servicio de Render, verás un botón **Deploy latest commit** (o se despliega solo tras push).
2. El build correrá:
   - `pip install -r requirements.txt`
   - `python manage.py collectstatic --noinput`
   - `python manage.py migrate`
3. Si todo va bien, el servicio pasa a **Live** y te da una URL tipo `https://creator-gpts.onrender.com`.

---

## Paso 6: Verificación post-deploy

Accede a tu URL y prueba en orden:

```bash
# Prueba básica (desde tu PC)
curl -I https://creator-gpts.onrender.com/
# Debe devolver HTTP/2 200

# Login / Registro
# Crear un chatbot
# Subir un documento (PDF/DOCX/TXT)
# Hacer una pregunta (streaming)
# Compartir público (toggle público en edición)
```

Si algún paso falla:

- **Build error**: Revisa los logs de Render (pestaña **Logs** → **Build**). Normalmente es `requirements.txt` faltante o `SECRET_KEY` vacío.
- **Database error**: Confirma que `DATABASE_URL` esté completa y la DB esté creada en la misma región.
- **InsForge error**: Confirma que `INSFORGE_ANON_KEY` y `INSFORGE_PROJECT_ID` sean reales. Prueba con `curl` a tu endpoint de InsForge.

---

## Paso 7: Custom domain + SSL (opcional, una vez en línea)

1. En Render Dashboard de tu servicio → **Settings** → **Custom Domains**.
2. Añade tu dominio (ej: `chatbot.tudominio.com`).
3. Render te da registros DNS (`CNAME` y `A` / `AAAA`). Configúralos en tu proveedor DNS.
4. Render emite SSL automático (Let's Encrypt) en ~1 minuto.
5. Actualiza `ALLOWED_HOSTS` y `APP_URL` con tu dominio.

---

## Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'certifi'` | Falta en requirements | Vuelve a `pip install -r requirements.txt` y despliega |
| `DATABASE_URL not configured` | Falta variable o DB no enlazada | Revisa Paso 3; si usas `render.yaml`, la variable `fromDatabase` la inyecta sola |
| `CSRF verification failed` | `ALLOWED_HOSTS` o `APP_URL` incorrecto | Actualiza con tu URL real |
| `InsForge connection error` | Clave anónima incorrecta o URL base mal | Prueba `curl` a tu endpoint InsForge manualmente |
| `SSL CERTIFICATE_VERIFY_FAILED` en Windows | Entorno local | Ya centralizado en `apps/core/utils/ssl.py`; en Render no ocurre |
| `collectstatic` lento | Muchos archivos estáticos | Normal; espera el build o excluye archivos no usados |

---

## Lista de verificación final para que esté 100%

- [ ] Código subido a GitHub (`main` actualizado con `render.yaml` y cambios de producción)
- [ ] Servicio creado en Render con Build/Start commands correctos
- [ ] PostgreSQL creada y `DATABASE_URL` configurada
- [ ] Variables de entorno completas (especialmente `SECRET_KEY`, `OPENROUTER_API_KEY`, `INSFORGE_ANON_KEY`)
- [ ] Deploy exitoso (estado **Live**)
- [ ] `/` carga, login funciona, chatbot crea, documento sube, chat responde, compartir público funciona
- [ ] (Opcional) Dominio custom + SSL en Render
- [ ] (Opcional) Backup automático de DB o exportación periódica

---

¿Necesitas que te ayude con alguna parte específica? Puedo:
- Generar un `SECRET_KEY` seguro ahora
- Revisar si tu clave `INSFORGE_ANON_KEY` es correcta con un `curl`
- Configurar el dominio custom paso a paso
- Preparar un `README.md` de deploy para tu repo
