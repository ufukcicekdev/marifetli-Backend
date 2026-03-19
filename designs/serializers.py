from rest_framework import serializers
from django.core.files.base import ContentFile
from .models import Design, DesignImage, DesignLike, DesignComment
from .services import add_watermark_to_image
import uuid
import os


def _image_url(request, image_field):
    if not image_field:
        return None
    if request:
        return request.build_absolute_uri(image_field.url)
    return image_field.url


class DesignUploadSerializer(serializers.Serializer):
    """Çoklu görsel yükleme: files context'te gönderilir."""

    license = serializers.ChoiceField(choices=[c[0] for c in Design._meta.get_field("license").choices], default="cc-by")
    add_watermark = serializers.BooleanField(default=True)
    tags = serializers.CharField(required=False, allow_blank=True, max_length=500)
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    copyright_confirmed = serializers.BooleanField(required=True)

    def validate_copyright_confirmed(self, value):
        if not value:
            raise serializers.ValidationError("Telif beyanının onaylanması zorunludur.")
        return value

    def create(self, validated_data):
        files = self.context.get("files") or []
        if not files:
            raise serializers.ValidationError({"files": "En az bir görsel yükleyin."})
        add_watermark = validated_data.pop("add_watermark", True)
        author = self.context["request"].user

        design = Design.objects.create(author=author, add_watermark=add_watermark, **validated_data)
        for order, file_obj in enumerate(files):
            if add_watermark:
                bytes_data, _ = add_watermark_to_image(
                    file_obj,
                    format_from_name=(os.path.splitext(getattr(file_obj, "name", ""))[1] or ".png").lstrip(".").upper() or "PNG",
                )
                if bytes_data:
                    name = f"{uuid.uuid4().hex}.png"
                    DesignImage.objects.create(design=design, image=ContentFile(bytes_data, name=name), order=order)
                else:
                    DesignImage.objects.create(design=design, image=file_obj, order=order)
            else:
                DesignImage.objects.create(design=design, image=file_obj, order=order)
        return design


class DesignSerializer(serializers.ModelSerializer):
    """Liste/detay için read-only; image_urls slider için."""

    image_url = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()
    author_username = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Design
        fields = [
            "id", "image_url", "image_urls", "license", "add_watermark", "tags", "description",
            "like_count", "comment_count", "liked_by_me", "created_at", "author_username",
        ]
        read_only_fields = fields

    def get_image_url(self, obj):
        imgs = list(obj.design_images.order_by("order"))
        if imgs and imgs[0].image:
            return _image_url(self.context.get("request"), imgs[0].image)
        return _image_url(self.context.get("request"), obj.image)

    def get_image_urls(self, obj):
        request = self.context.get("request")
        imgs = list(obj.design_images.order_by("order"))
        if imgs:
            return [_image_url(request, im.image) for im in imgs if im.image]
        if obj.image:
            return [_image_url(request, obj.image)]
        return []

    def get_author_username(self, obj):
        return obj.author.username if obj.author_id else None

    def get_liked_by_me(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return DesignLike.objects.filter(user=user, design=obj).exists()


class DesignUpdateSerializer(serializers.ModelSerializer):
    """Sahip tasarımı günceller (license, tags, description)."""

    class Meta:
        model = Design
        fields = ["license", "tags", "description"]

    def validate_license(self, value):
        if value not in dict(Design._meta.get_field("license").choices):
            raise serializers.ValidationError("Geçersiz lisans.")
        return value


class DesignLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignLike
        fields = ["id", "user", "design", "created_at"]
        read_only_fields = ["id", "user", "design", "created_at"]


class DesignCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField()
    author_profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = DesignComment
        fields = ["id", "design", "author", "author_username", "author_profile_picture", "parent", "content", "created_at", "updated_at"]
        read_only_fields = ["id", "design", "author", "author_username", "author_profile_picture", "created_at", "updated_at"]

    def get_author_username(self, obj):
        return obj.author.username if obj.author_id else None

    def get_author_profile_picture(self, obj):
        req = self.context.get("request")
        profile_picture = getattr(obj.author, "profile_picture", None)
        return _image_url(req, profile_picture)

    def validate_parent(self, value):
        if value is None:
            return value
        design = self.context.get("design")
        if design is not None and value.design_id != design.id:
            raise serializers.ValidationError("Yanıt sadece aynı tasarımın yorumuna verilebilir.")
        if value.parent_id is not None:
            raise serializers.ValidationError("En fazla bir seviye yanıt desteklenir.")
        return value
