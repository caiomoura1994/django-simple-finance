from rest_framework import viewsets
from finances.accounts.account_serializers import AccountSerializer
from finances.models import Account
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal, InvalidOperation
from rest_framework import status

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def adjust_balance(self, request, slug=None):
        account = self.get_object()
        try:
            amount = Decimal(request.data.get('amount', 0))
        except (TypeError, ValueError, InvalidOperation):
            return Response(
                {'error': 'Invalid amount provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        account.balance = amount
        account.save()
        
        return Response({
            'message': 'Balance adjusted successfully',
            'new_balance': account.balance
        }) 