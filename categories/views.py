from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Category, CategoryFollow
from .serializers import CategorySerializer, CategoryListSerializer


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(parent=None).prefetch_related('subcategories')
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class CategoryDetailView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


from rest_framework.views import APIView


class CategoryFollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        category = Category.objects.get(pk=pk)
        _, created = CategoryFollow.objects.get_or_create(user=request.user, category=category)
        return Response({'followed': created})


class CategoryUnfollowView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        CategoryFollow.objects.filter(user=request.user, category_id=pk).delete()
        return Response(status=204)
