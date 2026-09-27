from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class InvalidCredentials(Exception):
    """Autenticacion fallida -> la vista responde 401."""


class LoginSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class RegisterSerializer(serializers.Serializer):
    pass


class LogOutSerializer(serializers.Serializer):
    pass


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = fields
