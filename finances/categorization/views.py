from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from finances.models import TransactionCategoryRule

from .serializers import TransactionCategoryRuleSerializer


class TransactionCategoryRuleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TransactionCategoryRuleSerializer
    permission_classes = [IsAuthenticated]
    queryset = TransactionCategoryRule.objects.none()

    def get_queryset(self):
        return TransactionCategoryRule.objects.filter(
            owner=self.request.user
        ).select_related("category")
