from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType
from core.permissions import IsVerified
from .models import SavedCollection, SavedItem
from .serializers import SavedCollectionSerializer, SavedItemSerializer
from questions.models import Question


def get_or_create_default_collection(user):
    """Get or create the default 'Kaydettiklerim' collection for user."""
    coll, created = SavedCollection.objects.get_or_create(
        user=user,
        name='Kaydettiklerim',
        defaults={'is_default': True}
    )
    if created:
        SavedCollection.objects.filter(user=user).exclude(pk=coll.pk).update(is_default=False)
    return coll


class SavedCollectionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = SavedCollectionSerializer

    def get_queryset(self):
        return SavedCollection.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavedCollectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = SavedCollectionSerializer

    def get_queryset(self):
        return SavedCollection.objects.filter(user=self.request.user)


class SavedCollectionItemsView(generics.ListAPIView):
    """List saved items in a collection"""
    permission_classes = [IsAuthenticated, IsVerified]
    serializer_class = SavedItemSerializer

    def get_queryset(self):
        return SavedItem.objects.filter(
            collection__user=self.request.user,
            collection_id=self.kwargs['pk']
        )


class SaveToCollectionView(generics.CreateAPIView):
    """Save a question to a collection (or create default and save)"""
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, question_id, *args, **kwargs):
        try:
            question = Question.objects.get(pk=question_id)
        except Question.DoesNotExist:
            return Response({'detail': 'Soru bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)

        collection_id = request.data.get('collection_id')
        if collection_id:
            try:
                collection = SavedCollection.objects.get(
                    pk=collection_id,
                    user=request.user
                )
            except SavedCollection.DoesNotExist:
                return Response({'detail': 'Koleksiyon bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            collection = get_or_create_default_collection(request.user)

        ct = ContentType.objects.get_for_model(Question)
        item, created = SavedItem.objects.get_or_create(
            collection=collection,
            content_type=ct,
            object_id=question.pk
        )
        if created:
            return Response({
                'id': item.id,
                'collection': SavedCollectionSerializer(collection).data,
                'message': 'Kaydedildi'
            }, status=status.HTTP_201_CREATED)
        return Response({
            'id': item.id,
            'collection': SavedCollectionSerializer(collection).data,
            'message': 'Zaten bu koleksiyonda'
        }, status=status.HTTP_200_OK)


class CheckSavedView(generics.GenericAPIView):
    """Check if a question is saved by current user"""
    permission_classes = [IsAuthenticated, IsVerified]

    def get(self, request, question_id, *args, **kwargs):
        ct = ContentType.objects.get_for_model(Question)
        items = SavedItem.objects.filter(
            collection__user=request.user,
            content_type=ct,
            object_id=question_id
        ).select_related('collection')
        collections = [SavedCollectionSerializer(i.collection).data for i in items]
        return Response({
            'saved': items.exists(),
            'collections': collections
        })


class RemoveFromSavedView(generics.DestroyAPIView):
    """Remove a question from a collection"""
    permission_classes = [IsAuthenticated, IsVerified]

    def delete(self, request, question_id, *args, **kwargs):
        from django.shortcuts import get_object_or_404
        ct = ContentType.objects.get_for_model(Question)
        items = SavedItem.objects.filter(
            collection__user=request.user,
            content_type=ct,
            object_id=question_id
        )
        deleted_count, _ = items.delete()
        if deleted_count:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Kayıt bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)


class CreateCollectionAndSaveView(generics.CreateAPIView):
    """Create a new collection and save the question to it"""
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, question_id, *args, **kwargs):
        try:
            question = Question.objects.get(pk=question_id)
        except Question.DoesNotExist:
            return Response({'detail': 'Soru bulunamadı.'}, status=status.HTTP_404_NOT_FOUND)

        name = request.data.get('name', '').strip()
        if not name:
            return Response({'detail': 'Koleksiyon adı gerekli.'}, status=status.HTTP_400_BAD_REQUEST)

        collection, created = SavedCollection.objects.get_or_create(
            user=request.user,
            name=name,
            defaults={'is_default': False}
        )
        ct = ContentType.objects.get_for_model(Question)
        item, item_created = SavedItem.objects.get_or_create(
            collection=collection,
            content_type=ct,
            object_id=question.pk
        )
        return Response({
            'collection': SavedCollectionSerializer(collection).data,
            'message': 'Kaydedildi'
        }, status=status.HTTP_201_CREATED)
