from rest_framework import serializers
from category.models import Category, Animal, AnimalCategory
from django.contrib.auth.models import User
from collections import OrderedDict

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "pk", "title", "photo", "is_active", "measurement", "description"
            ]

class GetCategorySerializer(serializers.Serializer):
    categories = CategorySerializer(many=True)
    animal_id = serializers.IntegerField(required=False, allow_null=True)
    items_in_cart = serializers.IntegerField()

class CreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username"
            ]

class AnimalSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField()
    moderator = serializers.SerializerMethodField()
    def get_creator(self, obj):
        return obj.creator.username

    def get_moderator(self, obj):
        return obj.moderator.username if obj.moderator else None
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
  record = serializers.SerializerMethodField()

  class Meta:
    model = Category
    fields = [
      "pk", "title", "photo", "measurement", "record"
    ]

  def get_record(self, obj):
    try:
      animal_category = obj.animalcategory_set.first()
      return animal_category.record
    except:
      return None



class FullAnimalSerializer(serializers.ModelSerializer):
  category = serializers.SerializerMethodField() # Change this to SerializerMethodField

  class Meta:
    model = Animal
    fields = [
      "pk", "status", "animal", "period", "habitat", "creation_date", "formation_date",
      "completion_date", "creator", "moderator", "category", "record_date"
    ]

  def get_category(self, obj): # Define a method to get the category
    # Get the AnimalCategory related to the current Animal
    animal_categories = obj.animalcategory_set.all() # Get all related AnimalCategories
    categories = []
    for animal_category in animal_categories:
      # For each related AnimalCategory, get the corresponding Category
      category = animal_category.category 
      # Serialize the Category using CategoryForRequestSerializer
      serialized_category = CategoryForRequestSerializer(category).data 
      categories.append(serialized_category) # Add the serialized category to the list

    return categories



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
    
    def get_fields(self):
            new_fields = OrderedDict()
            for name, field in super().get_fields().items():
                field.required = False
                new_fields[name] = field
            return new_fields

class UserUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def update(self, instance, validated_data):
        if 'email' in validated_data:
            instance.email = validated_data['email']

        if 'password' in validated_data:
            instance.set_password(validated_data['password'])

        instance.save()
        return instance