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
    static_configs:
      - targets:
          - <backend-hostname>:8000
```

Not: Railway mimarine gore `target` degeri private domain veya service endpoint olabilir.

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

