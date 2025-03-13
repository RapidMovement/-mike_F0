import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('quiz_bot.db')

# Создание курсора
cursor = conn.cursor()

# Выполнение SQL-запроса для получения списка таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Таблицы в базе данных:")
for table in tables:
    print(table[0])

# Выполнение SQL-запроса для получения данных из таблицы
cursor.execute("SELECT * FROM quiz_state;")
rows = cursor.fetchall()

# Получение имен столбцов
column_names = [description[0] for description in cursor.description]

print("\nИмена столбцов таблицы 'quiz_state':")
print(column_names)

print("\nСодержимое таблицы 'quiz_state':")
for row in rows:
    print(row)

# Закрытие соединения
conn.close()