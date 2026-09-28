from __future__ import annotations

from rest_framework import serializers

from ..application import AuthOutput, LoginInput, RegisterInput


class LoginSerializer(serializers.Serializer):
    # Entrada de Json de longin. Salida: AuthOutput ya mapeado.

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def to_application_input(self, validated_data: dict) -> LoginInput:
        return LoginInput(
            email=validated_data["email"], password=validated_data["password"]
        )

    def to_representation(self, output: AuthOutput) -> dict:
        return {
            "id": output.id,
            "email": output.email,
            "first_name": output.first_name,
            "last_name": output.last_name,
            "user_type": output.user_type,
        }


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def to_application_input(self, validated_data: dict) -> RegisterInput:
        return RegisterInput(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )

    def to_representation(self, output: AuthOutput) -> dict:
        return {
            "id": output.id,
            "email": output.email,
            "first_name": output.first_name,
            "last_name": output.last_name,
            "user_type": output.user_type,
        }
