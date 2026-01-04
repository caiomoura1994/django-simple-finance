from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from identity.serializers import RegisterSerializer, UserSerializer, ChangePasswordSerializer
from loguru import logger

# Create your views here.

class RegisterView(generics.CreateAPIView):
    """
    Register a new user.
    Returns user data and authentication token upon successful registration.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', 'unknown')
        logger.info(f"User registration attempt - Email: {email}")
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Generate token
            token, created = Token.objects.get_or_create(user=user)
            
            logger.info(f"User {user.id} ({user.email}) registered successfully")
            
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error registering user with email {email}: {str(e)}", exc_info=True)
            raise

class LoginView(ObtainAuthToken):
    """
    Login user and return authentication token.
    """
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', 'unknown')
        logger.info(f"Login attempt - Email: {email}")
        try:
            serializer = self.serializer_class(data=request.data,
                                             context={'request': request})
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            
            logger.info(f"User {user.id} ({user.email}) logged in successfully")
            
            return Response({
                'token': token.key,
                'user_id': user.pk,
                'email': user.email
            })
        except Exception as e:
            logger.warning(f"Failed login attempt for email {email}: {str(e)}")
            raise

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update user profile.
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} retrieving profile")
        return super().retrieve(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} updating profile")
        try:
            response = super().update(request, *args, **kwargs)
            if response.status_code == 200:
                logger.info(f"User {request.user.id} profile updated successfully")
            return response
        except Exception as e:
            logger.error(f"Error updating profile for user {request.user.id}: {str(e)}", exc_info=True)
            raise

class ChangePasswordView(generics.UpdateAPIView):
    """
    Change user password.
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    def update(self, request, *args, **kwargs):
        logger.info(f"User {request.user.id} changing password")
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Set new password
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()

            # Generate new token
            Token.objects.filter(user=request.user).delete()
            token, created = Token.objects.get_or_create(user=request.user)
            
            logger.info(f"User {request.user.id} password changed successfully")
            
            return Response({
                'message': 'Password updated successfully',
                'token': token.key
            })
        except Exception as e:
            logger.error(f"Error changing password for user {request.user.id}: {str(e)}", exc_info=True)
            raise

class LogoutView(APIView):
    """
    Logout user by deleting their token.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        logger.info(f"User {request.user.id} logging out")
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            logger.info(f"User {request.user.id} logged out successfully")
            return Response(
                {'message': 'Successfully logged out'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error logging out user {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Something went wrong'},
                status=status.HTTP_400_BAD_REQUEST
            )
