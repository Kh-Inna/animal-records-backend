from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    title = models.CharField(max_length=255)
    photo = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    measurement = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'category'

class Animal(models.Model):
    class RequestStatus(models.TextChoices):
        DRAFT = "DRAFT"
        DELETED = "DELETED"
        FORMED = "FORMED"
        COMPLETED = "COMPLETED"
        REJECTED = "REJECTED"

    status = models.CharField(
        max_length=10,
        choices=RequestStatus.choices,
        default=RequestStatus.DRAFT,
    )
    animal = models.CharField(max_length=255)
    period = models.CharField(max_length=255, blank=True, null=True)
    habitat = models.CharField(max_length=255, blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    formation_date = models.DateTimeField(blank=True, null=True)
    completion_date = models.DateTimeField(blank=True, null=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='animals_created')
    moderator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='animals_moderated', blank=True, null=True)
    record_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'animal'

class AnimalCategory(models.Model):
    animal = models.ForeignKey(Animal, models.DO_NOTHING, blank=True, null=True)
    category = models.ForeignKey('Category', models.DO_NOTHING, blank=True, null=True)
    record = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'animal_category'
        unique_together = (('animal', 'category'),)
