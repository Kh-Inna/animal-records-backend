from django.shortcuts import render
from datetime import date

category_list =[
    {
        'id': 0,
        'title': 'Самые большие',
        'photo': 'http://127.0.0.1:9000/pic/photo_1.jpg',
        'measurement': 'Метров:',
        'description': 'К этой категории относятся самые большие по размеру животные своего вида. Например: синий кит, африканский слон, гигансткий кальмар. Единицы измерения: метры.',
    },
    {
        'id': 1,
        'title': 'Самые быстрые',
        'photo': 'http://127.0.0.1:9000/pic/photo_2.jpeg',
        'measurement': 'Км/ч:',
        'description': 'К этой категории относятся самые быстрые животные своего вида. Например: сапсан, гепард, рыба-парусник. Единицы измерения: км/ч.',
    },
    {
        'id': 2,
        'title': 'Самые старые',
        'photo': 'http://127.0.0.1:9000/pic/photo_3.jpg',
        'measurement': 'Лет:',
        'description': 'К этой категории относятся самые долгоживущие животные своего вида. Например: гренландский кит, океанская мидия, гигантская морская черепаха. Единицы измерения: года.',
    },
    {
        'id': 3,
        'title': 'Самые громкие',
        'photo': 'http://127.0.0.1:9000/pic/photo_4.jpg',
        'measurement': 'дБ:',
        'description': 'К этой категории относятся самые громкие животные своего вида. Например: синий кит, голубой кит, африканский слон Единицы измерения: дБ.',
    }
]

animal_list = [
    {
        'id': 0,
        'animal': 'Синий кит',
        'period': 'Четвертичный',
        'habitat': 'Океан',
        'categories': [
            {
                'category': category_list[0],
                'record': 200
            },
            {
                'category': category_list[2],
                'record': 188
            }
        ]
    }
]

def get_category_list(request):
    category_query = request.GET.get('category')
    if category_query:
        filtered_categories = [category for category in category_list if category_query.lower() in category['title'].lower()]
        return render(request, 'categories.html', { 'data' : {
            'current_date': date.today(),
            'categories': filtered_categories,
            'category_query': category_query,
            'animal_id': animal_list[0]['id'],
            'animal_cnt': len(animal_list[0]['categories'])
        }})
    else:
        return render(request, 'categories.html', { 'data' : {
            'current_date': date.today(),
            'categories': category_list,
            'animal_id' : animal_list[0]['id'],
            'animal_cnt': len(animal_list[0]['categories'])
        }})

def get_category_detail(request, id):
    category = next((item for item in category_list if item['id'] == int(id)), None)
    if category:
        return render(request, 'category.html', {
            'data': {
                'current_date': date.today(),
                'title': category.get('title'),
                'photo': category.get('photo'),
                'description': category.get('description'),
            }
        })
    else:
        return render(request, 'category.html', {'error_message': 'Category not found'})

def get_animal(request, id):
    for animal in animal_list:
        if animal['id'] == int(id):
            return render(request, 'animal.html', {'animal': animal})
    return render(request, 'error.html', {'message': 'Animal not found'})