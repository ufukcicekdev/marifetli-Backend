from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        from core.prometheus_host import register_prometheus_host_collectors

        register_prometheus_host_collectors()
