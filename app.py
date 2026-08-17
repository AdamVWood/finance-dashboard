from database.database import setup
from app.dashboard import main_menu

setup()
print("Database setup complete")
main_menu()
