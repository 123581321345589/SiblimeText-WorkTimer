import sublime
import sublime_plugin
import time
import json
import fileinput
import os

global WT

WT = None

class WorkTimer:

	sep          = '\\' if sublime.platform() == 'Windows' else '/'
	package_name = 'WorkTimer'

	data         = None
	data_file    = 'Data.json'
	data_path    = None

	project      = None
	project_name = None

	show_time_s  = None
	show_time_d  = None

	# Подготавливает данные для работы скрипта
	def __init__(self):

		# Сформировать путь к файлу данных
		self.data_path = sublime.packages_path() + self.sep + self.package_name + self.sep + self.data_file

		# Получить название проекта в фокусе
		current_project_name = sublime.active_window().extract_variables().get('project_base_name')

		# Остановиться если нет проекта
		if current_project_name is None:
			return

		# Определить, нужно ли показывать дни в строке состояния
		self.show_time_d = self.get_setting('show_time_d')

		# Определить, нужно ли показывать секунды в строке состояния
		self.show_time_s = self.get_setting('show_time_s')

		# Запомнить название проекта название проекта
		self.project_name = current_project_name

		# Прочитать данные проекта
		self.read_project_data()

		# Указать точку отсчета
		self.project['start'] = int(time.time())

		# Записать данные в файл
		self.save_data()

		# Показать информацию в строке состояния
		self.show()

	# Возвращает текущий view (файл с фокусом)
	def get_view(self):
		return sublime.active_window().active_view()

	# Возвращает настройки из файла (значение указанного ключа)
	def get_setting(self, name):

		settings = self.get_view().settings().get(self.package_name)

		if settings is None:
			settings = sublime.load_settings(self.package_name + '.sublime-settings')

		return settings.get(name)

	# Сохраняет затраченное на данный момент время
	def save(self):

		# Получить текущее время
		curr_time = int(time.time())

		# Подсчитать затраченное время
		self.project['total'] += (curr_time - self.project['start'])

		# Обновить точку начала отсчета
		self.project['start'] = curr_time

		# Записать данные в файл
		self.save_data()

	# Получает данные о всех проектах из файла данных
	def read_data(self):

		# Остановить метод, если данные уже в памяти
		if self.data is not None:
			return

		# Прочитать файл данных
		try:
			file = open(self.data_path, 'r', encoding='utf-8')

		# Создать файл если не существует
		except IOError as e:
			self.data = {}
			file = open(self.data_path, 'w')
			file.write(json.dumps(self.data, indent=4, sort_keys=True))
			file.close()

		# Запомнить данные из файла
		else:
			self.data = json.load(file)
			file.close()

	# Записывает данные в файл
	def save_data(self):

		# Объединить данные текущего проекта с данными всех проектов
		self.data[self.project_name] = self.project

		# Записать данные в файл
		file = open(self.data_path, 'w')
		file.write(json.dumps(self.data, indent=4, sort_keys=True))
		file.close()

	# Получает данные о конкретном проекте
	def read_project_data(self):

		# Остановить метод, если данные уже в памяти
		if self.project is not None:
			return

		# Прочитать данные о всех проектах
		self.read_data()

		# Получить данные проекта
		try:
			self.project = self.data[self.project_name]

		# Создать данные проект если их не существует
		except Exception as e:
			self.project = {
				'start': 0,
				'total': 0
			}
			self.data[self.project_name] = self.project
			file = open(self.data_path, 'w')
			file.write(json.dumps(self.data, indent=4, sort_keys=True))
			file.close()

	# Показывает информацию в строке состояния
	def show(self):
		self.get_view().set_status('wt_time', self.get_time_show())

	# Показывает информацию в строке состояния
	def hide(self):
		self.get_view().erase_status('wt_time')

	# Переводит секунды в минуты, часы, дни
	def get_time_show(self, sec=False):

		# Если НЕ получено значене - рассчитать из текущего проекта
		if sec == False:
			sec = int(time.time()) - self.project['start'] + self.project['total']

		# Переменная для возврата
		r = ''

		# Вычислить глобальные суммы
		sum_s = sec
		sum_m = sum_s // 60 if sum_s >= 60 else 0
		sum_h = sum_m // 60 if sum_m >= 60 else 0
		sum_d = sum_h // 24 if sum_h >= 24 else 0

		# Вычислить корректные суммы
		cor_s = sum_s % 60 if sum_s > 0 else 0
		cor_m = sum_m % 60 if sum_m > 0 else 0
		cor_h = sum_h % 24 if sum_h > 0 else 0

		r += self.get_setting('show_time_before')

		# Дни только если разрешено в настройках
		if self.show_time_d:
			r += str(sum_d) + self.get_setting('show_time_after_d') if sum_d > 0 else ''

		# Часы (в зависимости от настроек дней)
		if self.show_time_d:
			r += str(cor_h) + self.get_setting('show_time_after_h') if cor_h > 0 else ''
		else:
			r += str(sum_h) + self.get_setting('show_time_after_h') if sum_h > 0 else ''

		# Минуты
		r += str(cor_m) + self.get_setting('show_time_after_m') if cor_m > 0 else ''

		# Секунды только если разрешено в настройках
		if self.show_time_s:
			r += str(cor_s) + self.get_setting('show_time_after_s')

		# Вернуть результат
		return r

# Обработка событий
class WorkTimerListener(sublime_plugin.ViewEventListener):

	# При фокусе в открытый файл
	def on_activated_async(self):

		global WT

		# Получить имя проекта
		current_project_name = sublime.active_window().extract_variables().get('project_base_name')

		# Если открыт редактор БЕЗ проекта
		if current_project_name is None:

			# Если в памяти есть запущеный скрипт
			if isinstance(WT, WorkTimer):

				# Сохранить его
				WT.save()

				# И закрыть
				WT = None

		# Если в фокусе есть проект и есть скрипт в памяти
		elif isinstance(WT, WorkTimer):

			# Сохранить время, затраченное на проект (скрипт которого еще в памяти)
			WT.save()

			# Если фокус в новом проекте
			if current_project_name != WT.project_name:

				# Запустить новый скрпит
				WT = WorkTimer()

			# Если фокус в текущем проекте
			else:

				# Показать информацию в строке состояния
				WT.show()

		# Если в фокусе есть проект НО в памяти еще нет скрипта
		else:

			# Запустить скрпит
			WT = WorkTimer()

	# При сохранении
	def on_pre_save(self):

		global WT

		# Если скрипт уже запущен
		if isinstance(WT, WorkTimer):

			# Сохранить время, затраченное на предыдущий проект
			WT.save()

# Удаляет файла данных
class WorkTimerClearAllProjectsCommand(sublime_plugin.WindowCommand):
	def run(self):

		global WT

		# Если скрипт уже запущен
		if isinstance(WT, WorkTimer):

			# Удалить файл данных
			os.remove(WT.data_path)

			# Скрыть информацию из строки состояния
			WT.hide()

			# Сбросить запущеный скрипт
			WT = None

# Выводит на экран статистику по всем проектам
class WorkTimerStatAllProjectsCommand(sublime_plugin.WindowCommand):
	def run(self):

		# Получить данные
		tmp = WorkTimer()
		tmp.read_data()

		# Заголовок
		res = tmp.package_name

		# Сформировать результат
		for name in tmp.data:
			res += '\n\n'
			res += name
			res += '\n'
			res += tmp.get_time_show(int(tmp.data[name]['total']))

		# Создать новый файл
		view = sublime.active_window().new_file()

		# Вывести результат
		view.run_command('insert', { 'characters': res })

# Открывает файл данных
class WorkTimerEditAllProjectsCommand(sublime_plugin.WindowCommand):
	def run(self):

		# Получить данные
		tmp = WorkTimer()

		# Открыть файл данных
		sublime.active_window().open_file(tmp.data_path)
