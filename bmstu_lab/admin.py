from django.contrib import admin
from .models import Category, Animal, AnimalCategory

admin.site.register(Category)
admin.site.register(Animal)
admin.site.register(AnimalCategory)