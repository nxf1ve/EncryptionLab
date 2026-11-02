"""Графический интерфейс лабораторной работы №3."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from magma import transform_file

# Каждая вкладка содержит разделы: заголовок и пояснение.
HELP_PAGES = {
    'Как пользоваться': [
        ('Шифрование файла',
         '1. Выберите исходный файл.\n'
         '2. Укажите новое имя файла результата.\n'
         '3. Выберите «Шифрование» и способ ввода пароля.\n'
         '4. Введите пароль или выберите файл с паролем.\n'
         '5. Нажмите «Выполнить».'),
        ('Расшифрование файла',
         'Выберите зашифрованный файл, укажите новое имя результата '
         'и переключитесь на «Расшифрование». Используйте тот же пароль, '
         'что и при шифровании. Для документа или изображения сохраните '
         'исходное расширение, например .docx или .png.'),
        ('Два способа ввода пароля',
         'С клавиатуры: текст преобразуется в байты UTF-8.\n\n'
         'Из файла: читаются все байты, включая переводы строк и BOM. '
         'Чтобы пароль совпал с введённым вручную, сохраните текст '
         'в UTF-8 без BOM и без перевода строки в конце.'),
        ('Пример для проверки',
         'Исходный файл: examples/input.bin\n'
         'Пароль: lab3-demo\n'
         'Файл с тем же паролем: examples/password.txt\n\n'
         'Зашифруйте файл, затем расшифруйте его в новый файл. '
         'Хэши SHA-256 исходного и восстановленного файлов должны совпасть.'),
    ],
    'Алгоритм': [
        ('Блочный шифр «Магма»',
         'ГОСТ 34.12-2018\n'
         'Размер блока: 64 бита (8 байт).\n'
         'Размер ключа: 256 бит (32 байта).\n'
         'Количество раундов: 32.\n\n'
         'В раунде выполняются сложение с частью ключа по модулю 2³², '
         'замены через S-box, циклический сдвиг на 11 бит и XOR.'),
        ('Режим CFB — обратная связь по шифртексту',
         'ГОСТ 34.13-2018\n'
         'Сегмент: 64 бита. Регистр: 128 бит.\n\n'
         '1. Зашифровать старшие 8 байт регистра «Магмой»: получится гамма.\n'
         '2. Выполнить XOR входного сегмента с гаммой.\n'
         '3. Сдвинуть регистр и добавить шифртекст справа.\n\n'
         'В обоих направлениях обратная связь использует шифртекст. '
         'Для последнего неполного сегмента берётся нужное количество '
         'байтов гаммы; дополнение не требуется.'),
        ('Ключ и начальное значение',
         'В учебной программе ключ получают как SHA-256 от байтов пароля. '
         'Для каждого шифрования создаётся случайный IV длиной 16 байт. '
         'Он сохраняется в файле и используется при расшифровании.'),
        ('Формат зашифрованного файла',
         'Метка формата — 8 байт.\n'
         'Начальное значение IV — 16 байт.\n'
         'Шифртекст — столько же байт, сколько в исходном файле.\n\n'
         'Общий размер увеличивается на 24 байта.'),
    ],
}

class Application:
    def __init__(self, root):
        self.root = root
        root.title('ЛР №3 — Магма / CFB — Вариант 6')
        root.geometry('850x410')
        root.minsize(780,410)
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text='Магма · Гаммирование с ОС (CFB)', font=('Segoe UI',16,'bold')).grid(row=0,column=0,columnspan=3,pady=10)
        ttk.Label(frame, text='Пыжов Егор · группа ПИбд-42').grid(
            row=1,column=0,columnspan=2,sticky='w',pady=(4,16))
        ttk.Label(frame, text='Вариант 6').grid(row=1,column=2,sticky='e',pady=(4,16))
        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.password = tk.StringVar()
        self.password_file = tk.StringVar()
        self.password_mode = tk.StringVar(value='keyboard')
        self.action = tk.StringVar(value='encrypt')
        for row,label,var in [(3,'Исходный файл',self.source),(4,'Файл результата',self.destination)]:
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=7)
            ttk.Entry(frame,textvariable=var).grid(row=row,column=1,sticky='ew',padx=10)
        ttk.Button(frame,text='Выбрать…',command=self.choose_source).grid(row=3,column=2)
        ttk.Button(frame,text='Сохранить как…',command=self.choose_destination).grid(row=4,column=2)
        modes = ttk.Frame(frame)
        modes.grid(row=5,column=0,columnspan=3,pady=12)
        ttk.Radiobutton(modes,text='Шифрование',variable=self.action,value='encrypt').pack(side='left',padx=15)
        ttk.Radiobutton(modes,text='Расшифрование',variable=self.action,value='decrypt').pack(side='left',padx=15)
        ttk.Radiobutton(frame,text='Пароль с клавиатуры',variable=self.password_mode,value='keyboard').grid(row=6,column=0,sticky='w')
        ttk.Entry(frame,textvariable=self.password,show='*').grid(row=6,column=1,sticky='ew',padx=10)
        ttk.Radiobutton(frame,text='Пароль из файла',variable=self.password_mode,value='file').grid(row=7,column=0,sticky='w',pady=12)
        ttk.Entry(frame,textvariable=self.password_file).grid(row=7,column=1,sticky='ew',padx=10)
        ttk.Button(frame,text='Выбрать…',command=self.choose_password).grid(row=7,column=2)
        frame.rowconfigure(8, weight=1)
        ttk.Separator(frame).grid(row=9,column=0,columnspan=3,sticky='ew',pady=(12,12))
        buttons = ttk.Frame(frame)
        buttons.grid(row=10,column=0,columnspan=3,sticky='e')
        ttk.Button(buttons,text='Справка и описание алгоритма',
                   command=self.show_help).pack(side='left',padx=(0,12))
        self.run_button = ttk.Button(buttons,text='Выполнить',width=16,command=self.start)
        self.run_button.pack(side='left')

    def show_help(self):
        """Отдельное окно с вкладками и прокручиваемым текстом."""
        if hasattr(self, 'help_window') and self.help_window.winfo_exists():
            self.help_window.lift()
            self.help_window.focus_set()
            return
        window = tk.Toplevel(self.root)
        self.help_window = window
        window.title('Справка — Магма / CFB')
        window.geometry('740x610')
        window.minsize(580,440)
        window.transient(self.root)
        frame = ttk.Frame(window, padding=18)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Справка по программе',
                  font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(frame, text='ЛР №3 · Магма / CFB · Вариант 6',
                  font=('Segoe UI',10)).pack(anchor='w',pady=(4,16))
        notebook = ttk.Notebook(frame)
        notebook.pack(fill='both',expand=True)
        for title, sections in HELP_PAGES.items():
            tab = ttk.Frame(notebook, padding=1)
            notebook.add(tab, text=title)
            text = ScrolledText(tab, wrap='word', font=('Segoe UI',11),
                                background='white', foreground='#263238',
                                relief='flat', borderwidth=0, padx=18, pady=16,
                                spacing1=2, spacing3=8, cursor='arrow')
            text.pack(fill='both',expand=True)
            text.tag_configure('heading',font=('Segoe UI',12,'bold'),
                               foreground='#224B68',spacing1=12,spacing3=6)
            for heading, body in sections:
                text.insert('end', heading + '\n', 'heading')
                text.insert('end', body + '\n\n')
            text.configure(state='disabled')
        ttk.Button(frame, text='Закрыть', width=14,
                   command=window.destroy).pack(anchor='e',pady=(14,0))
        window.bind('<Escape>', lambda event: window.destroy())

    def choose_source(self):
        value = filedialog.askopenfilename()
        if value: self.source.set(value)

    def choose_destination(self):
        value = filedialog.asksaveasfilename()
        if value: self.destination.set(value)

    def choose_password(self):
        value = filedialog.askopenfilename(title='Файл с паролем')
        if value: self.password_file.set(value)

    def start(self):
        """Простой последовательный обработчик кнопки."""
        try:
            if not self.source.get() or not self.destination.get():
                raise ValueError('Выберите исходный файл и файл результата')
            if self.password_mode.get() == 'file':
                password = Path(self.password_file.get()).read_bytes()
            else:
                password = self.password.get().encode('utf-8')

            decrypt = self.action.get() == 'decrypt'
            transform_file(self.source.get(), self.destination.get(), password, decrypt)
            messagebox.showinfo('Готово', 'Файл сохранён')
        except (OSError, ValueError) as error:
            messagebox.showerror('Ошибка', str(error))

if __name__ == '__main__':
    root = tk.Tk()
    Application(root)
    root.mainloop()
