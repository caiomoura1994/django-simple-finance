from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from identity.serializers import RegisterSerializer, UserSerializer, ChangePasswordSerializer

# Create your views here.

class RegisterView(generics.CreateAPIView):
    """
    Register a new user.
    Returns user data and authentication token upon successful registration.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)

class LoginView(ObtainAuthToken):
    """
    Login user and return authentication token.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                         context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update user profile.
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

class ChangePasswordView(generics.UpdateAPIView):
    """
    Change user password.
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set new password
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        # Generate new token
        Token.objects.filter(user=request.user).delete()
        token, created = Token.objects.get_or_create(user=request.user)
        
        return Response({
            'message': 'Password updated successfully',
            'token': token.key
        })

class LogoutView(APIView):
    """
    Logout user by deleting their token.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            return Response(
                {'message': 'Successfully logged out'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Something went wrong'},
                status=status.HTTP_400_BAD_REQUEST
            )
