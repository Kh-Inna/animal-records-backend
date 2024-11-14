"""
URL configuration for api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from category import views
from rest_framework import permissions
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
      description="Test description",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
# Категория (услуга)
    path('category/', views.get_category_list, name='category_list'),
    path('category/post', views.post_category, name='category_post'),
    path('category/<int:pk>', views.get_category, name='category'),
    path('category/<int:pk>/delete', views.delete_category, name='category_delete'),
    path('category/<int:pk>/put', views.put_category, name='category_put'),
    path('category/<int:pk>/add', views.post_category_to_request, name='category_add'),
    path('category/<int:pk>/add_image', views.post_category_image, name='category_add_image'),
# Животное (заявка)
    path('animal/', views.get_animal, name='animal'),
    path('animal/<int:pk>', views.get_animal_request, name='animal_request'),
    path('animal/<int:pk>/put', views.put_animal, name='animal_put'),
    path('animal/<int:pk>/form', views.form_animal, name='form_animal'),
    path('animal/<int:pk>/resolve', views.resolve_animal, name='animal_resolve'),
    path('animal/<int:pk>/delete', views.delete_animal, name='animal_delete'),
# SoftwareInRequest
    path('record/<int:animal_pk>/<int:category_pk>/put', views.put_record, name='record_put'),
    path('record/<int:animal_pk>/<int:category_pk>/delete', views.delete_record, name='record_delete'),
 # User
    path('users/create', views.create_user, name='users_create'),
    path('users/login', views.login_user, name='users_login'),
    path('users/logout', views.logout_user, name='users_logout'),
    path('users/update', views.update_user, name='users_update'),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

]
