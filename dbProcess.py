from os import path
import sqlite3
import shutil

f = open('user_files/db_config.txt', 'r')
id_reminder = int(f.read())
f.close()


def connect_to_db():
    """ Подключение базы данных. """

    global db, sql

    db = sqlite3.connect('user_files/nk.db', check_same_thread=False)
    sql = db.cursor()

    sql.execute("""CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        status INTEGER,
        toUserId TEXT,
        textContent TEXT,
        documentContent TEXT,
        videoContent TEXT,
        photoContent TEXT,
        audioContent TEXT,
        date TEXT
    )""")

    db.commit()

    return (db, sql)


def save_remind(toUser):
    """ Функция сохраняет данные в базу данных. Данные берутся из файла temp.txt, который хранится в отдельной директории каждого пользователя """
    
    global sql, db

    access = False

    if path.isfile('temp_files/' + str(toUser) + '/temp.txt'):
        temp_data = open('temp_files/' + str(toUser) + '/temp.txt', 'r', encoding='utf-8')
        data_to_db = temp_data.readlines()
        temp_data.close()

        text_cont = ''
        document_cont = []
        photo_cont = []
        video_cont = []
        audio_cont = []
        user_cont = None
        date_cont = None

        for elem in data_to_db:
            if elem[0:4:] == 'text':
                text_cont += (elem[6:-1:] + '\n')
            elif elem[0:4:] == 'docu':
                document_cont.append(elem[6:-1:])
            elif elem[0:4:] == 'phot':
                photo_cont.append(elem[6:-1:])
            elif elem[0:4:] == 'vide':
                video_cont.append(elem[6:-1:])
            elif elem[0:4:] == 'audi':
                audio_cont.append(elem[6:-1:])
            elif elem[0:4:] == 'user':
                user_cont = elem[6:-1:]
            elif elem[0:4:] == 'date':
                date_cont = elem[6::]

        try:
            sql.execute(f"INSERT INTO reminders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (id_reminder, str(1), str(user_cont), str(text_cont), str(document_cont)[1:-1:], str(video_cont)[1:-1:], str(photo_cont)[1:-1:], str(audio_cont)[1:-1:], str(date_cont)))
            db.commit()
            access = True
            mess_content = 'Отлично! Напоминание сохранено!'
        except:
            connect_to_db()
            try:
                sql.execute(f"INSERT INTO reminders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (id_reminder, str(1), str(user_cont), str(text_cont), str(document_cont)[1:-1:], str(video_cont)[1:-1:], str(photo_cont)[1:-1:], str(audio_cont)[1:-1:], str(date_cont)))
                db.commit()
                access = True
                mess_content = 'Отлично! Напоминание сохранено!'
            except:
                mess_content = 'Ошибка! Проблемы на сервере... Попробуйте позже.'

        if path.isdir('temp_files/' + str(toUser)):
            shutil.rmtree('temp_files/' + str(toUser), ignore_errors=True)

        return (access, mess_content)
    
    else:
        return (access, 'ERROR: File not found')


def del_remind(id):
    """ Функция удаляет напоминание из базы данных. Поиск записи происходит по передаваемому аргументу id. """

    global sql, db

    try:
        data = sql.execute("SELECT * FROM reminders WHERE id = (?)", (str(id))).fetchall()[0]
        toUser = data[2]

        if path.isdir('user_files/' + str(toUser) + '/' + str(id)):
            shutil.rmtree('user_files/' + str(toUser) + '/' + str(id), ignore_errors=True)    

        sql.execute("DELETE FROM reminders WHERE id = (?)", str(id))
        db.commit()
        return True
        
    except:
        connect_to_db()
        
    try:    
        del_remind(id)
        return True
    except:
        return False
