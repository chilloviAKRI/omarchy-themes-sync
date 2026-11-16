# Omarchy Discord & Vencord Theme Synchronization

Автоматическая синхронизация темы Discord (через Vencord или Vesktop) с текущей системной темой Omarchy.

## Особенности

- **Полная адаптация под Omarchy**: цвета фона, боковых панелей (сервера, каналы, список участников), шапки, полей ввода, карточек, меню, кнопок и статусов подстраиваются под активную тему (`colors.toml`).
- **macOS Blue Выделение Текста**: цвет выделения текста зафиксирован в классический синий цвет macOS (`#0063e6` с белым текстом `#ffffff`), как было запрошено.
- **Галочки, свитчи и бейджи**: динамически адаптируются под цвет акцента текущей темы Omarchy.
- **Поддержка Vencord & Vesktop**: генерирует тему как в виде отдельной Vencord темы (`omarchy.theme.css`), так и в QuickCSS (`quickCss.css`).
- **Автоматическое обновление**: Omarchy хуки (`theme-set.d` и `post-boot.d`) мгновенно перегенерируют тему при смене системной темы (`omarchy theme set <имя>`), а Vencord подхватывает изменения на лету без перезапуска клиента.

## Структура файлов

```
~/.config/omarchy/discord-theme/
├── bin/
│   └── sync.sh               # Скрипт синхронизации темы
├── hooks/
│   ├── post-boot             # Хук при входе в систему
│   └── theme-set             # Хук при смене темы Omarchy
├── install.sh                # Установщик хуков
├── omarchy-discord-theme.py  # Генератор CSS темы
└── README.md
```

## Расположение темы в клиенте

- Vencord: `~/.config/Vencord/themes/omarchy.theme.css` и `~/.config/Vencord/settings/quickCss.css`
- Vesktop: `~/.config/vesktop/themes/omarchy.theme.css` и `~/.config/vesktop/settings/quickCss.css`

## Установка и ручной запуск

Для ручной перегенерации темы:
```bash
~/.config/omarchy/discord-theme/bin/sync.sh
```

Для повторной установки хуков:
```bash
~/.config/omarchy/discord-theme/install.sh
```
