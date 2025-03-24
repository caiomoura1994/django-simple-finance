from rest_framework import viewsets, filters, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from finances.transactions.transaction_serializers import TransactionSerializer
from finances.models import Transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
from rest_framework import status

class TransactionViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['kind_of_transaction', 'category', 'account', 'date']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']  # Default ordering
    search_fields = ['description']
    queryset = Transaction.objects.none()

    def get_queryset(self):
        return Transaction.objects.filter(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        # Get query parameters for date filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date', timezone.now().date().isoformat())
        
        # Base queryset
        queryset = self.get_queryset()
        
        # Apply date filtering if provided
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                return Response(
                    {"error": "Invalid start_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(date__lte=end_date)
        except ValueError:
            return Response(
                {"error": "Invalid end_date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate summary
        income = queryset.filter(kind_of_transaction='INCOME').aggregate(
            total=Sum('amount'))['total'] or 0
        expenses = queryset.filter(kind_of_transaction='EXPENSE').aggregate(
            total=Sum('amount'))['total'] or 0
        
        return Response({
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat(),
            },
            'total_income': income,
            'total_expenses': expenses,
            'balance': income - expenses,
            'transaction_count': queryset.count()
        })

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        queryset = self.get_queryset()
        summary = queryset.values('category__name', 'kind_of_transaction')\
            .annotate(total=Sum('amount'))\
            .order_by('category__name', 'kind_of_transaction')
        
        return Response(summary)

    @action(detail=False, methods=['get'])
    def by_account(self, request):
        queryset = self.get_queryset()
        summary = queryset.values('account__name', 'kind_of_transaction')\
            .annotate(total=Sum('amount'))\
            .order_by('account__name', 'kind_of_transaction')
        
        return Response(summary) 

