from .home import go_home
from .auth import do_login, do_register, logout_user
from .episodes import show_episodes
from .locations import show_locations
from .ranking import show_ranking, create_ranking, delete_ranking
from .api import (
    search_attachables,
    category_items,
    ranking_items,
    character_reviews,
)
from .statistics import statistics_page, statistics_data
from .admin_views import upload_json, create_category



