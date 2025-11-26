import customtkinter as ctk
from datetime import datetime
import json
import os
from dataclasses import dataclass, asdict
import calendar

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Путь к файлу данных
DATA_FILE = "subscriptions.json"


@dataclass
class Subscription:
    """Класс подписки"""
    id: int
    name: str
    price: float
    billing_day: int  # День месяца для списания
    category: str
    color: str
    icon: str

    def days_until_payment(self) -> int:
        """Рассчитать дни до следующего платежа"""
        today = datetime.now()
        current_month = today.month
        current_year = today.year

        # Определяем дату следующего платежа
        billing_day = min(self.billing_day, calendar.monthrange(current_year, current_month)[1])

        if today.day <= billing_day:
            # Платеж в этом месяце
            next_payment = datetime(current_year, current_month, billing_day)
        else:
            # Платеж в следующем месяце
            if current_month == 12:
                next_month = 1
                next_year = current_year + 1
            else:
                next_month = current_month + 1
                next_year = current_year
            billing_day = min(self.billing_day, calendar.monthrange(next_year, next_month)[1])
            next_payment = datetime(next_year, next_month, billing_day)

        return (next_payment - today).days + 1


class SubscriptionCard(ctk.CTkFrame):
    """Карточка подписки"""

    def __init__(self, parent, subscription: Subscription, on_edit, on_delete, **kwargs):
        super().__init__(parent, **kwargs)

        self.subscription = subscription
        self.on_edit = on_edit
        self.on_delete = on_delete

        days_left = subscription.days_until_payment()

        # Определяем цвет в зависимости от срочности
        if days_left <= 3:
            border_color = "#FF4444"  # Красный - срочно
            status_color = "#FF4444"
            status_text = "⚠️ Скоро!"
        elif days_left <= 7:
            border_color = "#FFB344"  # Оранжевый
            status_color = "#FFB344"
            status_text = "📅 На неделе"
        else:
            border_color = "#44FF77"  # Зелёный
            status_color = "#44FF77"
            status_text = "✓ Не скоро"

        self.configure(
            fg_color="#1E1E2E",
            corner_radius=15,
            border_width=2,
            border_color=border_color
        )

        # Основной контейнер
        self.grid_columnconfigure(1, weight=1)

        # Иконка и цвет категории
        icon_frame = ctk.CTkFrame(
            self,
            fg_color=subscription.color,
            corner_radius=12,
            width=50,
            height=50
        )
        icon_frame.grid(row=0, column=0, rowspan=2, padx=15, pady=15)
        icon_frame.grid_propagate(False)

        icon_label = ctk.CTkLabel(
            icon_frame,
            text=subscription.icon,
            font=ctk.CTkFont(size=24),
            text_color="white"
        )
        icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Информация о подписке
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="w", padx=5, pady=(15, 0))

        name_label = ctk.CTkLabel(
            info_frame,
            text=subscription.name,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        name_label.pack(anchor="w")

        category_label = ctk.CTkLabel(
            info_frame,
            text=subscription.category,
            font=ctk.CTkFont(size=12),
            text_color="#888888"
        )
        category_label.pack(anchor="w")

        # Дни до оплаты
        days_frame = ctk.CTkFrame(self, fg_color="transparent")
        days_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(0, 15))

        days_label = ctk.CTkLabel(
            days_frame,
            text=f"До оплаты: {days_left} дн.",
            font=ctk.CTkFont(size=13),
            text_color=status_color
        )
        days_label.pack(side="left")

        status_label = ctk.CTkLabel(
            days_frame,
            text=f"  •  {status_text}",
            font=ctk.CTkFont(size=12),
            text_color=status_color
        )
        status_label.pack(side="left")

        # Цена
        price_frame = ctk.CTkFrame(self, fg_color="transparent")
        price_frame.grid(row=0, column=2, rowspan=2, padx=15, pady=15)

        price_label = ctk.CTkLabel(
            price_frame,
            text=f"{subscription.price:,.0f}₽",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#4CAF50"
        )
        price_label.pack()

        month_label = ctk.CTkLabel(
            price_frame,
            text="/мес",
            font=ctk.CTkFont(size=11),
            text_color="#666666"
        )
        month_label.pack()

        # Кнопки действий
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=0, column=3, rowspan=2, padx=10, pady=15)

        edit_btn = ctk.CTkButton(
            actions_frame,
            text="✏️",
            width=35,
            height=35,
            fg_color="#2D2D3D",
            hover_color="#3D3D4D",
            corner_radius=8,
            command=lambda: self.on_edit(subscription)
        )
        edit_btn.pack(pady=2)

        delete_btn = ctk.CTkButton(
            actions_frame,
            text="🗑️",
            width=35,
            height=35,
            fg_color="#2D2D3D",
            hover_color="#FF4444",
            corner_radius=8,
            command=lambda: self.on_delete(subscription.id)
        )
        delete_btn.pack(pady=2)


class AddSubscriptionDialog(ctk.CTkToplevel):
    """Диалог добавления/редактирования подписки"""

    # Предустановленные сервисы
    PRESETS = {
        "Netflix": {"icon": "🎬", "color": "#E50914", "category": "Видео"},
        "Spotify": {"icon": "🎵", "color": "#1DB954", "category": "Музыка"},
        "Яндекс.Плюс": {"icon": "🔴", "color": "#FC3F1D", "category": "Мультисервис"},
        "YouTube Premium": {"icon": "▶️", "color": "#FF0000", "category": "Видео"},
        "Apple Music": {"icon": "🍎", "color": "#FA2D48", "category": "Музыка"},
        "VK Музыка": {"icon": "🎧", "color": "#0077FF", "category": "Музыка"},
        "Кинопоиск": {"icon": "🎥", "color": "#FF6600", "category": "Видео"},
        "iCloud": {"icon": "☁️", "color": "#3693F3", "category": "Хранилище"},
        "Telegram Premium": {"icon": "✈️", "color": "#229ED9", "category": "Мессенджер"},
        "ChatGPT Plus": {"icon": "🤖", "color": "#10A37F", "category": "AI"},
        "Notion": {"icon": "📝", "color": "#000000", "category": "Продуктивность"},
        "Другое": {"icon": "📦", "color": "#6B7280", "category": "Другое"},
    }

    ICONS = ["🎬", "🎵", "🔴", "▶️", "🍎", "🎧", "🎥", "☁️", "✈️", "🤖", "📝", "📦", "💪", "📚", "🎮", "💼"]
    COLORS = ["#E50914", "#1DB954", "#FC3F1D", "#FF0000", "#FA2D48", "#0077FF", "#FF6600", "#3693F3", "#229ED9", "#10A37F", "#6B7280", "#9333EA"]

    def __init__(self, parent, subscription=None, on_save=None):
        super().__init__(parent)

        self.subscription = subscription
        self.on_save = on_save
        self.selected_icon = "📦"
        self.selected_color = "#6B7280"

        self.title("✏️ Редактировать" if subscription else "➕ Новая подписка")
        self.geometry("520x800")
        self.minsize(520, 600)
        self.resizable(True, True)

        self.configure(fg_color="#121218")

        # Центрирование окна
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 800) // 2
        self.geometry(f"+{x}+{y}")

        self.grab_set()
        self.focus_force()

        self._create_widgets()

        if subscription:
            self._fill_data(subscription)

    def _create_widgets(self):
        # ============ КНОПКИ СОХРАНЕНИЯ ВВЕРХУ ============
        # Фиксированная панель с кнопками сверху - всегда видна!
        top_buttons_frame = ctk.CTkFrame(self, fg_color="#1a1a24", corner_radius=0)
        top_buttons_frame.pack(fill="x", side="top")

        # Заголовок
        title_label = ctk.CTkLabel(
            top_buttons_frame,
            text="✏️ Редактировать подписку" if self.subscription else "➕ Добавить подписку",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(side="left", padx=20, pady=15)

        # Кнопка сохранения справа вверху
        save_btn_top = ctk.CTkButton(
            top_buttons_frame,
            text="💾 Сохранить",
            width=140,
            height=40,
            fg_color="#4CAF50",
            hover_color="#45A049",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._save
        )
        save_btn_top.pack(side="right", padx=10, pady=15)

        # Кнопка отмены
        cancel_btn_top = ctk.CTkButton(
            top_buttons_frame,
            text="✕ Отмена",
            width=100,
            height=40,
            fg_color="#2D2D3D",
            hover_color="#3D3D4D",
            font=ctk.CTkFont(size=14),
            command=self.destroy
        )
        cancel_btn_top.pack(side="right", pady=15)

        # ============ ПРОКРУЧИВАЕМАЯ ОБЛАСТЬ ============
        scroll_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color="#3D3D4D",
            scrollbar_button_hover_color="#4D4D5D"
        )
        scroll_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ============ БЫСТРЫЙ ВЫБОР СЕРВИСА ============
        presets_label = ctk.CTkLabel(
            scroll_container,
            text="🚀 Популярные сервисы (нажмите для автозаполнения):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        presets_label.pack(anchor="w", padx=20, pady=(10, 5))

        presets_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        presets_frame.pack(fill="x", padx=20, pady=10)

        row = 0
        col = 0
        for name, data in self.PRESETS.items():
            btn = ctk.CTkButton(
                presets_frame,
                text=f"{data['icon']} {name}",
                width=150,
                height=35,
                fg_color="#2D2D3D",
                hover_color="#3D3D4D",
                font=ctk.CTkFont(size=12),
                command=lambda n=name, d=data: self._apply_preset(n, d)
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            col += 1
            if col > 2:
                col = 0
                row += 1

        # Настройка колонок для равномерного распределения
        presets_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # ============ ФОРМА ВВОДА ============
        form_frame = ctk.CTkFrame(scroll_container, fg_color="#1E1E2E", corner_radius=15)
        form_frame.pack(fill="x", padx=20, pady=15)

        # Название
        name_label = ctk.CTkLabel(
            form_frame,
            text="📌 Название подписки:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        name_label.pack(anchor="w", padx=20, pady=(20, 5))

        self.name_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Например: Netflix, Spotify, Яндекс.Плюс...",
            height=45,
            font=ctk.CTkFont(size=14),
            corner_radius=10
        )
        self.name_entry.pack(fill="x", padx=20)

        # Стоимость
        price_label = ctk.CTkLabel(
            form_frame,
            text="💰 Стоимость (₽ в месяц):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        price_label.pack(anchor="w", padx=20, pady=(20, 5))

        self.price_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Например: 199, 599, 1490...",
            height=45,
            font=ctk.CTkFont(size=14),
            corner_radius=10
        )
        self.price_entry.pack(fill="x", padx=20)

        # День списания
        day_label = ctk.CTkLabel(
            form_frame,
            text="📅 День списания (число месяца):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        day_label.pack(anchor="w", padx=20, pady=(20, 5))

        day_container = ctk.CTkFrame(form_frame, fg_color="transparent")
        day_container.pack(fill="x", padx=20)

        self.day_slider = ctk.CTkSlider(
            day_container,
            from_=1,
            to=31,
            number_of_steps=30,
            width=300,
            command=self._update_day_label
        )
        self.day_slider.set(15)
        self.day_slider.pack(side="left", padx=(0, 15))

        self.day_value_label = ctk.CTkLabel(
            day_container,
            text="15 число",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4CAF50",
            width=100
        )
        self.day_value_label.pack(side="left")

        # Категория
        category_label = ctk.CTkLabel(
            form_frame,
            text="🏷️ Категория:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        category_label.pack(anchor="w", padx=20, pady=(20, 5))

        self.category_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Видео, Музыка, Хранилище, Другое...",
            height=45,
            font=ctk.CTkFont(size=14),
            corner_radius=10
        )
        self.category_entry.pack(fill="x", padx=20, pady=(0, 20))

        # ============ ИКОНКА ============
        icon_frame = ctk.CTkFrame(scroll_container, fg_color="#1E1E2E", corner_radius=15)
        icon_frame.pack(fill="x", padx=20, pady=10)

        icon_label = ctk.CTkLabel(
            icon_frame,
            text="😀 Выберите иконку:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        icon_label.pack(anchor="w", padx=20, pady=(15, 10))

        icons_container = ctk.CTkFrame(icon_frame, fg_color="transparent")
        icons_container.pack(padx=20, pady=(0, 15))

        self.icon_buttons = []
        for i, icon in enumerate(self.ICONS):
            btn = ctk.CTkButton(
                icons_container,
                text=icon,
                width=40,
                height=40,
                fg_color="#2D2D3D",
                hover_color="#3D3D4D",
                font=ctk.CTkFont(size=18),
                corner_radius=10,
                command=lambda ic=icon: self._select_icon(ic)
            )
            btn.grid(row=i // 8, column=i % 8, padx=3, pady=3)
            self.icon_buttons.append((icon, btn))

        # ============ ЦВЕТ ============
        color_frame = ctk.CTkFrame(scroll_container, fg_color="#1E1E2E", corner_radius=15)
        color_frame.pack(fill="x", padx=20, pady=10)

        color_label = ctk.CTkLabel(
            color_frame,
            text="🎨 Выберите цвет:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        color_label.pack(anchor="w", padx=20, pady=(15, 10))

        colors_container = ctk.CTkFrame(color_frame, fg_color="transparent")
        colors_container.pack(padx=20, pady=(0, 15))

        self.color_buttons = []
        for i, color in enumerate(self.COLORS):
            btn = ctk.CTkButton(
                colors_container,
                text="",
                width=35,
                height=35,
                fg_color=color,
                hover_color=color,
                corner_radius=17,
                border_width=0,
                command=lambda c=color: self._select_color(c)
            )
            btn.grid(row=0, column=i, padx=4, pady=4)
            self.color_buttons.append((color, btn))

        # ============ КНОПКИ ДЕЙСТВИЙ ВНИЗУ (дублирование) ============
        bottom_buttons_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        bottom_buttons_frame.pack(fill="x", padx=20, pady=20)

        cancel_btn = ctk.CTkButton(
            bottom_buttons_frame,
            text="✕ Отмена",
            width=200,
            height=50,
            fg_color="#2D2D3D",
            hover_color="#3D3D4D",
            font=ctk.CTkFont(size=15),
            corner_radius=12,
            command=self.destroy
        )
        cancel_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(
            bottom_buttons_frame,
            text="💾 Сохранить подписку",
            width=250,
            height=50,
            fg_color="#4CAF50",
            hover_color="#45A049",
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=12,
            command=self._save
        )
        save_btn.pack(side="right", padx=5)

        # Подсказка
        hint_label = ctk.CTkLabel(
            scroll_container,
            text="💡 Совет: выберите готовый сервис выше для быстрого заполнения",
            font=ctk.CTkFont(size=12),
            text_color="#666666"
        )
        hint_label.pack(pady=(0, 20))

    def _update_day_label(self, value):
        day = int(value)
        self.day_value_label.configure(text=f"{day} число")

    def _select_icon(self, icon):
        self.selected_icon = icon
        for ic, btn in self.icon_buttons:
            if ic == icon:
                btn.configure(fg_color="#4CAF50", border_width=2, border_color="white")
            else:
                btn.configure(fg_color="#2D2D3D", border_width=0)

    def _select_color(self, color):
        self.selected_color = color
        for c, btn in self.color_buttons:
            if c == color:
                btn.configure(border_width=3, border_color="white")
            else:
                btn.configure(border_width=0)

    def _apply_preset(self, name, data):
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, name)
        self.category_entry.delete(0, "end")
        self.category_entry.insert(0, data["category"])
        self._select_icon(data["icon"])
        self._select_color(data["color"])

    def _fill_data(self, sub: Subscription):
        self.name_entry.insert(0, sub.name)
        self.price_entry.insert(0, str(int(sub.price)))
        self.day_slider.set(sub.billing_day)
        self._update_day_label(sub.billing_day)
        self.category_entry.insert(0, sub.category)
        self._select_icon(sub.icon)
        self._select_color(sub.color)

    def _save(self):
        name = self.name_entry.get().strip()
        price_str = self.price_entry.get().strip()
        category = self.category_entry.get().strip() or "Другое"

        # Валидация
        if not name:
            self.name_entry.configure(border_color="#FF4444", border_width=2)
            self.name_entry.focus()
            return

        self.name_entry.configure(border_width=0)

        if not price_str:
            self.price_entry.configure(border_color="#FF4444", border_width=2)
            self.price_entry.focus()
            return

        try:
            price = float(price_str)
            if price <= 0:
                raise ValueError
        except ValueError:
            self.price_entry.configure(border_color="#FF4444", border_width=2)
            self.price_entry.focus()
            return

        self.price_entry.configure(border_width=0)

        sub_data = {
            "id": self.subscription.id if self.subscription else None,
            "name": name,
            "price": price,
            "billing_day": int(self.day_slider.get()),
            "category": category,
            "color": self.selected_color,
            "icon": self.selected_icon
        }

        if self.on_save:
            self.on_save(sub_data)

        self.destroy()


class SubscriptionTracker(ctk.CTk):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()

        self.title("💳 Менеджер подписок")
        self.geometry("750x750")
        self.minsize(650, 500)
        self.configure(fg_color="#0D0D12")

        # Центрирование окна
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 750) // 2
        y = (self.winfo_screenheight() - 750) // 2
        self.geometry(f"+{x}+{y}")

        self.subscriptions = []
        self.next_id = 1

        self._load_data()
        self._create_widgets()
        self._refresh_list()

    def _create_widgets(self):
        # ============ ВЕРХНЯЯ ПАНЕЛЬ ============
        header_frame = ctk.CTkFrame(self, fg_color="#1E1E2E", corner_radius=0)
        header_frame.pack(fill="x")

        # Заголовок
        title_label = ctk.CTkLabel(
            header_frame,
            text="💳 Менеджер подписок",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=(20, 15))

        # Контейнер для суммы и кнопки
        top_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_container.pack(fill="x", padx=30, pady=(0, 15))

        # Общая сумма (слева)
        self.total_frame = ctk.CTkFrame(top_container, fg_color="#2D2D3D", corner_radius=15)
        self.total_frame.pack(side="left")

        self.total_label = ctk.CTkLabel(
            self.total_frame,
            text="💰 Ты тратишь: 0 ₽/мес",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#4CAF50"
        )
        self.total_label.pack(pady=15, padx=25)

        # Кнопка добавления (справа) - ВСЕГДА ВИДНА
        add_btn = ctk.CTkButton(
            top_container,
            text="➕ Добавить подписку",
            width=220,
            height=55,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#4CAF50",
            hover_color="#45A049",
            corner_radius=15,
            command=self._add_subscription
        )
        add_btn.pack(side="right")

        # ============ СТАТИСТИКА ============
        stats_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=30, pady=(0, 20))

        self.stat_cards_frame = ctk.CTkFrame(stats_frame, fg_color="transparent")
        self.stat_cards_frame.pack(fill="x")
        self.stat_cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Карточка: Количество подписок
        card1 = ctk.CTkFrame(self.stat_cards_frame, fg_color="#1E1E2E", corner_radius=12)
        card1.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(card1, text="📊", font=ctk.CTkFont(size=20)).pack(pady=(10, 0))
        ctk.CTkLabel(card1, text="Подписок", font=ctk.CTkFont(size=11), text_color="#888888").pack()
        self.count_label = ctk.CTkLabel(card1, text="0", font=ctk.CTkFont(size=18, weight="bold"))
        self.count_label.pack(pady=(0, 10))

        # Карточка: Ближайший платёж
        card2 = ctk.CTkFrame(self.stat_cards_frame, fg_color="#1E1E2E", corner_radius=12)
        card2.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(card2, text="⏰", font=ctk.CTkFont(size=20)).pack(pady=(10, 0))
        ctk.CTkLabel(card2, text="Ближайший платёж", font=ctk.CTkFont(size=11), text_color="#888888").pack()
        self.next_payment_label = ctk.CTkLabel(card2, text="—", font=ctk.CTkFont(size=18, weight="bold"))
        self.next_payment_label.pack(pady=(0, 10))

        # Карточка: Годовые траты
        card3 = ctk.CTkFrame(self.stat_cards_frame, fg_color="#1E1E2E", corner_radius=12)
        card3.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(card3, text="📅", font=ctk.CTkFont(size=20)).pack(pady=(10, 0))
        ctk.CTkLabel(card3, text="В год", font=ctk.CTkFont(size=11), text_color="#888888").pack()
        self.yearly_label = ctk.CTkLabel(card3, text="0 ₽", font=ctk.CTkFont(size=18, weight="bold"))
        self.yearly_label.pack(pady=(0, 10))

        # ============ СПИСОК ПОДПИСОК ============
        list_header = ctk.CTkFrame(self, fg_color="transparent")
        list_header.pack(fill="x", padx=25, pady=(10, 5))

        ctk.CTkLabel(
            list_header,
            text="📋 Ваши подписки:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color="#3D3D4D",
            scrollbar_button_hover_color="#4D4D5D"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def _refresh_list(self):
        # Очистка списка
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        if not self.subscriptions:
            # Пустое состояние
            empty_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#1E1E2E", corner_radius=15)
            empty_frame.pack(fill="x", pady=30, padx=30)

            ctk.CTkLabel(
                empty_frame,
                text="📭",
                font=ctk.CTkFont(size=50)
            ).pack(pady=(30, 10))

            ctk.CTkLabel(
                empty_frame,
                text="Пока нет подписок",
                font=ctk.CTkFont(size=20, weight="bold")
            ).pack()

            ctk.CTkLabel(
                empty_frame,
                text="Нажмите кнопку «➕ Добавить подписку» выше,\nчтобы начать отслеживать свои расходы",
                font=ctk.CTkFont(size=14),
                text_color="#888888",
                justify="center"
            ).pack(pady=(10, 30))

        else:
            # Сортировка по дням до оплаты (срочные сверху)
            sorted_subs = sorted(self.subscriptions, key=lambda x: x.days_until_payment())

            for sub in sorted_subs:
                card = SubscriptionCard(
                    self.scroll_frame,
                    sub,
                    on_edit=self._edit_subscription,
                    on_delete=self._delete_subscription
                )
                card.pack(fill="x", pady=6, padx=5)

        # Обновление статистики
        self._update_stats()

    def _update_stats(self):
        total = sum(s.price for s in self.subscriptions)
        yearly = total * 12
        count = len(self.subscriptions)

        self.total_label.configure(text=f"💰 Ты тратишь: {total:,.0f} ₽/мес")
        self.count_label.configure(text=str(count))
        self.yearly_label.configure(text=f"{yearly:,.0f} ₽")

        if self.subscriptions:
            nearest = min(self.subscriptions, key=lambda x: x.days_until_payment())
            days = nearest.days_until_payment()

            if days <= 3:
                color = "#FF4444"
            elif days <= 7:
                color = "#FFB344"
            else:
                color = "#44FF77"

            self.next_payment_label.configure(text=f"{days} дн.", text_color=color)
        else:
            self.next_payment_label.configure(text="—", text_color="white")

    def _add_subscription(self):
        dialog = AddSubscriptionDialog(self, on_save=self._save_subscription)
        dialog.focus()

    def _edit_subscription(self, subscription: Subscription):
        dialog = AddSubscriptionDialog(
            self,
            subscription=subscription,
            on_save=self._save_subscription
        )
        dialog.focus()

    def _save_subscription(self, data):
        if data["id"] is None:
            # Новая подписка
            data["id"] = self.next_id
            self.next_id += 1
            sub = Subscription(**data)
            self.subscriptions.append(sub)
        else:
            # Редактирование существующей
            for i, s in enumerate(self.subscriptions):
                if s.id == data["id"]:
                    self.subscriptions[i] = Subscription(**data)
                    break

        self._save_data()
        self._refresh_list()

    def _delete_subscription(self, sub_id: int):
        self.subscriptions = [s for s in self.subscriptions if s.id != sub_id]
        self._save_data()
        self._refresh_list()

    def _save_data(self):
        data = {
            "next_id": self.next_id,
            "subscriptions": [asdict(s) for s in self.subscriptions]
        }
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def _load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.next_id = data.get("next_id", 1)
                    self.subscriptions = [
                        Subscription(**s) for s in data.get("subscriptions", [])
                    ]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Ошибка загрузки данных: {e}")
                self.subscriptions = []


if __name__ == "__main__":
    app = SubscriptionTracker()
    app.mainloop()