import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import (
    get_portfolio_summary,
    login_user,
    register_user,
)


def handle_register(args: list[str]) -> None:
    """Обрабатывает команду регистрации пользователя"""
    usage = "Использование: register --username <имя> --password <пароль>"

    if len(args) != 4:
        raise ValueError(usage)

    options = {}

    for index in range(0, len(args), 2):
        key = args[index]
        value = args[index + 1]

        if key not in ("--username", "--password") or key in options:
            raise ValueError(usage)

        options[key] = value

    user = register_user(
        username=options["--username"],
        password=options["--password"],
    )

    print(f"Пользователь '{user.username}' зарегистрирован (id={user.user_id})")
    print("Регистрация завершена успешно")


def handle_login(args: list[str]) -> User:
    """Обрабатывает команду авторизации пользователя"""
    usage = "Использование: login --username <имя> --password <пароль>"

    if len(args) != 4:
        raise ValueError(usage)

    options = {}

    for index in range(0, len(args), 2):
        key = args[index]
        value = args[index + 1]

        if key not in ("--username", "--password") or key in options:
            raise ValueError(usage)

        options[key] = value

    return login_user(
        username=options["--username"],
        password=options["--password"],
    )


def handle_show_portfolio(args: list[str], current_user: User | None) -> None:
    """Показывает портфель авторизованного пользователя"""
    if current_user is None:
        raise ValueError("Сначала выполните login")

    if not args:
        base_currency = "USD"
    elif len(args) == 2 and args[0] == "--base":
        base_currency = args[1]
    else:
        raise ValueError("Использование: show-portfolio [--base <валюта>]")

    summary = get_portfolio_summary(current_user, base_currency)

    print(
        f"Портфель пользователя '{summary['username']}' "
        f"(база: {summary['base_currency']}):"
    )

    if not summary["wallets"]:
        print("В портфеле пока нет кошельков")
        return

    table = PrettyTable()
    table.field_names = [
        "Валюта",
        "Баланс",
        f"Стоимость ({summary['base_currency']})",
    ]

    for wallet in summary["wallets"]:
        code = wallet["currency_code"]
        balance = wallet["balance"]
        value = wallet["value"]

        if code in ("BTC", "ETH"):
            balance_text = f"{balance:.8f}"
        else:
            balance_text = f"{balance:.2f}"

        table.add_row([code, balance_text, f"{value:,.2f}"])

    print(table)
    print(f"ИТОГО: {summary['total']:,.2f} {summary['base_currency']}")


def run_cli() -> None:
    """Запускает консольный интерфейс валютной платформы"""
    current_user: User | None = None

    print("Добро пожаловать в ValutaTrade Hub!")
    print("Доступные команды: register, login, show-portfolio, help, exit")

    while True:
        try:
            command = input("> ").strip()
            parts = shlex.split(command)

            if not parts:
                continue

            action = parts[0]
            args = parts[1:]

            if action == "register":
                handle_register(args)

            elif action == "login":
                current_user = handle_login(args)
                print(f"Вы вошли как '{current_user.username}'")

            elif action == "show-portfolio":
                handle_show_portfolio(args, current_user)

            elif action == "help":
                print("register --username <имя> --password <пароль>")
                print("login --username <имя> --password <пароль>")
                print("show-portfolio [--base <валюта>]")
                print("exit — выход из программы")

            elif action == "exit":
                print("До свидания!")
                break

            else:
                print(f"Неизвестная команда: {action}")

        except ValueError as error:
            print(f"Ошибка: {error}")

        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break
