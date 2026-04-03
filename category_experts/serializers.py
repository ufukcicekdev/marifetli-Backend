import mimetypes

from rest_framework import serializers

ALLOWED_EXPERT_ATTACHMENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)
MAX_EXPERT_ATTACHMENT_BYTES = 5 * 1024 * 1024


class CategoryExpertAskSerializer(serializers.Serializer):
    main_category_id = serializers.IntegerField(min_value=1)
    subcategory_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    question = serializers.CharField(min_length=1, max_length=4000, trim_whitespace=True)
    attachment = serializers.FileField(required=False, allow_null=True, write_only=True)

    def validate_attachment(self, f):
        if f is None:
            return None
        if f.size > MAX_EXPERT_ATTACHMENT_BYTES:
            raise serializers.ValidationError("Ek dosya en fazla 5 MB olabilir.")
        ct = (getattr(f, "content_type", None) or "").split(";")[0].strip().lower()
        if ct not in ALLOWED_EXPERT_ATTACHMENT_TYPES:
            guess, _ = mimetypes.guess_type(getattr(f, "name", "") or "")
            if guess and guess.lower() in ALLOWED_EXPERT_ATTACHMENT_TYPES:
                ct = guess.lower()
            else:
                raise serializers.ValidationError("Sadece JPEG, PNG, WebP veya GIF görsel yükleyebilirsiniz.")
        return f

    def validate(self, attrs):
        q = (attrs.get("question") or "").strip()
        attrs["question"] = q
        if not attrs.get("attachment"):
            if len(q) < 3:
                raise serializers.ValidationError(
                    {"question": "Sorunuz en az 3 karakter olmalıdır (veya bir görsel ekleyin)."}
                )
        return attrs
