from django.urls import path
from simpsonsRankApp.views import *
from simpsonsRankApp.views.admin_views import admin_get_category, admin_update_category, admin_toggle_category
from simpsonsRankApp.views.character import show_characters
from simpsonsRankApp.views.reviews import create_location_review, create_character_review, episode_reviews, \
    create_episode_review, location_reviews
from simpsonsRankApp.views.statistics import category_avg_ranking

urlpatterns = [
    path("", do_login, name="do_login"),
    path("home/", go_home, name="home"),
    path('characters/', show_characters, name='characters'),
    path('episodes/', show_episodes, name='episodes'),
    path('locations/', show_locations, name='locations'),
    path('ranking/', show_ranking, name='ranking'),
    path('login/', do_login, name='do_login'),
    path('register/', do_register, name='do_register'),
    path('logout/', logout_user, name='logout_user'),
    path("upload_json/", upload_json, name="upload_json"),
    path("create_category/", create_category, name="create_category"),
    path("rankings/", show_ranking, name="show_ranking"),
    path("rankings/create/", create_ranking, name="create_ranking"),
    path("categories/create/", create_category, name="create_category"),
    path("attachables/search/", search_attachables, name="search_attachables"),
    path("categories/<slug:slug>/items/", category_items, name="category_items"),
    path("ranking-items/<str:ranking_id>/", ranking_items, name="ranking_items"),
    path("character/<int:character_id>/reviews/", character_reviews, name="character_reviews"),
    path("character/<int:character_id>/reviews/create/", create_character_review, name="create_character_review"),
    path("api/episodes/<int:episode_id>/reviews/", episode_reviews, name="episode_reviews"),
    path("api/episodes/<int:episode_id>/reviews/create/", create_episode_review, name="create_episode_review"),
    path("api/locations/<int:location_id>/reviews/", location_reviews, name="location_reviews"),
    path("api/locations/<int:location_id>/reviews/create/", create_location_review, name="create_location_review"),
    path("admin/categories/<slug:slug>/get/", admin_get_category, name="admin_get_category"),
    path("admin/categories/<slug:slug>/update/", admin_update_category, name="admin_update_category"),
    path("admin/categories/<slug:slug>/toggle/", admin_toggle_category, name="admin_toggle_category"),
    path("rankings/<str:ranking_id>/delete/", delete_ranking, name="delete_ranking"),
    path("statistics/", statistics_page, name="statistics_page"),
    path("api/statistics/", statistics_data, name="statistics_data"),
    path("statistics/category-avg/<slug:category_slug>/", category_avg_ranking, name="category_avg_ranking"),





]