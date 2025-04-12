# Task Manager

Task Manager – це веб-додаток для управління завданнями, розроблений на основі Django та Django Rest Framework. Проєкт дозволяє створювати проєкти, додавати завдання, організовувати їх у колонки (To do, In progress, Done) та відслідковувати прогрес у режимі реального часу.

## Технології
- **Python** – основна мова програмування.
- **Django** – фреймворк для серверної частини.
- **Django Rest Framework (DRF)** – для створення REST API.
- **PostgreSQL** – база даних.
- **Django Channels** – для реалізації WebSocket-з'єднань (реальний час).
- **drf-yasg** – для автодокументації API (Swagger UI).
- **django-cors-headers** – для налаштування CORS.

## Встановлення

1. Клонувати репозиторій:
   ```bash
   git clone https://github.com/vladikD/TaskMaster
   cd TaskMaster
   
2. Створити віртуальне середовище та активувати його:  
   ```bash
   python -m venv venv
   source venv/bin/activate  # Для Linux/macOS
   venv\Scripts\activate  # Для Windows

3. Встановити залежності:
   ```bash
   pip install -r requirements.txt

4. Налаштувати файл .env із відповідними налаштуваннями, наприклад, SECRET_KEY, налаштування бази даних тощо.

5. Застосувати міграції:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
6.  Запустити сервер:
python manage.py runserver


## Використання

```markdown
## Використання
- **Адмін-панель:**  
  Перейдіть за адресою `http://127.0.0.1:8000/admin/` та увійдіть з даними суперкористувача.
  
- **API:**  
  Використовуйте URL `/api/` для доступу до API.  
  Документація API доступна за адресою:
  - Swagger UI: `http://127.0.0.1:8000/swagger/`
  - ReDoc: `http://127.0.0.1:8000/redoc/`


## Додаткова інформація
- **WebSocket:**  
  Для реального часу використовується Django Channels. Клієнти підключаються за URL типу `ws://127.0.0.1:8000/ws/projects/<project_id>/`.

- **Логування та відстеження:**  
  Реалізовано логування основних подій для спрощення налагодження.


