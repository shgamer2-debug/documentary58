# 58 ПСЧ Документы — GitHub Actions

Автоматизация документооборота 58 ПСЧ.

## Secrets

Настрой в GitHub → Settings → Secrets and variables → Actions:

| Secret | Описание |
|--------|----------|
| `MAIL_PASS` | Пароль от pch-58@mail.ru |
| `TELEGRAM_TOKEN` | Токен бота @Deus_ex_machinaBot |
| `CHAT_ID` | ID группы (-1004320702729) |

## Воркфлоу

- `check-mail.yml` — проверка почты каждые 30 мин в рабочее время
- `digest.yml` — утренний дайджест в 07:55
- `reminders.yml` — напоминания в 08:20, 12:00, 15:00