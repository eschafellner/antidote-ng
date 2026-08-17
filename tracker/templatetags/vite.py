import json
from pathlib import Path
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def vite_asset(entry_name: str = "frontend/main.js") -> str:
    """
    Renders script and stylesheet tags for the given Vite entrypoint.
    Reads manifest.json from static/dist/ in production or built mode.
    """
    manifest_path = settings.BASE_DIR / "static" / "dist" / "manifest.json"

    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            entry_data = manifest.get(entry_name, {})
            js_file = entry_data.get("file", "")
            css_files = entry_data.get("css", [])

            html_tags = []
            for css in css_files:
                html_tags.append(
                    f'<link rel="stylesheet" href="{settings.STATIC_URL}dist/{css}">'
                )

            if js_file:
                html_tags.append(
                    f'<script type="module" src="{settings.STATIC_URL}dist/{js_file}"></script>'
                )

            return mark_safe("\n".join(html_tags))
        except Exception:
            pass

    # Fallback to local dev server
    return mark_safe(
        f"""
        <script type="module" src="http://localhost:5173/@vite/client"></script>
        <script type="module" src="http://localhost:5173/{entry_name}"></script>
        """
    )
