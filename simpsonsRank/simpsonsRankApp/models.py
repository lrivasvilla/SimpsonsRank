from django.contrib.auth.models import AbstractBaseUser, BaseUserManager,PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


# Create your models here.

#pyhton manage.py make migrations --> PREPARA SQL SCRIPT
#python manage.py migrate --> SCRIPT --> BBDD

#SQLITE MODELS
class UserManager(BaseUserManager):
    def create_user(self, mail, username, password=None, role='cliente'):
        if not mail or not username:
            raise ValueError("Debes rellenar mail y username")

        mail = self.normalize_email(mail)
        user = self.model(mail=mail, username=username, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mail, username, password=None):
        user = self.create_user(mail, username, password=password, role='admin')
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLES = (
        ('admin', 'Administrador'),
        ('cliente', 'Cliente'),
    )

    mail = models.EmailField(unique=True)
    username = models.CharField(max_length=100, unique=True)
    role = models.CharField(max_length=20, choices=ROLES, default='cliente')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['mail']  # role fuera

    def __str__(self):
        return self.username

#MONGODB MODELS
class Character(models.Model):

    name = models.CharField(max_length=150)
    gender = models.CharField(max_length=150)
    age = models.IntegerField()
    birthdate = models.CharField(max_length=150)
    status = models.CharField(max_length=150)
    occupation = models.CharField(max_length=150)
    portrait_path = models.CharField(max_length=350)
    phrases = models.JSONField(null=True, blank=True, default=list)
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'characters'
        managed = False

    def __str__(self):
        return self.name

class Episodes(models.Model):

    episode_number = models.IntegerField()
    airdate = models.CharField()
    season = models.IntegerField()
    name = models.CharField(max_length=150)
    image_path = models.CharField(max_length=350)
    synopsis = models.TextField()

    class Meta:
        db_table = 'episodes'
        managed = False

    def __str__(self):
        return self.name


class Locations(models.Model):

    name = models.CharField(max_length=150)
    image_path = models.CharField(max_length=350)
    town = models.TextField(max_length=150)
    use = models.CharField(max_length=150)

    class Meta:
        db_table = 'locations'
        managed = False

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    characters = models.ManyToManyField("Character", blank=True, related_name="categories")
    locations = models.ManyToManyField("Locations", blank=True, related_name="categories")
    episodes = models.ManyToManyField("Episodes", blank=True, related_name="categories")

    def __str__(self):
        return self.name

class Review(models.Model):
   user = models.CharField(max_length=150)
   characterCode = models.IntegerField(null=False)
   reviewDate = models.DateField(default=timezone.now)
   rating = models.PositiveIntegerField(null=False,  validators=[MinValueValidator(1), MaxValueValidator(5)])
   comments = models.TextField()

   def __str__(self):
       return self.user + " " + str(self.rating)

   class Meta:
       db_table = 'reviews'
       managed = False


# models.py
class Ranking(models.Model):
    user = models.CharField(max_length=150)

    # ESTE CAMPO
    categoryCode = models.CharField(max_length=120)
    title = models.CharField(max_length=120, default="")

    rankinList = models.JSONField(default=list)
    rankinDate = models.DateField()

    class Meta:
        db_table = "rankings"
        managed = False

