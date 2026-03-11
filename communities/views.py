from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.permissions import IsVerified
from .models import (
    Community,
    CommunityMember,
    CommunityBan,
    CommunityJoinRequest,
    JOIN_TYPE_OPEN,
    JOIN_TYPE_APPROVAL,
    MEMBER_ROLE_MOD,
)
from .serializers import (
    CommunityListSerializer,
    CommunityCreateSerializer,
    CommunityDetailSerializer,
)


def _is_mod_or_owner(community, user):
    if not user or not user.is_authenticated:
        return False
    if community.owner_id == user.pk:
        return True
    return community.members.filter(user=user, role=MEMBER_ROLE_MOD).exists()


class CommunityListView(generics.ListAPIView):
    """Kategoriye göre topluluk listesi. ?category=slug ile filtre."""
    serializer_class = CommunityListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Community.objects.select_related('category', 'owner').prefetch_related('members')
        category_slug = self.request.query_params.get('category', '').strip()
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs.order_by('-created_at')


class CommunityMyManagedListView(generics.ListAPIView):
    """Giriş yapmış kullanıcının sahip veya mod olduğu topluluklar (profilde 'Oluşturduğum topluluklar')."""
    serializer_class = CommunityListSerializer
    permission_classes = [IsAuthenticated, IsVerified]
    pagination_class = None  # Profil için kısa liste, sayfalama yok

    def get_queryset(self):
        user = self.request.user
        from django.db.models import Q
        return (
            Community.objects.filter(Q(owner=user) | Q(members__user=user, members__role=MEMBER_ROLE_MOD))
            .select_related('category', 'owner')
            .prefetch_related('members')
            .distinct()
            .order_by('-created_at')
        )


class CommunityMyJoinedListView(generics.ListAPIView):
    """Giriş yapmış kullanıcının üye olduğu topluluklar (profilde 'Takip ettiklerim' alanında)."""
    serializer_class = CommunityListSerializer
    permission_classes = [IsAuthenticated, IsVerified]
    pagination_class = None

    def get_queryset(self):
        return (
            Community.objects.filter(members__user=self.request.user)
            .select_related('category', 'owner')
            .prefetch_related('members')
            .distinct()
            .order_by('-created_at')
        )


class CommunityCreateView(generics.CreateAPIView):
    """Topluluk oluştur (giriş + doğrulanmış kullanıcı)."""
    queryset = Community.objects.all()
    serializer_class = CommunityCreateSerializer
    permission_classes = [IsAuthenticated, IsVerified]


class CommunityDetailView(generics.RetrieveAPIView):
    """Tekil topluluk detay."""
    queryset = Community.objects.select_related('category', 'owner').prefetch_related('members')
    serializer_class = CommunityDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'


class CommunityUpdateView(generics.UpdateAPIView):
    """Topluluk güncelle (sadece sahip veya mod)."""
    queryset = Community.objects.all()
    serializer_class = CommunityCreateSerializer
    permission_classes = [IsAuthenticated, IsVerified]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs
        from django.db.models import Q
        return qs.filter(Q(owner=user) | Q(members__user=user, members__role=MEMBER_ROLE_MOD))

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())


class CommunityJoinView(APIView):
    """Katıl: open ise doğrudan üye; approval ise talep oluştur. Yasaklı ise 403."""
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug):
        community = get_object_or_404(Community, slug=slug)
        if CommunityBan.objects.filter(community=community, user=request.user).exists():
            return Response(
                {'detail': 'Bu topluluktan yasaklandınız.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if CommunityMember.objects.filter(community=community, user=request.user).exists():
            return Response({'joined': False, 'member_count': community.members.count()})

        if community.join_type == JOIN_TYPE_OPEN:
            CommunityMember.objects.create(user=request.user, community=community)
            return Response({'joined': True, 'member_count': community.members.count()})

        if community.join_type == JOIN_TYPE_APPROVAL:
            req, created = CommunityJoinRequest.objects.get_or_create(
                user=request.user,
                community=community,
                defaults={'status': 'pending'},
            )
            if not created and req.status == 'pending':
                return Response(
                    {'detail': 'Zaten bir katılım talebiniz beklemede.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not created:
                req.status = 'pending'
                req.reviewed_by = None
                req.reviewed_at = None
                req.save()
            # Sahip ve tüm modlara bildirim
            try:
                from notifications.services import create_notification
                message = f"{request.user.username} r/{community.slug} topluluğunuza katılmak istiyor."
                recipients = [community.owner_id]
                recipients.extend(
                    community.members.filter(role=MEMBER_ROLE_MOD).values_list('user_id', flat=True)
                )
                for uid in set(recipients):
                    if uid != request.user.pk:
                        from django.contrib.auth import get_user_model
                        U = get_user_model()
                        create_notification(
                            U.objects.get(pk=uid),
                            request.user,
                            'community_join_request',
                            message,
                            community=community,
                        )
            except Exception:
                pass
            return Response(
                {'joined': False, 'request_sent': True, 'member_count': community.members.count()},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response({'joined': False, 'member_count': community.members.count()})


class CommunityLeaveView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug):
        community = get_object_or_404(Community, slug=slug)
        if community.owner_id == request.user.pk:
            return Response(
                {'detail': 'Topluluk sahibi topluluktan ayrılamaz. Topluluğu silmek için destek ile iletişime geçin.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        CommunityMember.objects.filter(user=request.user, community=community).delete()
        return Response({'member_count': community.members.count()})


class CommunityJoinRequestListView(generics.ListAPIView):
    """Bekleyen katılım talepleri (sadece mod/sahip)."""
    permission_classes = [IsAuthenticated, IsVerified]

    def get_queryset(self):
        slug = self.kwargs['slug']
        community = get_object_or_404(Community, slug=slug)
        if not _is_mod_or_owner(community, self.request.user):
            return CommunityJoinRequest.objects.none()
        return (
            CommunityJoinRequest.objects.filter(community=community, status='pending')
            .select_related('user')
            .order_by('created_at')
        )

    def list(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        qs = self.get_queryset()
        data = [
            {
                'id': r.id,
                'user_id': r.user_id,
                'username': r.user.username,
                'created_at': r.created_at,
            }
            for r in qs
        ]
        return Response(data)


class CommunityJoinRequestApproveView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug, request_id):
        community = get_object_or_404(Community, slug=slug)
        if not _is_mod_or_owner(community, request.user):
            return Response({'detail': 'Yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        join_req = get_object_or_404(
            CommunityJoinRequest,
            id=request_id,
            community=community,
            status='pending',
        )
        join_req.status = 'approved'
        join_req.reviewed_by = request.user
        join_req.reviewed_at = timezone.now()
        join_req.save()
        CommunityMember.objects.get_or_create(user=join_req.user, community=community)
        return Response({'approved': True, 'member_count': community.members.count()})


class CommunityJoinRequestRejectView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug, request_id):
        community = get_object_or_404(Community, slug=slug)
        if not _is_mod_or_owner(community, request.user):
            return Response({'detail': 'Yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        join_req = get_object_or_404(
            CommunityJoinRequest,
            id=request_id,
            community=community,
            status='pending',
        )
        join_req.status = 'rejected'
        join_req.reviewed_by = request.user
        join_req.reviewed_at = timezone.now()
        join_req.save()
        return Response({'rejected': True})


class CommunityBanUserView(APIView):
    """Kullanıcıyı topluluktan yasakla (mod/sahip)."""
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug):
        community = get_object_or_404(Community, slug=slug)
        if not _is_mod_or_owner(community, request.user):
            return Response({'detail': 'Yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id gerekli.'}, status=status.HTTP_400_BAD_REQUEST)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        target = get_object_or_404(User, id=user_id)
        if target.pk == community.owner_id:
            return Response({'detail': 'Topluluk sahibi yasaklanamaz.'}, status=status.HTTP_400_BAD_REQUEST)
        CommunityMember.objects.filter(community=community, user=target).delete()
        CommunityJoinRequest.objects.filter(community=community, user=target).update(status='rejected')
        CommunityBan.objects.get_or_create(
            community=community,
            user=target,
            defaults={'banned_by': request.user, 'reason': request.data.get('reason', '')},
        )
        return Response({'banned': True, 'member_count': community.members.count()})


class CommunityUnbanUserView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug, user_id):
        community = get_object_or_404(Community, slug=slug)
        if not _is_mod_or_owner(community, request.user):
            return Response({'detail': 'Yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        CommunityBan.objects.filter(community=community, user_id=user_id).delete()
        return Response({'unbanned': True})


class CommunityBannedListView(generics.ListAPIView):
    """Yasaklı kullanıcı listesi (mod/sahip)."""
    permission_classes = [IsAuthenticated, IsVerified]

    def get_queryset(self):
        slug = self.kwargs['slug']
        community = get_object_or_404(Community, slug=slug)
        if not _is_mod_or_owner(community, self.request.user):
            return CommunityBan.objects.none()
        return CommunityBan.objects.filter(community=community).select_related('user', 'banned_by').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = [
            {
                'id': b.id,
                'user_id': b.user_id,
                'username': b.user.username,
                'reason': b.reason,
                'banned_at': b.created_at,
            }
            for b in qs
        ]
        return Response(data)


class CommunityQuestionsView(generics.ListAPIView):
    """Topluluk sayfasındaki sorular (onaylı, toplulukla eşleşen)."""
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        from questions.serializers import QuestionListSerializer
        return QuestionListSerializer

    def get_queryset(self):
        from questions.models import Question
        slug = self.kwargs['slug']
        community = get_object_or_404(Community, slug=slug)
        return (
            Question.objects.filter(community=community)
            .exclude(status='draft')
            .filter(moderation_status=1)
            .select_related('author', 'category', 'community')
            .prefetch_related('tags')
            .order_by('-created_at')
        )


class CommunityRemoveQuestionView(APIView):
    """Mod/owner: Soruyu topluluktan kaldır. Sebep yazılırsa gönderi sahibine bildirim gider."""
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug):
        community = get_object_or_404(Community, slug=slug)
        if not _is_mod_or_owner(community, request.user):
            return Response({'detail': 'Bu işlem için yetkiniz yok.'}, status=status.HTTP_403_FORBIDDEN)
        question_id = request.data.get('question_id')
        reason = (request.data.get('reason') or '').strip()
        if not question_id:
            return Response({'detail': 'question_id gerekli.'}, status=status.HTTP_400_BAD_REQUEST)
        from questions.models import Question
        question = get_object_or_404(Question, pk=question_id, community=community)
        author = question.author
        question.community = None
        question.save(update_fields=['community'])
        if reason and author.pk != request.user.pk:
            from notifications.services import create_notification
            msg = f"r/{community.slug} topluluğunda paylaştığınız bir gönderi topluluktan kaldırıldı."
            if reason:
                msg += f" Sebep: {reason}"
            create_notification(author, request.user, 'community_post_removed', msg, question=question, community=community)
        return Response({'detail': 'Gönderi topluluktan kaldırıldı.'}, status=status.HTTP_200_OK)
