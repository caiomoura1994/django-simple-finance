from django.urls import include, path
from rest_framework import routers

from finances.categories.views import CategoryViewSet

category_router = routers.DefaultRouter()
category_router.register(r'categories', CategoryViewSet)


urlpatterns = [
    path('categories/', include(category_router.urls)),
]