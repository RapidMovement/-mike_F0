import aiosqlite

# Имя базы данных
DB_NAME = 'quiz_bot.db'

async def get_quiz_index(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = ?', (user_id, )) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0

async def update_quiz_index(user_id, index):
    async with aiosqlite.connect(DB_NAME) as db:
        # INSERT OR IGNORE для предотвращения сброса значений других столбцов
        await db.execute('INSERT OR IGNORE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
        await db.execute('UPDATE quiz_state SET question_index = ? WHERE user_id = ?', (index, user_id))
        await db.commit()

async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS quiz_state (
                user_id INTEGER PRIMARY KEY,
                question_index INTEGER,
                correct_answers INTEGER DEFAULT 0
            )
        ''')
        await db.commit()

async def increment_correct_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            UPDATE quiz_state
            SET correct_answers = correct_answers + 1
            WHERE user_id = ?
        ''', (user_id,))
        await db.commit()

async def get_correct_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT correct_answers FROM quiz_state WHERE user_id = ?', (user_id, )) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0

async def reset_correct_answers(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        # Обновляем значение correct_answers на 0 для указанного user_id
        await db.execute('UPDATE quiz_state SET correct_answers = 0 WHERE user_id = ?', (user_id,))
        await db.commit()