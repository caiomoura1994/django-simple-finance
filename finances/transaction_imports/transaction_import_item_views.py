from django.db import transaction as database_transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from finances.categorization.service import normalize_transaction_description
from finances.models import (
    Transaction,
    TransactionCategoryRule,
    TransactionImportItem,
)

from .orchestrator import TransactionImportOrchestrator
from .transaction_import_item_serializers import (
    ApproveTransactionImportItemSerializer,
    TransactionImportItemSerializer,
)


class TransactionImportItemViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = TransactionImportItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "date", "amount"]
    ordering = ["created_at"]
    queryset = TransactionImportItem.objects.none()

    def get_queryset(self):
        queryset = TransactionImportItem.objects.filter(owner=self.request.user).select_related(
            "account",
            "suggested_category",
            "transaction_import",
            "transaction",
        )
        transaction_import = self.request.query_params.get("transaction_import")
        review_status = self.request.query_params.get("review_status")

        if transaction_import:
            queryset = queryset.filter(transaction_import_id=transaction_import)
        if review_status:
            queryset = queryset.filter(review_status=review_status)

        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        input_serializer = ApproveTransactionImportItemSerializer(
            data=request.data,
            context={"request": request},
        )
        input_serializer.is_valid(raise_exception=True)
        category = input_serializer.validated_data["category"]
        remember_choice = input_serializer.validated_data["remember_choice"]

        with database_transaction.atomic():
            item = get_object_or_404(
                self.get_queryset().select_for_update(),
                pk=pk,
            )

            if item.review_status == TransactionImportItem.ReviewStatus.REJECTED:
                return Response(
                    {"error": "Rejected items cannot be approved"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if item.review_status == TransactionImportItem.ReviewStatus.APPROVED:
                return Response(self.get_serializer(item).data)

            suggested_category_id = item.suggested_category_id
            transaction = Transaction.objects.create(
                owner=request.user,
                kind_of_transaction=item.kind_of_transaction,
                amount=item.amount,
                date=item.date,
                description=item.description,
                category=category,
                account=item.account,
            )

            item.transaction = transaction
            item.suggested_category = category
            item.review_status = TransactionImportItem.ReviewStatus.APPROVED
            item.reviewed_at = timezone.now()
            if category.id != suggested_category_id:
                item.categorization_source = TransactionImportItem.CategorizationSource.MANUAL
            item.save(
                update_fields=[
                    "transaction",
                    "suggested_category",
                    "review_status",
                    "reviewed_at",
                    "categorization_source",
                    "updated_at",
                ]
            )

            normalized_description = normalize_transaction_description(item.description)
            if remember_choice and normalized_description:
                TransactionCategoryRule.objects.update_or_create(
                    owner=request.user,
                    normalized_description=normalized_description,
                    kind_of_transaction=item.kind_of_transaction,
                    defaults={"category": category},
                )

            TransactionImportOrchestrator().resume_after_human_review(
                item.transaction_import_id
            )

        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        with database_transaction.atomic():
            item = get_object_or_404(
                self.get_queryset().select_for_update(),
                pk=pk,
            )

            if item.review_status == TransactionImportItem.ReviewStatus.APPROVED:
                return Response(
                    {"error": "Approved items cannot be rejected"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            item.review_status = TransactionImportItem.ReviewStatus.REJECTED
            item.reviewed_at = timezone.now()
            item.save(update_fields=["review_status", "reviewed_at", "updated_at"])
            TransactionImportOrchestrator().resume_after_human_review(
                item.transaction_import_id
            )

        return Response(self.get_serializer(item).data)
