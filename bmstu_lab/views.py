from django.shortcuts import render, redirect, get_object_or_404, redirect
from django.db import connection, transaction
from django.db.models import Q
from django.urls import reverse
from django.contrib import messages
from datetime import date
from django.utils import timezone
from bmstu_lab.models import Category, Animal, AnimalCategory

def get_category_list(request):
    category_query = request.GET.get('category')
    categories = Category.objects.all()
    category_query = ''
    if category_query:
        categories = categories.filter(title__icontains=category_query)
    last_draft_animal = Animal.objects.filter(status="DRAFT").order_by('-creation_date').first()
    animal_id = last_draft_animal.id if last_draft_animal else 0
    animal_cnt = Animal.objects.filter(status="DRAFT").count()
    context = {
        'data': {
            'current_date': timezone.now().date(),
            'categories': categories,
            'category_query': category_query,
            'animal_id': animal_id,
            'animal_cnt': animal_cnt 
        }
    }
    return render(request, 'categories.html', context)

def get_category_detail(request, id):
    category = get_object_or_404(Category, pk=id) 
    return render(request, 'category.html', {
        'data': {
            'current_date': date.today(),
            'title': category.title,
            'photo': category.photo,
            'description': category.description,
        }
    })

def get_animal(request, id):
    animal = get_object_or_404(Animal, pk=id)  
    categories = AnimalCategory.objects.filter(animal=animal)
    formatted_categories = [
        {'category': category.category, 'record': category.record} 
        for category in categories
    ]
    return render(request, 'animal.html', {'animal': animal, 'categories': formatted_categories})

def add_category_to_animal(animal_id, category_id):
    with transaction.atomic():
        animal_category, created = AnimalCategory.objects.get_or_create(
            animal_id=animal_id,
            category_id=category_id,
        )
        if not created:
            animal_category.save()
    return animal_id

def add_to_animal(request, animal_id, category_id):
    if request.method == 'POST':
        try:
            animal = Animal.objects.get(pk=animal_id)
            if animal.status == "DELETE":
                new_animal = Animal.objects.create(
                    status="DRAFT", 
                    animal="",
                    period="",
                    habitat="",
                    creation_date=timezone.now(),
                    creator_id=None,
                    moderator_id=None,
                )
                animal_id = new_animal.id
        except Animal.DoesNotExist:
            animal = Animal.objects.create(
                status="DRAFT", 
                animal="",
                period="",
                habitat="",
                creation_date=timezone.now(),
                creator_id=None,
                moderator_id=None,
            )
            animal_id = animal.id
        add_category_to_animal(animal_id, category_id)
        
        return redirect('categories')
    else:
        return redirect('categories')
    

def remove_category(request, animal_id, category_id):
    if request.method == 'POST':
        try:
            AnimalCategory.objects.get(animal_id=animal_id, category_id=category_id).delete()
            return redirect(reverse('animal', args=[animal_id]))  
        except AnimalCategory.DoesNotExist:
            messages.error(request, "Категория не найдена.")
            return redirect(reverse('animal', args=[animal_id]))
    else:
        return redirect('categories') 
    
def delete_animal_and_related_categories(animal_id):
    with transaction.atomic():
        AnimalCategory.objects.filter(animal_id=animal_id).delete()
        animal = Animal.objects.get(pk=animal_id)
        animal.status = "DELETE"
        animal.save()

    return True

def delete_animal(request, animal_id):
    if request.method == 'POST':
        try:
            animal = Animal.objects.get(pk=animal_id)
            animal.status = "DELETE" 
            animal.save()
            messages.success(request, "Заявка успешно удалена.")
            return redirect('categories') 
        except Animal.DoesNotExist:
            messages.error(request, "Заявка не найдена.")
            return redirect('categories')
    else:
        return redirect('categories')