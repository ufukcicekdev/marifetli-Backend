from rest_framework import serializers


class CategoryExpertAskSerializer(serializers.Serializer):
    main_category_id = serializers.IntegerField(min_value=1)
    subcategory_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    question = serializers.CharField(min_length=3, max_length=4000, trim_whitespace=True)
