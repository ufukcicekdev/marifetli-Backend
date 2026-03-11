from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from core.permissions import IsVerified
from .models import OnboardingStep, OnboardingChoice, UserOnboarding, UserOnboardingSelection, UserOnboardingCategorySelection
from .serializers import OnboardingStepSerializer
from questions.serializers import TagSerializer
from categories.models import Category, CategoryFollow
from questions.models import Tag, TagFollow


def _user_has_completed_onboarding(user):
    obj, _ = UserOnboarding.objects.get_or_create(user=user)
    return obj.completed_at is not None


class OnboardingStepListView(generics.ListAPIView):
    """Aktif onboarding adımlarını listele. Herkes görebilir (AllowAny)."""
    serializer_class = OnboardingStepSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return OnboardingStep.objects.filter(is_active=True).prefetch_related('choices')


class OnboardingMySelectionsView(APIView):
    """Giriş yapmış kullanıcının mevcut onboarding seçimlerini döner (profilden güncelleme için)."""
    permission_classes = [IsAuthenticated, IsVerified]

    def get(self, request):
        user = request.user
        steps_data = []
        steps = OnboardingStep.objects.filter(is_active=True).order_by('order', 'id')
        for step in steps:
            if step.step_type == 'category':
                cat_ids = list(
                    UserOnboardingCategorySelection.objects.filter(
                        user=user, step=step
                    ).values_list('category_id', flat=True)
                )
                steps_data.append({'step_id': step.id, 'step_type': 'category', 'category_ids': cat_ids, 'choice_ids': [], 'tag_ids': []})
            elif step.step_type == 'custom':
                choice_ids = list(
                    UserOnboardingSelection.objects.filter(
                        user=user, choice__step=step
                    ).values_list('choice_id', flat=True)
                )
                steps_data.append({'step_id': step.id, 'step_type': 'custom', 'choice_ids': choice_ids, 'category_ids': [], 'tag_ids': []})
            elif step.step_type == 'tag':
                tag_ids = list(TagFollow.objects.filter(user=user).values_list('tag_id', flat=True))
                steps_data.append({'step_id': step.id, 'step_type': 'tag', 'tag_ids': tag_ids, 'choice_ids': [], 'category_ids': []})
            else:
                steps_data.append({'step_id': step.id, 'step_type': getattr(step, 'step_type', ''), 'choice_ids': [], 'category_ids': [], 'tag_ids': []})
        return Response({'steps': steps_data})


class OnboardingSubmitView(APIView):
    """Bir adım için kullanıcı seçimlerini kaydet. Tamamlanmış kullanıcı güncelleme yapıyorsa ilgili adımın seçimleri yenileriyle değiştirilir."""
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request):
        step_id = request.data.get('step_id')
        category_ids = request.data.get('category_ids', []) or []
        tag_ids = request.data.get('tag_ids', []) or []
        choice_ids = request.data.get('choice_ids', []) or []

        if not step_id:
            return Response({'detail': 'step_id gerekli'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            step = OnboardingStep.objects.get(pk=step_id, is_active=True)
        except OnboardingStep.DoesNotExist:
            return Response({'detail': 'Adım bulunamadı'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        is_update = _user_has_completed_onboarding(user)

        if getattr(step, 'is_optional', False) and not category_ids and not tag_ids and not choice_ids:
            if is_update and step.step_type == 'category':
                prev = list(UserOnboardingCategorySelection.objects.filter(user=user, step=step).values_list('category_id', flat=True))
                UserOnboardingCategorySelection.objects.filter(user=user, step=step).delete()
                for cid in prev:
                    CategoryFollow.objects.filter(user=user, category_id=cid).delete()
            elif is_update and step.step_type == 'custom':
                UserOnboardingSelection.objects.filter(user=user, choice__step=step).delete()
            return Response({'status': 'ok'})

        if step.step_type == 'category':
            if not category_ids:
                return Response({'detail': 'En az bir kategori seçin'}, status=status.HTTP_400_BAD_REQUEST)
            if step.max_selections and len(category_ids) > step.max_selections:
                return Response({'detail': f'En fazla {step.max_selections} kategori seçebilirsiniz'}, status=status.HTTP_400_BAD_REQUEST)
            if is_update:
                prev = list(UserOnboardingCategorySelection.objects.filter(user=user, step=step).values_list('category_id', flat=True))
                UserOnboardingCategorySelection.objects.filter(user=user, step=step).delete()
                for cid in prev:
                    CategoryFollow.objects.filter(user=user, category_id=cid).delete()
            for cid in category_ids:
                try:
                    cat = Category.objects.get(pk=cid)
                    CategoryFollow.objects.get_or_create(user=user, category=cat)
                    UserOnboardingCategorySelection.objects.get_or_create(
                        user=user, step=step, category=cat,
                        defaults={}
                    )
                except Category.DoesNotExist:
                    pass

        elif step.step_type == 'tag':
            if not tag_ids:
                return Response({'detail': 'En az bir etiket seçin'}, status=status.HTTP_400_BAD_REQUEST)
            if step.max_selections and len(tag_ids) > step.max_selections:
                return Response({'detail': f'En fazla {step.max_selections} etiket seçebilirsiniz'}, status=status.HTTP_400_BAD_REQUEST)
            for tid in tag_ids:
                try:
                    tag = Tag.objects.get(pk=tid)
                    TagFollow.objects.get_or_create(user=user, tag=tag)
                except Tag.DoesNotExist:
                    pass

        elif step.step_type == 'custom':
            if not choice_ids:
                return Response({'detail': 'En az bir seçenek seçin'}, status=status.HTTP_400_BAD_REQUEST)
            if step.max_selections and len(choice_ids) > step.max_selections:
                return Response({'detail': f'En fazla {step.max_selections} seçenek seçebilirsiniz'}, status=status.HTTP_400_BAD_REQUEST)
            if is_update:
                UserOnboardingSelection.objects.filter(user=user, choice__step=step).delete()
            for cid in choice_ids:
                try:
                    choice = OnboardingChoice.objects.get(pk=cid, step=step)
                    UserOnboardingSelection.objects.get_or_create(user=user, choice=choice)
                except OnboardingChoice.DoesNotExist:
                    pass

        return Response({'status': 'ok'})


class OnboardingCompleteView(APIView):
    """Onboarding'i tamamla"""
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request):
        obj, _ = UserOnboarding.objects.get_or_create(user=request.user)
        obj.completed_at = timezone.now()
        obj.save()
        return Response({'status': 'ok', 'completed_at': obj.completed_at.isoformat()})


class OnboardingStatusView(APIView):
    """Kullanıcının onboarding durumunu kontrol et. Giriş yapmamışsa completed: true döner (yönlendirme yapılmaz)."""
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'completed': True, 'completed_at': None})
        obj, _ = UserOnboarding.objects.get_or_create(user=request.user)
        return Response({
            'completed': obj.completed_at is not None,
            'completed_at': obj.completed_at.isoformat() if obj.completed_at else None,
        })


class OnboardingCategoriesView(APIView):
    """Kategori adımı için mevcut kategorileri getir. gender=kadin|erkek|belirtmiyorum ile cinsiyete göre filtrelenir."""
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db.models import Q
        gender = (request.query_params.get('gender') or '').strip().lower()
        qs = Category.objects.all().order_by('parent_id', 'order', 'name')
        if gender in ('kadin', 'erkek'):
            qs = qs.filter(Q(target_gender='hepsi') | Q(target_gender=gender))
        elif gender != 'belirtmiyorum':
            pass
        cats = qs.values('id', 'name', 'slug', 'parent_id', 'target_gender')
        return Response(list(cats))


class OnboardingTagsView(APIView):
    """Etiket adımı için mevcut etiketleri getir"""
    permission_classes = [AllowAny]

    def get(self, request):
        tags = Tag.objects.all()
        return Response(TagSerializer(tags, many=True).data)
