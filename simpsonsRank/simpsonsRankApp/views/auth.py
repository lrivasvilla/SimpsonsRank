from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from simpsonsRankApp.forms import LoginForm, RegisterForm


def do_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # o el name correcto
    else:
        form = LoginForm()

    return render(request, 'login.html', {"form": form})


def do_register(request):
    if request.method == 'POST':
        dataform = RegisterForm(request.POST)
        dataformLogin = LoginForm(request.POST)

        if dataform.is_valid():
            user = dataform.save(commit=False)
            user.set_password(dataform.cleaned_data['password'])

            # si marca el checkbox, lo hacemos admin real
            if request.POST.get("is_admin") == "on":
                user.role = "admin"
                user.is_staff = True
                user.is_superuser = True
            else:
                user.role = "cliente"
                user.is_staff = False
                user.is_superuser = False

            user.save()
            return redirect('do_login')

        return render(request, 'register.html', {"form": dataformLogin})

    form = RegisterForm()
    return render(request, 'register.html', {"form": form})


def logout_user(request):
    logout(request)
    return redirect('do_login')