from django.shortcuts import render

from simpsonsRankApp.models import *
def show_characters(request):
    list_characters = Character.objects.all()
    return render(request, 'characters.html', {"list": list_characters})




