from rest_framework.pagination import PageNumberPagination

class LargeResultsSetPagination(PageNumberPagination):
    """
    Custom pagination class for handling large datasets.
    
    - `page_size`: Default number of items per page (6).
    - `page_size_query_param`: Allows clients to request a different page size.
    - `max_page_size`: Maximum limit a client can request (100).
    """
    page_size = 6
    page_size_query_param = 'page_size'
    max_page_size = 100  # Erhöhtes Limit für größere Anfragen