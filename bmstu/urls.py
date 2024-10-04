from django.contrib import admin
from django.urls import path
from bmstu_lab import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.get_category_list, name='categories'),
    path('add_to_animal/<int:animal_id>/<int:category_id>/', views.add_to_animal, name='add_to_animal'),
    path('detail/<int:id>/', views.get_category_detail, name='category_detail'), 
    path('animal/<int:id>/', views.get_animal, name='animal'), 
    path('delete_animal/<int:animal_id>/', views.delete_animal, name='delete_animal'),
]