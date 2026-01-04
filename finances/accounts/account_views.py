from rest_framework import viewsets
from finances.accounts.account_serializers import AccountSerializer
from finances.models import Account
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal, InvalidOperation
from rest_framework import status
from loguru import logger

class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)
    
    def create(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} creating new account")
        try:
            response = super().create(request, *args, **kwargs)
            if response.status_code == 201:
                account_id = response.data.get('id')
                account_name = response.data.get('name')
                logger.info(f"Account {account_id} ({account_name}) created successfully by user {request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Error creating account for user {request.user.id}: {str(e)}", exc_info=True)
            raise
    
    def update(self, request, *args, **kwargs):
        account = self.get_object()
        logger.info(f"User {request.user.id} updating account {account.id} ({account.name})")
        try:
            response = super().update(request, *args, **kwargs)
            if response.status_code == 200:
                logger.info(f"Account {account.id} updated successfully by user {request.user.id}")
            return response
        except Exception as e:
            logger.error(f"Error updating account {account.id} for user {request.user.id}: {str(e)}", exc_info=True)
            raise

    @action(detail=True, methods=['post'])
    def adjust_balance(self, request, slug=None):
        account = self.get_object()
        logger.info(f"User {request.user.id} adjusting balance for account {account.id} ({account.name})")
        try:
            amount = Decimal(request.data.get('amount', 0))
        except (TypeError, ValueError, InvalidOperation):
            logger.warning(f"Invalid amount provided by user {request.user.id} for account {account.id}: {request.data.get('amount')}")
            return Response(
                {'error': 'Invalid amount provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_balance = account.balance
        account.balance = amount
        account.save()
        
        logger.info(f"Account {account.id} balance adjusted by user {request.user.id} - Old: {old_balance}, New: {account.balance}")
        
        return Response({
            'message': 'Balance adjusted successfully',
            'new_balance': account.balance
        }) 