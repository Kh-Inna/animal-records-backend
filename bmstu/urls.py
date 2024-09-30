from django.contrib import admin
from django.urls import path
from bmstu_lab import views

urlpatterns = [
    path('', views.get_category_list, name='categories'), 
    path('detail/<int:id>/', views.get_category_detail, name='category_detail'), 
    path('animal/<int:id>/', views.get_animal, name='animal'), 
]