"""
Veritabanına log yazan handler. LOGGING ayarında kullanılır.
"""
import logging


class DatabaseLogHandler(logging.Handler):
    """
    Log kayıtlarını logs.LogEntry tablosuna yazar.
    Handler kendi hatalarını sessizce yutar (DB yazılamazsa uygulama kırılmaz).
    """

    def __init__(self, source=""):
        super().__init__()
        self.source = source or ""

    def emit(self, record: logging.LogRecord):
        try:
            from logs.models import LogEntry

            message = self.format(record)
            extra_dict = {}
            if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
                extra_dict = record.extra_data
            # record.args vb. hassas veya non-JSON olabilir; sadece eklediğimiz extra_data kullan
            LogEntry.objects.create(
                level=record.levelname,
                logger_name=record.name,
                message=message[:10000],  # çok uzun mesaj kesilsin
                source=self.source or record.name.split(".")[0] if record.name else "",
                extra=extra_dict,
            )
        except Exception:
            # DB yazılamazsa sessizce geç (recursion / DB down vb.)
            self.handleError(record)
