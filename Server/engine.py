import dotenv
import os

from supabase import create_client, Client


dotenv.load_dotenv()


# Данные для подключения (получить в настройках Supabase)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_PRIVATE_KEY")

# Создание клиента
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Проверка подключения
try:
    response = supabase.table('User').select("*").limit(1).execute()
    print("✅ Подключение успешно!")
except Exception as e:
    print(f"❌ Ошибка подключения: {e}")