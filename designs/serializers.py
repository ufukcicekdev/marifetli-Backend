from rest_framework import serializers
from django.core.files.base import ContentFile
from .models import Design
from .services import add_watermark_to_image
import uuid
import os


class DesignUploadSerializer(serializers.ModelSerializer):
    file = serializers.ImageField(write_only=True, required=True)
    license = serializers.ChoiceField(choices=[c[0] for c in Design._meta.get_field("license").choices], default="cc-by")
    add_watermark = serializers.BooleanField(default=True)
    tags = serializers.CharField(required=False, allow_blank=True, max_length=500)
    copyright_confirmed = serializers.BooleanField(required=True)

    class Meta:
        model = Design
        fields = ["file", "license", "add_watermark", "tags", "copyright_confirmed"]

    def validate_copyright_confirmed(self, value):
        if not value:
            raise serializers.ValidationError("Telif beyanının onaylanması zorunludur.")
        return value

    def create(self, validated_data):
        file_obj = validated_data.pop("file")
        add_watermark = validated_data.pop("add_watermark", True)
        author = self.context["request"].user

        if add_watermark:
            bytes_data, content_type = add_watermark_to_image(
                file_obj,
                format_from_name=(os.path.splitext(getattr(file_obj, "name", ""))[1] or ".png").lstrip(".").upper() or "PNG",
            )
            if bytes_data:
                name = f"{uuid.uuid4().hex}.png"
                validated_data["image"] = ContentFile(bytes_data, name=name)
            else:
                validated_data["image"] = file_obj
        else:
            validated_data["image"] = file_obj

        return Design.objects.create(author=author, **validated_data)


class DesignSerializer(serializers.ModelSerializer):
    """Liste/detay için read-only."""

    image_url = serializers.SerializerMethodField()
    author_username = serializers.SerializerMethodField()

    class Meta:
        model = Design
        fields = [
            "id", "image", "image_url", "license", "add_watermark", "tags",
            "created_at", "author_username",
        ]
        read_only_fields = fields

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def get_author_username(self, obj):
        return obj.author.username if obj.author_id else None


class DesignUpdateSerializer(serializers.ModelSerializer):
    """Sahip tasarımı günceller (license, tags)."""

    class Meta:
        model = Design
        fields = ["license", "tags"]

    def validate_license(self, value):
        if value not in dict(Design._meta.get_field("license").choices):
            raise serializers.ValidationError("Geçersiz lisans.")
        return value
