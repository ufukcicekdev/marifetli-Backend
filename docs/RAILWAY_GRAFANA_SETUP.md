# Railway + Grafana Izleme Kurulumu

Bu proje icin minimum izleme kurulumu:

1. Backend'e `/metrics` endpointi acilir (bu repoda acildi).
2. Railway'de Grafana template deploy edilir.
3. Prometheus veri kaynagi eklenir (Grafana Cloud Prometheus veya Railway icinde Prometheus servisi).
4. Dashboard + alarm kurulur.

## 1) Backend tarafi (tamamlandi)

Bu repoda asagidaki degisiklikler yapildi:

- `django-prometheus` eklendi (`requirements.txt`)
- middleware eklendi (`settings.py`)
- URL eklendi: `/metrics` (`marifetli_project/urls.py`)

Deploy sonrasi test:

- `GET https://<backend-domain>/metrics`
- Cikti icinde `django_http_requests_total` vb. metrikler gorulmeli.

## 1.1) Metrics endpoint güvenliği (onerilen)

Backend service variables:

- `METRICS_PUBLIC_ENABLED=false`
- `METRICS_BEARER_TOKEN=<uzun-rastgele-token>`

Bu durumda disaridan `/metrics` endpointi ya 404 (public kapali) ya da token yoksa 403 doner.
Prometheus scrape icin Authorization header kullan.

## 2) Railway Grafana template

Railway'de Grafana template'i deploy et.

Sonra Grafana'da:

- **Connections -> Data sources -> Add data source**
- `Prometheus` sec
- URL olarak Prometheus endpointini gir:
  - Grafana Cloud kullaniyorsan Cloud Prometheus URL'i
  - Railway icindeki Prometheus servisi kullaniyorsan onun internal URL'i

## 3) Prometheus scrape

Prometheus, backend'in `/metrics` endpointini periyodik cekmeli.

Ornek scrape job:

```yaml
scrape_configs:
  - job_name: marifetli-backend
    metrics_path: /metrics
    scrape_interval: 15s
    authorization:
      type: Bearer
      credentials: <METRICS_BEARER_TOKEN>
    static_configs:
      - targets:
          - <backend-hostname>:8000
```

Not: Railway mimarine gore `target` degeri private domain veya service endpoint olabilir.

## 3.1) Backend CPU / RAM (Railway — Node Exporter olmadan)

Web servisi **Daphne tek süreç**; `/metrics` ciktisinda Prometheus’un standart **`process_*`** metrikleri
gorunur ( `prometheus_client` ProcessCollector — `core.prometheus_host` import ile garanti edilir).

Grafana ornekleri:

- **RAM (RSS — bu Python süreci)**
  - `process_resident_memory_bytes`
- **CPU kullanimi (çekirdek basina oran, ~0–1 arasi)**
  - `rate(process_cpu_seconds_total[2m])`
- **Konteyner bellek (Railway Linux cgroup; varsa)**
  - Kullanim: `marifetli_container_memory_usage_bytes`
  - Limit: `marifetli_container_memory_limit_bytes`
  - Oran (panel): `marifetli_container_memory_usage_bytes / marifetli_container_memory_limit_bytes`

Not: Celery ayri Railway servisinde calisiyorsa bu metrikler **yalnizca web konteynerini** gösterir;
worker icin ayri serviste ayni `/metrics` yaklasimi veya Celery Flower/metrik ayri düsünülür.

## 3.2) Grafana dashboard (import)

Dashboard JSON’u **Git’e commit etmiyoruz** (`.gitignore`: `docs/grafana/marifetli-backend-dashboard.json`).

- Grafana’da panelleri kurduktan sonra **Share → Export → Save to file** ile JSON indirip isteğe bağlı olarak bu yola kaydedebilirsin; yerelde kalır, repoya gitmez.
- Yeni ortamda: **Dashboards → New → Import** ile kendi dosyanı yükle veya aşağıdaki PromQL’lerle (§4) sıfırdan panel ekle.

Panel özeti (referans): HTTP RPS, p95 gecikme, 4xx/5xx, `process_*` RAM/CPU, cgroup bellek (`marifetli_container_*`). Import sırasında **Prometheus** veri kaynağını seç.

## 4) Ilk dashboard paneler

Asagidaki panellerle basla:

- **Request rate (RPS)**
  - `sum(rate(django_http_requests_total_by_method_total[5m]))`
- **5xx error rate**
  - `sum(rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]))`
- **4xx error rate**
  - `sum(rate(django_http_responses_total_by_status_total{status=~"4.."}[5m]))`
- **P95 latency**
  - `histogram_quantile(0.95, sum(rate(django_http_requests_latency_seconds_by_view_method_bucket[5m])) by (le))`

## 5) Alarmlar (onerilen baslangic)

- 5xx > %2 (5 dakika)
- p95 latency > 0.8 sn (5 dakika)
- request sayisi aniden dusus (trafik beklenen saatlerde)

## 6) Uptime/health

Uygulamada root (`/`) 200 donuyor. Ayri health endpoint isterse:

- Railway healthcheck: `/`
- Alternatif: `/healthz` endpointi eklenebilir.

## 7) Loki (log) ve Tempo (trace) aktivasyonu

Bu repoda Loki/Tempo entegrasyonu opsiyonel olarak eklendi.

### A) Loki log push

Backend service variables:

- `LOKI_PUSH_URL=http://loki:3100/loki/api/v1/push`
- `REQUEST_LOGGING_ENABLED=true`
- `REQUEST_LOGGING_EXCLUDE_PREFIXES=/metrics,/admin,/static,/media,/favicon.ico` (opsiyonel)

Not:

- Bu degisken doluysa Django loglari Loki'ye push edilir.
- Bos birakilirsa sadece mevcut console/file/db loglama devam eder.
- `REQUEST_LOGGING_ENABLED=true` oldugunda endpoint bazli access log da Loki'de gorunur.

### B) Tempo trace (OTLP HTTP)

Backend service variables:

- `OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318/v1/traces`
- `OTEL_SERVICE_NAME=marifetli-backend` (opsiyonel; varsayilan ayni)

Not:

- `OTEL_EXPORTER_OTLP_ENDPOINT` yoksa tracing hic acilmaz.
- Endpoint verildiginde Django + requests + psycopg2 trace enstrumantasyonu aktif olur.

### C) Grafana tarafi

- Explore -> `Loki` datasource secip log query calistir:
  - `{application="marifetli-backend"}`
- Explore -> `Tempo` datasource secip trace search yap.


