from pathlib import Path

app_name = "genieapp"
app_entrypoint = "genieapp.backend.app:app"
app_slug = "genieapp"
api_prefix = "/api"
dist_dir = Path(__file__).parent / "__dist__"
