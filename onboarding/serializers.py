from rest_framework import serializers
from .models import OnboardingStep, OnboardingChoice
from categories.serializers import CategoryListSerializer
from questions.serializers import TagSerializer


class OnboardingChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingChoice
        fields = ['id', 'label', 'value', 'order']


class OnboardingStepSerializer(serializers.ModelSerializer):
    choices = OnboardingChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = OnboardingStep
        fields = ['id', 'title', 'description', 'step_type', 'order', 'max_selections', 'is_optional', 'choices']
