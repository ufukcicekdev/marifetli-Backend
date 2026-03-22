"""
DRF sayfalama: ?page_size= istemci tarafından sınırlı şekilde artırılabilir (sitemap vb.).
Varsayılan sayfa boyutu 20 kalır.
"""
from rest_framework.pagination import PageNumberPagination


class MarifetliPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
