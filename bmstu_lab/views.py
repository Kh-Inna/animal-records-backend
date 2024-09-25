from django.shortcuts import render
from datetime import date

category_list =[
    {
        'id': 0,
        'title': 'Самые большие',
        'photo': 'http://127.0.0.1:9000/pic/photo_1.jpg',
        'description': 'К этой категории относятся самые большие по размеру животные своего вида. Например: синий кит, африканский слон, гигансткий кальмар.',
    },
    {
        'id': 1,
        'title': 'Самые быстрые',
        'photo': 'http://127.0.0.1:9000/pic/photo_2.jpeg',
        'description': 'К этой категории относятся самые быстрые по размеру животные своего вида. Например: сапсан, гепард, рыба-парусник.',
    },
    {
        'id': 2,
        'title': 'Самые старые',
        'photo': 'http://127.0.0.1:9000/pic/photo_3.jpg',
        'description': 'К этой категории относятся самые долгоживущие по размеру животные своего вида. Например: гренландский кит, оеанская мидия, гигантская морская черепаха.',
    },
    {
        'id': 3,
        'title': 'Самые громкие',
        'photo': 'http://127.0.0.1:9000/pic/photo_4.jpg',
        'description': 'К этой категории относятся самые громкие по размеру животные своего вида. Например: синий кит, голубой кит, африканский слон.',
    }
]

category_app =[{
        'id': 0,
        'category': [
        {
            'id': 0,
            'title': 'Самые большие',
            'photo': 'http://127.0.0.1:9000/pic/photo_1.jpg',
            'measurement': 'Метров:',
        },
        {
            'id': 2,
            'title': 'Самые старые',
            'photo': 'http://127.0.0.1:9000/pic/photo_3.jpg',
            'measurement': 'Лет:',
        }]},
        {
        'id': 1,
        'category': [
        {
            'id': 0,
            'title': 'Самые большие',
            'photo': 'http://127.0.0.1:9000/pic/photo_1.jpg',
            'measurement': 'Метров:',
        },
        {
            'id': 3,
            'title': 'Самые громкие',
            'photo': 'http://127.0.0.1:9000/pic/photo_4.jpg',
            'measurement': 'дБ:',
        }]}
]

def get_category_list(request):
    category_query = request.GET.get('q')
    if category_query:
        filtered_categories = [category for category in category_list if category_query.lower() in category['title'].lower()]
        return render(request, 'categories.html', { 'data' : {
            'current_date': date.today(),
            'categories': filtered_categories,
            'category_query': category_query,
            'app_id' : category_app[0]['id'],
        }})
    else:
        return render(request, 'categories.html', { 'data' : {
            'current_date': date.today(),
            'categories': category_list,
            'app_id' : category_app[0]['id'],
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

def get_application(request, id):
    for categories in category_app:
        if categories['id'] == id:
            return render(request, 'application.html', {'categories': categories['category']})
    return render(request, 'error.html', {'message': 'Category not found'}) 
