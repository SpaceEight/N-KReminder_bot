import telebot
from os import mkdir, path
import shutil
from time import sleep
import datetime
import sqlite3

from dbProcess import connect_to_db, save_remind, del_remind


f = open('user_files/db_config.txt', 'r')
id_reminder = int(f.read())
f.close()

""" переменные отвечают за подключение и работу с базой данных """
db, sql = connect_to_db()


bot = telebot.TeleBot('5914851349:AAHR2ScVHWdOjLpmVGHF3SNM3uQ2zBb0S3s')

""" В check хранятся пользователи, которые уже запустили бота. В словаре status хранятся статусы 
    пользователей (статус - этап действия, который выполняется для пользователя) """
check = set()
status = {}
delete_fromtable_when_editing = None


def start_reminder(id, date):
    """ 
    Функция вызывается для отправки напоминания и замораживается на такое количество
    секунд t, что для current_time + t = указанная дата напоминания.
    Параметры: id - номер записи в базе данных, data - дата и время напоминания.
    Переменные: time_until_remind - хранит время от текущего до времени напоминания в секундах, data_for_send - данные напоминания из бд, 
        toUserId - id telegram_user.
    """

    global sql, db

    time_until_remind = (date - datetime.datetime.now()).total_seconds()

    try:
        sleep(time_until_remind)

        data_for_send = sql.execute("SELECT * FROM reminders WHERE id = (?)", str(id)).fetchall()[0]

        toUserId = int(data_for_send[2])
        
        if data_for_send[1] == 1:

            date_after_sleep = data_for_send[-1].split(" ")
            year = int(date_after_sleep[0])
            month = int(date_after_sleep[1])
            day = int(date_after_sleep[2])
            hour = int(date_after_sleep[3])
            minute = int(date_after_sleep[4])
            date_after_sleep = datetime.datetime(year, month, day, hour, minute)

            if date_after_sleep == date:
                send_remind(id)

                keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
                keyboard.row('/help', '/add', '/edit')
                bot.send_message(toUserId, 'Отправил вам все, что вы просили!', reply_markup=keyboard)

        del_remind(str(id))
    
    except:
        bot.send_message(toUserId, 'Это время уже наступило!', reply_markup=telebot.types.ReplyKeyboardRemove())


def send_remind(id):
    """
    Функция отправляет напоминание пользователю. Вызывается в функции start_reminder, принимает 
    Параметры: id записи в базе данных, данные из которой нужно отправить.
    Переменные: data_for_send - данные из базы данных для напоминания, toUserId - id пользователя telegram.
    В функции из базы данных считываются: текстовые сообщения и пути файлов. Затем это все отправляется пользователю.
    """

    global sql, db
    try:
        data_for_send = sql.execute("SELECT * FROM reminders WHERE id = (?)", str(id)).fetchall()[0]

        toUserId = int(data_for_send[2])

        try:
            text_send = data_for_send[3]
            if text_send != '':
                for i in text_send.split(", "):
                    bot.send_message(toUserId, i[:-1:])
        except:
            pass

        try:
            document_send = data_for_send[4]
            if document_send != '':
                for i in document_send.split(", "):
                    with open(i[1:-1:], 'rb') as fileTo:
                        bot.send_document(toUserId, fileTo)
        except:
            pass

        try:
            video_send = data_for_send[5]
            if video_send != '':
                for i in video_send.split(", "):
                    with open(i[1:-1:], 'rb') as fileTo:
                        bot.send_video(toUserId, fileTo)
        except:
            pass

        try:
            photo_send = data_for_send[6]
            if photo_send != '':
                for i in photo_send.split(", "):
                    with open(i[1:-1:], 'rb') as fileTo:
                        bot.send_photo(toUserId, fileTo)
        except:
            pass

        try:
            audio_send = data_for_send[7]
            if audio_send != '':
                for i in audio_send.split(", "):
                    with open(i[1:-1:], 'rb') as fileTo:
                        bot.send_audio(toUserId, fileTo)
        except:
            pass
    
    except:
        connect_to_db()
        send_remind(id)



@bot.message_handler(commands=['start'])
def start(message):
    """ 
    Функция, отвечающая за старт. Отслеживает отправку пользователем такой команды, как /start. 
    Возвращает пользователю сообщение с приветствием и создает начальную клавиатуру (клавиатуру главного экрана). 
    """

    global check, status

    keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
    keyboard.row('/help', '/add', '/edit')

    if message.from_user.id in check:
        end_of_line = ' Продолжим!'
    else:
        end_of_line = ''
        check.add(message.from_user.id)
    
    mess_content = f'Приветствую вас, {message.from_user.first_name} {message.from_user.last_name}!' + end_of_line

    bot.send_message(message.chat.id, mess_content, reply_markup=keyboard)


@bot.message_handler(commands=['help'])
def help(message):
    """ 
    Функция отправляет пользователю инструкцию по использованию бота, устанавливет клавиатуру с функциями по работе с напоминаниями.
    """

    global check, status

    if message.from_user.id in check:
        status[str(message.from_user.id)] = 'help'

        keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
        keyboard.row('/add', '/edit')

        mess_content = f'{message.from_user.first_name}, чтобы создать напоминание, нажмите /add.\n Для просмотра или удаления нажмите /edit.'
        
        bot.send_message(message.chat.id, mess_content, reply_markup=keyboard)


@bot.message_handler(commands=['add'])
def add(message):
    """ 
    Функция добавления напоминания. При вызове запускает процесс создания напоминания, а также создает необходимые директории.
    Переменные: temp_files_src - путь к temp файлу пользователя.
    """

    global check, status

    if message.from_user.id in check:
        status[str(message.from_user.id)] = 'add_1'

        temp_files_src = 'temp_files/' + str(message.from_user.id)
        if not path.isdir(temp_files_src):
            mkdir(temp_files_src)
        else:
            shutil.rmtree(temp_files_src, ignore_errors=True)
            mkdir(temp_files_src)

        user_files_src = 'user_files/' + str(message.from_user.id)
        if not path.isdir(user_files_src):
            mkdir(user_files_src)

        keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
        keyboard.row('Продолжить')

        mess_content = 'Введите текст напоминания. Вы также можете отправить фотографии, музыку и документы. Когда отправите все, что вам нужно, нажмите кнопку "Продолжить.'
            
        bot.send_message(message.chat.id, mess_content, reply_markup=keyboard)


@bot.message_handler(commands=['edit'])
def edit(message):
    """ 
    Функция позволяет пользователю просмотреть свои созданные напоминания и удалить какие-то из них при необходимости. 
    Переменные: data_for_send - данные для всех напоминаний, которые принадлежат пользователю.
    """

    global check, status, sql, db

    if message.from_user.id in check:
        status[str(message.from_user.id)] = 'edit'
        toUserId = str(message.from_user.id)
        data_for_send = sql.execute("SELECT * FROM reminders WHERE toUserId = (?) and status = 1", (toUserId,)).fetchall()

        if data_for_send == []:
            bot.send_message(message.chat.id, 'У вас нет сохраненных напоминаний. Создайте их с помощью /add !')
        
        else:
            keyboard = telebot.types.InlineKeyboardMarkup()
            phrase = 'Напоминание на '
            for rem in data_for_send:
                date = rem[-1].split(" ")
                date = datetime.datetime(int(date[0]), int(date[1]), int(date[2]), int(date[3]), int(date[4]))
                inf_for_sent = str(message.from_user.id) + '|' + str(rem[0])
                button = telebot.types.InlineKeyboardButton(text=phrase+str(date), callback_data=inf_for_sent)
                keyboard.add(button)

            bot.send_message(message.chat.id, 'Выберите напоминание, чтобы посмотреть содержимое:', reply_markup=keyboard)


CONTENT_TYPES = ["text", "audio", "document", "photo", "sticker", "video", "video_note", "voice", "location", "contact",
                 "new_chat_members", "left_chat_member", "new_chat_title", "new_chat_photo", "delete_chat_photo",
                 "group_chat_created", "supergroup_chat_created", "channel_chat_created", "migrate_to_chat_id",
                 "migrate_from_chat_id", "pinned_message"]

@bot.message_handler(content_types=CONTENT_TYPES)
def get_text(message):
    """ 
    Функция анализирует контент сообщения пользователя и обрабатывает в зависимости от значения и ситуации. Ситуации указываются в status с ключом
        в виде id пользователя, а значением в названии действия.
    """

    global check, status, id_reminder, delete_fromtable_when_editing, sql, db

    if message.from_user.id in check:
        if (str(message.from_user.id) not in status) or (status[str(message.from_user.id)] == 'help'):
            keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
            keyboard.row('/help', '/add', '/edit')

            mess_content = f'{message.from_user.first_name}, выберите что-то из списка команд.'
            
            bot.send_message(message.chat.id, mess_content, reply_markup=keyboard)

        elif (status[str(message.from_user.id)] == 'edit'):
            if message.text == 'Удалить':
                data_id = delete_fromtable_when_editing     
                if data_id != (None):
                    sql.execute("UPDATE reminders SET status = 0 WHERE id = (?)", str(data_id))
                    db.commit()

                    keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
                    keyboard.row('/help', '/add', '/edit')

                    status[str(message.from_user.id)] == ''

                    bot.send_message(message.chat.id, 'Напоминание удалено! Можете выбрать, что вы хотите сделать.', reply_markup=keyboard)

            elif message.text == 'Вернуться':
                status[str(message.from_user.id)] == ''

                keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
                keyboard.row('/help', '/add', '/edit')
                
                bot.send_message(message.chat.id, 'Выберите команду.', reply_markup=keyboard)
            
            else:
                keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
                keyboard.row('/help', '/add')

                mess_content = f'{message.from_user.first_name}, выберите сообщение, которое хотите изменить или что-то из списка команд.'
                
                bot.send_message(message.chat.id, mess_content, reply_markup=keyboard)

        elif (status[str(message.from_user.id)] == 'add_1'):
            if (message.text == 'Продолжить'):
                status[str(message.from_user.id)] = 'add_2'

                mess_content = 'Укажите дату и время, когда нужно отправить напоминание. Формат: часы:минуты.день.месяц.год (14:30.01.01.2022).'
                bot.send_message(message.chat.id, mess_content, reply_markup=telebot.types.ReplyKeyboardRemove())

            else:
                temp_files_src = 'temp_files/' + str(message.from_user.id)
                user_files_src = 'user_files/' + str(message.from_user.id) + '/' + str(id_reminder)

                if not path.isfile(temp_files_src + '/temp.txt'):
                    temp_data = open(temp_files_src + '/temp.txt', 'w', encoding='utf-8')
                else:
                    temp_data = open(temp_files_src + '/temp.txt', 'a', encoding='utf-8')


                if (message.content_type == 'text'):
                    temp_data.write('text: ' + message.text + '\n')

                elif (message.content_type in ["audio", "document", "photo", "video"]):
                    if not path.isdir(user_files_src.replace('/' + str(id_reminder), '')):
                        mkdir(user_files_src.replace('/' + str(id_reminder), ''))
                    if not path.isdir(user_files_src):
                        mkdir(user_files_src)

                    # Checking and processing a specific file type
                    if (message.content_type == 'document'):
                        file_info = bot.get_file(message.document.file_id)
                        downloaded_file = bot.download_file(file_info.file_path)

                        src = user_files_src + '/' + message.document.file_name
                        with open(src, 'wb') as new_file:
                            new_file.write(downloaded_file)

                        temp_data.write('docu: ' + src + '\n')

                    elif (message.content_type == 'photo'):
                        file_info = bot.get_file(message.photo[len(message.photo)-1].file_id)
                        downloaded_file = bot.download_file(file_info.file_path)

                        src = user_files_src + '/' + str(file_info.file_path)[7::]
                        with open(src, 'wb') as new_file:
                            new_file.write(downloaded_file)

                        temp_data.write('phot: ' + src + '\n')

                    elif (message.content_type == 'video'):
                        file_info = bot.get_file(message.video.file_id)
                        downloaded_file = bot.download_file(file_info.file_path)

                        src = user_files_src + '/' + str(file_info.file_path)[7::]
                        with open(src, 'wb') as new_file:
                            new_file.write(downloaded_file)

                        temp_data.write('vide: ' + src + '\n')

                    elif (message.content_type == 'audio'):
                        file_info = bot.get_file(message.audio.file_id)
                        downloaded_file = bot.download_file(file_info.file_path)

                        src = user_files_src + '/' + str(file_info.file_path)[6::]
                        with open(src, 'wb') as new_file:
                            new_file.write(downloaded_file)

                        temp_data.write('audi: ' + src + '\n')
                
                else:
                    bot.send_message(message.chat.id, 'Пока я не умею работать с этим типом файлов((')
                    
                temp_data.close()

        elif (status[str(message.from_user.id)] == 'add_2'):
            access = False
            error = False
            try:
                data = message.text.split('.')
            except:
                data = None

            keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
            keyboard.row('/help', '/add', '/edit')

            try:
                year = int(data[3])
                month = int(data[2])
                day = int(data[1])
                hour = int(data[0].split(':')[0])
                minute = int(data[0].split(':')[1])
            except:
                error = True

            if not(error):
                try:
                    full_date = datetime.datetime(year, month, day, hour, minute)
                    if full_date > datetime.datetime.now():

                        temp_data = open('temp_files/' + str(message.from_user.id) + '/temp.txt', 'a', encoding='utf-8')
                        temp_data.write('user: ' + str(message.from_user.id) + '\n')
                        temp_data.write('date: ' + str(year) + ' ' + str(month) + ' ' + str(day) + ' ' + str(hour) + ' ' + str(minute))
                        temp_data.close()

                        result = save_remind(message.from_user.id)
                        access = result[0]
                        mess_content = result[1]

                        del status[str(message.from_user.id)]
                    else:
                        mess_content = 'Эта дата уже прошла. Пожалуйста, укажите дату снова. Формат: часы:минуты.день.месяц.год (14:30.01.01.2022).'
                        keyboard = None
                except:
                    mess_content = 'Такой даты не существует! Перепроверьте дату и введите еще раз. Формат: часы:минуты.день.месяц.год (14:30.01.01.2022).'
                    keyboard = None
            else:
                mess_content = 'Неверный формат даты! Возможно, вы перепутали какие-то символы. Перепроверьте дату и введите еще раз. Формат: часы:минуты.день.месяц.год (14:30.01.01.2022).'
                keyboard = None
            
            bot.send_message(message.chat.id, mess_content,reply_markup=keyboard)
            if access:
                id_reminder += 1
                f = open('user_files/db_config.txt', 'w')
                f.write(str(id_reminder))
                f.close()
                start_reminder(id_reminder-1, full_date)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    """
    Функция обрабатывает нажатия на inlinekeyboard во время редактирования напоминаний.
    Переменные: toUserId - id пользователя, который отправляет запрос на изменение напоминания, data_id - id записи напоминания в базе данных.
    """
    global check, status, sql, db

    toUserId = int(call.data.split("|")[0])
    data_id = str(call.data.split("|")[1])

    keyboard = telebot.types.ReplyKeyboardMarkup(True, False)
    keyboard.row('Удалить', 'Вернуться')

    if toUserId in check:
        if status[str(toUserId)] == 'edit':
            send_remind(data_id)

            global delete_fromtable_when_editing
            delete_fromtable_when_editing = data_id

            bot.send_message(toUserId, 'Выберите, что вы хотите сделать.', reply_markup=keyboard)
                   

bot.polling(none_stop=True)