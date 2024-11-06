import os
from datetime import datetime, timedelta
from django.utils import timezone
from dateutil.parser import parse
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Category, Animal, AnimalCategory
from .serializers import FullAnimalSerializer, CategorySerializer, AnimalSerializer, PutAnimalSerializer, ResolveAnimalSerializer, AnimalCategorySerializer, UserSerializer
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from .minio import MinioStorage
from api import settings
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

SINGLETON_USER = User(id=1, username="admin")
SINGLETON_MANAGER = User(id=2, username="manager")

# Категория (услуга)

@api_view(['GET'])
def get_category_list(request):
    """
    Получение списка категорий
    """
    category_title = request.query_params.get("category_title", "")
    category_list = Category.objects.filter(title__istartswith=category_title, is_active=True).order_by('title')
    req = Animal.objects.filter(creator_id=SINGLETON_USER.id, status=Animal.RequestStatus.DRAFT).first()
    
    items_in_cart = 0
    if req is not None:
        items_in_cart = AnimalCategory.objects.filter(animal=req.id).count()
    serializer = CategorySerializer(category_list, many=True)
    return Response(
        {
            "categories": serializer.data,
            "animal_id": req.id if req else None,
            "items_in_cart": items_in_cart,
        },
        status=status.HTTP_200_OK
    )

@api_view(['POST'])
def post_category(request):
    """
    Добавление категории
    """
    serializer = CategorySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    new_category = serializer.save()
    serializer = CategorySerializer(new_category)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
def post_category_image(request, pk):
    """
    Загрузка изображения категории в Minio
    """
    category = Category.objects.filter(id=pk).first()
    if category is None:
        return Response("category not found", status=status.HTTP_404_NOT_FOUND)

    minio_storage = MinioStorage(endpoint=settings.MINIO_ENDPOINT_URL,
                                 access_key=settings.MINIO_ACCESS_KEY,
                                 secret_key=settings.MINIO_SECRET_KEY,
                                 secure=settings.MINIO_SECURE)

    file = request.FILES.get("photo")
    if not file:
        return Response("No photo in request", status=status.HTTP_400_BAD_REQUEST)

    file_extension = os.path.splitext(file.name)[1]
    file_name = f"{pk}{file_extension}"

    try:
        minio_storage.load_file(settings.MINIO_BUCKET_NAME, file_name, file)
    except Exception as e:
        return Response(f"Failed to load photo: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    category.photo = f"http://{settings.MINIO_ENDPOINT_URL}/{settings.MINIO_BUCKET_NAME}/{file_name}"
    category.save()
    return Response(status=status.HTTP_200_OK)

@api_view(['GET'])
def get_category(request, pk):
    """
    Получение категории
    """
    category = Category.objects.filter(id=pk).first()
    if category is None:
        return Response("Category not found", status=status.HTTP_404_NOT_FOUND)
    serialized_category = CategorySerializer(category)
    return Response(serialized_category.data, status=status.HTTP_200_OK)

@api_view(['DELETE'])
def delete_category(request, pk):
    """
    Удаление категории
    """
    category = Category.objects.filter(id=pk).first()
    if category is None:
        return Response("Category not found", status=status.HTTP_404_NOT_FOUND)

    if category.photo:
        minio_storage = MinioStorage(
            endpoint=settings.MINIO_ENDPOINT_URL,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        file_extension = os.path.splitext(category.photo)[1]
        file_name = f"{pk}{file_extension}"
        
        try:
            minio_storage.delete_file(settings.MINIO_BUCKET_NAME, file_name)
        except Exception as e:
            return Response(f"Failed to delete image: {e}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        category.photo = ""

    category.is_active = False
    category.save()
    
    return Response(status=status.HTTP_200_OK)

@api_view(['PUT'])
def put_category(request, pk):
    """
    Изменение категории
    """
    category = Category.objects.filter(id=pk, is_active=True).first()
    if category is None:
        return Response("category not found", status=status.HTTP_404_NOT_FOUND)

    serializer = CategorySerializer(category, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def post_category_to_request(request, pk):
    """
    Добавление категории в заявку животного
    """
    category = Category.objects.filter(id=pk, is_active=True).first()
    if category is None:
        return Response("category not found", status=status.HTTP_404_NOT_FOUND)
    request_id = get_or_create_user_cart(SINGLETON_USER.id)
    add_item_to_request(request_id, pk)
    return Response(status=status.HTTP_200_OK)

def get_or_create_user_cart(user_id: int) -> int:
    """
    Если у пользователя есть заявка в статусе DRAFT (корзина), возвращает её Id.
    Если нет - создает и возвращает id созданной заявки
    """
    old_req = Animal.objects.filter(creator_id=SINGLETON_USER.id,
                                                    status=Animal.RequestStatus.DRAFT).first()
    if old_req is not None:
        return old_req.id

    new_req = Animal(creator_id=SINGLETON_USER.id,
                                     status=Animal.RequestStatus.DRAFT)
    new_req.save()
    return new_req.id


def add_item_to_request(animal_id: int, category_id: int):
    """
    Добавление категории в заявку
    """
    animal = AnimalCategory(animal_id=animal_id, category_id=category_id)
    animal.save()


# Животное (заявка)

@api_view(['GET'])
def get_animal(request):
    """
    Получение списка заявок животных
    """
    status_filter = request.query_params.get("status")
    formation_datetime_start_filter = request.query_params.get("formation_start")
    formation_datetime_end_filter = request.query_params.get("formation_end")

    filters = ~Q(status=Animal.RequestStatus.DELETED)
    if status_filter is not None:
        filters &= Q(status=status_filter.upper())
    if formation_datetime_start_filter is not None:
        filters &= Q(formation_date__gte=parse(formation_datetime_start_filter))
    if formation_datetime_end_filter is not None:
        filters &= Q(formation_date__lte=parse(formation_datetime_end_filter))

    animals = Animal.objects.filter(filters).select_related("creator")
    serializer = AnimalSerializer(animals, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_animal_request(request, pk):
    """
    Получение животного
    """
    filters = Q(id=pk) & ~Q(status=Animal.RequestStatus.DELETED)
    animal = Animal.objects.filter(filters).first()
    if animal is None:
        return Response("Animal not found", status=status.HTTP_404_NOT_FOUND)

    serializer = FullAnimalSerializer(animal)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT'])
def put_animal(request, pk):
    """
    Изменение животного
    """
    animal = Animal.objects.filter(id=pk, status=Animal.RequestStatus.DRAFT).first()
    if animal is None:
        return Response("animal not found", status=status.HTTP_404_NOT_FOUND)

    serializer = PutAnimalSerializer(animal, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['PUT'])
def form_animal(request, pk):
    """
    Формирование заявки животного
    """
    animal = Animal.objects.filter(id=pk, status=Animal.RequestStatus.DRAFT).first()
    if animal is None:
        return Response("Animal not found", status=status.HTTP_404_NOT_FOUND)
    
    animal.status = Animal.RequestStatus.FORMED
    animal.formation_date = timezone.now()
    animal.save()
    serializer = AnimalSerializer(animal)
    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['PUT'])
def resolve_animal(request, pk):
    """
    Закрытие заявки животного
    """
    animal = Animal.objects.filter(id=pk, status=Animal.RequestStatus.FORMED).first()
    if animal is None:
        return Response("Animal not found", status=status.HTTP_404_NOT_FOUND)

    serializer = ResolveAnimalSerializer(animal, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    animal = Animal.objects.get(id=pk)
    animal.completion_date = datetime.now()
    animal.SINGLETON_MANAGER = SINGLETON_MANAGER
    animal.record_date = animal.completion_date + timedelta(days=30) 
    animal.save()

    serializer = AnimalSerializer(animal)
    return Response(serializer.data)

@api_view(['DELETE'])
def delete_animal(request, pk):
    """
    Удаление животного
    """
    animal = Animal.objects.filter(id=pk, status=Animal.RequestStatus.DRAFT).first()
    if animal is None:
        return Response("Animal not found", status=status.HTTP_404_NOT_FOUND)

    animal.status = Animal.RequestStatus.DELETED
    animal.save()
    return Response(status=status.HTTP_200_OK)

# Рекорд (м-м)

@api_view(['PUT'])
def put_record(request, animal_pk, category_pk):
    """
    Изменение данных о рекорде в заявке
    """
    record = AnimalCategory.objects.filter(animal=animal_pk, category=category_pk).first()
    if record is None:
        return Response("record not found", status=status.HTTP_404_NOT_FOUND)
    serializer = AnimalCategorySerializer(record, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_record(request, animal_pk, category_pk):
    """
    Удаление рекорда из заявки
    """
    record = AnimalCategory.objects.filter(animal=animal_pk, category=category_pk).first()
    if record is None:
        return Response("record not found", status=status.HTTP_404_NOT_FOUND)
    record.delete()
    return Response(status=status.HTTP_200_OK)

# Пользователь

@api_view(['POST'])
def create_user(request):
    """
    Создание пользователя
    """
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login_user(request):
    """
    Вход
    """
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_200_OK)
    return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    Выход
    """
    request.auth.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_user(request):
    """
    Обновление данных пользователя
    """
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)