from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404

from core.permissions import IsVerified
from .models import Community, CommunityMember
from .serializers import CommunityListSerializer, CommunityCreateSerializer, CommunityDetailSerializer


class CommunityListView(generics.ListAPIView):
    """Kategorive göre topluluk listesi. ?category=slug ile filtre."""
    serializer_class = CommunityListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Community.objects.select_related('category', 'owner').prefetch_related('members')
        category_slug = self.request.query_params.get('category', '').strip()
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        return qs.order_by('-created_at')


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


class CommunityJoinView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug):
        community = get_object_or_404(Community, slug=slug)
        _, created = CommunityMember.objects.get_or_create(user=request.user, community=community)
        return Response({'joined': created, 'member_count': community.members.count()})


class CommunityLeaveView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, slug):
        community = get_object_or_404(Community, slug=slug)
        CommunityMember.objects.filter(user=request.user, community=community).delete()
        return Response({'member_count': community.members.count()})
