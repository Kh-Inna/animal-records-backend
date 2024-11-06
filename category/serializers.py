from rest_framework import serializers
from category.models import Category, Animal, AnimalCategory
from django.contrib.auth.models import User

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "pk", "title", "photo", "is_active", "measurement", "description"
            ]

class CreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username"
            ]

class AnimalSerializer(serializers.ModelSerializer):
  creator = CreatorSerializer()

  class Meta:
    model = Animal
    fields = [
      "pk", "status", "animal", "period", "habitat", "creation_date", "formation_date",
      "completion_date", "creator", "moderator", "record_date"
    ]




class PutAnimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Animal
        fields = [
        "pk", "status", "animal", "period", "habitat", "creation_date", "formation_date",
        "completion_date", "creator", "moderator", "record_date"
        ]
        read_only_fields  = [
        "pk", "status", "animal", "period", "habitat", "creation_date", "formation_date",
        "completion_date", "creator", "moderator", "record_date"
        ]

class ResolveAnimalSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if data.get('status', '') not in (
                Animal.RequestStatus.COMPLETED, Animal.RequestStatus.REJECTED,):
            raise serializers.ValidationError("invalid status")
        return data

    class Meta:
        model = Animal
        fields = [
        "pk", "status", "animal", "period", "habitat", "creation_date", "formation_date",
        "completion_date", "creator", "moderator", "record_date"
        ]
        read_only_fields  = [
        "pk", "animal", "period", "habitat", "creation_date", "formation_date",
        "completion_date", "creator", "moderator", "record_date"
        ]
    
class AnimalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalCategory
        fields = [
        "animal", "category", "record"
        ]




class CategoryForRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "pk", "title", "photo", "measurement",
            ]


class RelatedSerializer(serializers.ModelSerializer):
    category = CategoryForRequestSerializer()

    class Meta:
        model = AnimalCategory
        fields = [
            "category", "record"
            ]


class FullAnimalSerializer(serializers.ModelSerializer):
    category_list = RelatedSerializer(source='animalcategory_set', many=True)

    class Meta:
        model = Animal
        fields = [
            "pk", "status", "animal", "period", "habitat", "creation_date", "formation_date",
            "completion_date", "creator", "moderator", "category_list", "record_date"
            ]





class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', '')
        )
        return user

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        instance.save()
        return instance