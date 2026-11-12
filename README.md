# sorbo. — las noticias en un sorbo

App de noticias instalable desde el navegador (PWA). Como el diario que se compraba al paso: lo más importante del día, para leer mientras te tomas el café.

**Cómo instalarla en el celular:** abre el link de la app →
- iPhone (Safari): *Compartir* → *Agregar a inicio*
- Android (Chrome): menú ⋮ → *Instalar app* / *Agregar a pantalla de inicio*

## Cómo funciona

```
GitHub Actions (cada 30 min)          GitHub Pages
  python build.py   ──────────►  docs/data/edition.json  ──►  la app (docs/)
  (motor de noticias en Python)                                (HTML + CSS + JS)
```

- `news/` — motor en Python: fuentes, lectura de RSS, resúmenes "En corto", ranking, racha, dato y quiz del día.
- `build.py` — arma la edición y la guarda en `docs/data/edition.json`.
- `.github/workflows/edicion.yml` — corre `build.py` cada 30 minutos y publica la edición.
- `docs/` — la app web: `index.html`, `styles.css`, `app.js`, `sw.js` (funciona sin señal) y `manifest.webmanifest` (para instalarla).

## Probarla en tu computador

```bash
python3 build.py                  # arma una edición con noticias reales
cd docs && python3 -m http.server 8000
```
Abre http://localhost:8000 (o, desde el celular en el mismo Wi-Fi, http://IP-de-tu-compu:8000).

## Publicarla (una sola vez)

1. Sube este proyecto al repositorio `sorbo` de tu cuenta de GitHub.
2. En el repo: **Settings → Pages → Source: Deploy from a branch → Branch: `main` / carpeta `/docs`** → Save.
3. En **Settings → Actions → General → Workflow permissions** elige **Read and write permissions**.
4. En la pestaña **Actions**, abre "Edición de Sorbo" y toca **Run workflow** para armar la primera edición.
5. Tu app queda en `https://TU-USUARIO.github.io/sorbo/`.

## Cambiar cosas

- Medios y temas: `news/sources.py`
- Colores y tipografías: arriba de `docs/styles.css`
- Textos y pantallas: `docs/app.js`
- Revisar qué fuentes funcionan: `python3 check_feeds.py`

Tipografías Lora e Inter bajo SIL Open Font License (ver `docs/assets/fonts/LICENCIAS.txt`).
La app muestra titulares y resúmenes públicos de cada medio y siempre enlaza a la nota original.
