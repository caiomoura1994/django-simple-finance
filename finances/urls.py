from django.urls import include, path
from rest_framework import routers

from finances.categories.category_views import CategoryViewSet
from finances.accounts.account_views import AccountViewSet
from finances.transactions.transaction_views import TransactionViewSet
from finances.transaction_imports.transaction_import_views import TransactionImportViewSet

router = routers.DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'accounts', AccountViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'transaction-imports', TransactionImportViewSet)

urlpatterns = [
    path('', include(router.urls)),
]