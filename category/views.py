import os
import random
import uuid

from datetime import datetime, timedelta

from dateutil.parser import parse

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes, parser_classes
from rest_framework.parsers import FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from api import settings
from .auth import AuthBySessionID, AuthBySessionIDIfExists, IsAuth, IsManagerAuth
from .minio import MinioStorage
from .models import Animal, AnimalCategory, Category
from .serializers import *
from .redis import session_storage


SINGLETON_USER = User(id=1, username="admin")
SINGLETON_MANAGER = User(id=2, username="manager")



# Категория (услуга)
@swagger_auto_schema(method='get',
                     manual_parameters=[
                         openapi.Parameter('category_title',
                                           type=openapi.TYPE_STRING,
                                           description='category_title',
                                           in_=openapi.IN_QUERY),
                     ],
                     responses={
                         status.HTTP_200_OK: GetCategorySerializer,
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['GET'])
@permission_classes([AllowAny])
@authentication_classes([AuthBySessionIDIfExists])
def get_category_list(request):
    """
    Получение списка категорий
    """
    user = request.user
    category_title = request.query_params.get("category_title", "")
    category_list = Category.objects.filter(title__istartswith=category_title, is_active=True).order_by('title')
    
    req = None
    items_in_cart = 0

    if user is not None:
        req = Animal.objects.filter(creator_id=user.pk, status=Animal.RequestStatus.DRAFT).first()
        if req is not None:
            items_in_cart = AnimalCategory.objects.filter(animal=req.id).count()
    
    serializer = GetCategorySerializer(
        {
            "categories": CategorySerializer(category_list,many=True).data,
            "animal_id": req.id if req else None,
            "items_in_cart": items_in_cart,
        },
    )
    return Response(serializer.data, status=status.HTTP_200_OK)

@swagger_auto_schema(method='post',
                     request_body=CategorySerializer,
                     responses={
                         status.HTTP_200_OK: CategorySerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['POST'])
@permission_classes([IsManagerAuth])
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

@swagger_auto_schema(method="post",
                     manual_parameters=[
                         openapi.Parameter(name="photo",
                                           in_=openapi.IN_QUERY,
                                           type=openapi.TYPE_FILE,
                                           required=True, description="photo")],
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['POST'])
@permission_classes([IsManagerAuth])
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

@swagger_auto_schema(method='get',
                     responses={
                         status.HTTP_200_OK: CategorySerializer(),
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['GET'])
@permission_classes([AllowAny])
def get_category(request, pk):
    """
    Получение категории
    """
    category = Category.objects.filter(id=pk).first()
    if category is None:
        return Response("Category not found", status=status.HTTP_404_NOT_FOUND)
    serialized_category = CategorySerializer(category)
    return Response(serialized_category.data, status=status.HTTP_200_OK)

@swagger_auto_schema(method='delete',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['DELETE'])
@permission_classes([IsManagerAuth])
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

@swagger_auto_schema(method='put',
                     request_body=CategorySerializer,
                     responses={
                         status.HTTP_200_OK: CategorySerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['PUT'])
@permission_classes([IsManagerAuth])
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

@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_400_BAD_REQUEST: "Bad request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['POST'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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

@swagger_auto_schema(method='get',
                     manual_parameters=[
                         openapi.Parameter('status',
                                           type=openapi.TYPE_STRING,
                                           description='status',
                                           in_=openapi.IN_QUERY),
                         openapi.Parameter('formation_start',
                                           type=openapi.TYPE_STRING,
                                           description='status',
                                           in_=openapi.IN_QUERY,
                                           format=openapi.FORMAT_DATETIME),
                         openapi.Parameter('formation_end',
                                           type=openapi.TYPE_STRING,
                                           description='status',
                                           in_=openapi.IN_QUERY,
                                           format=openapi.FORMAT_DATETIME),
                     ],
                     responses={
                         status.HTTP_200_OK: AnimalSerializer(many=True),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['GET'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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

@swagger_auto_schema(method='get',
                     responses={
                         status.HTTP_200_OK: FullAnimalSerializer(),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['GET'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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

@swagger_auto_schema(method='put',
                     request_body=PutAnimalSerializer,
                     responses={
                         status.HTTP_200_OK: PutAnimalSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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

@swagger_auto_schema(method='put',
                     responses={
                         status.HTTP_200_OK: AnimalSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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

@swagger_auto_schema(method='put',
                     responses={
                         status.HTTP_200_OK: ResolveAnimalSerializer(),
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['PUT'])
@permission_classes([IsManagerAuth])
@authentication_classes([AuthBySessionID])
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
    animal.record_date = animal.completion_date + timedelta(days=random.randint(1, 30))
    animal.save()

    serializer = AnimalSerializer(animal)
    return Response(serializer.data)

@swagger_auto_schema(method='delete',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['DELETE'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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
@swagger_auto_schema(method='put',
                     request_body=AnimalCategorySerializer,
                     responses={
                         status.HTTP_200_OK: AnimalCategorySerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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


@swagger_auto_schema(method='delete',
                     responses={
                         status.HTTP_200_OK: "OK",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                         status.HTTP_404_NOT_FOUND: "Not Found",
                     })
@api_view(['DELETE'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
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

@swagger_auto_schema(method='post',
                     request_body=UserSerializer,
                     responses={
                         status.HTTP_201_CREATED: "Created",
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                     })
@api_view(['POST'])
@permission_classes([AllowAny])
def create_user(request):
    """
    Создание пользователя
    """
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_204_NO_CONTENT: "No content",
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                     },
                     manual_parameters=[
                         openapi.Parameter('username',
                                           type=openapi.TYPE_STRING,
                                           description='username',
                                           in_=openapi.IN_FORM,
                                           required=True),
                         openapi.Parameter('password',
                                           type=openapi.TYPE_STRING,
                                           description='password',
                                           in_=openapi.IN_FORM,
                                           required=True)
                     ])
@api_view(['POST'])
@parser_classes((FormParser,))
@permission_classes([AllowAny])
def login_user(request):
    """
    Вход
    """
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        session_id = str(uuid.uuid4())
        session_storage.set(session_id, username)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.set_cookie("session_id", session_id, samesite="lax")
        return response
    return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(method='post',
                     responses={
                         status.HTTP_204_NO_CONTENT: "No content",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['POST'])
@permission_classes([IsAuth])
def logout_user(request):
    """
    Выход
    """
    session_id = request.COOKIES["session_id"]
    if session_storage.exists(session_id):
        session_storage.delete(session_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(status=status.HTTP_403_FORBIDDEN)


@swagger_auto_schema(method='put',
                     request_body=UserUpdateSerializer,
                     responses={
                         status.HTTP_200_OK: UserSerializer(),
                         status.HTTP_400_BAD_REQUEST: "Bad Request",
                         status.HTTP_403_FORBIDDEN: "Forbidden",
                     })
@api_view(['PUT'])
@permission_classes([IsAuth])
@authentication_classes([AuthBySessionID])
def update_user(request):
    """
    Обновление данных пользователя
    """
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)