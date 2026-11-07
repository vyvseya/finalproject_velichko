import shlex

from prettytable import PrettyTable

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_exchange_rate,
    get_portfolio_summary,
    login_user,
    register_user,
    sell_currency,
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


def handle_buy(args: list[str], current_user: User | None) -> None:
    """Обрабатывает покупку валюты"""
    if current_user is None:
        raise ValueError("Сначала выполните login")

    usage = "Использование: buy --currency <валюта> --amount <сумма>"

    if len(args) != 4:
        raise ValueError(usage)

    options = {}

    for index in range(0, len(args), 2):
        key = args[index]
        value = args[index + 1]

        if key not in ("--currency", "--amount") or key in options:
            raise ValueError(usage)

        options[key] = value

    if set(options) != {"--currency", "--amount"}:
        raise ValueError(usage)

    try:
        amount = float(options["--amount"])
    except ValueError:
        raise ValueError("Сумма покупки должна быть числом") from None

    result = buy_currency(
        current_user,
        options["--currency"],
        amount,
    )

    code = result["currency"]

    if code in ("BTC", "ETH"):
        amount_text = f"{result['amount']:.8f}"
    else:
        amount_text = f"{result['amount']:.2f}"

    print(f"Успешно куплено: {amount_text} {code}")
    print(f"Списано: {result['spent_usd']:.2f} USD")
    print(f"Остаток USD: {result['usd_balance']:.2f}")


def handle_sell(args: list[str], current_user: User | None) -> None:
    """Обрабатывает продажу валюты"""
    if current_user is None:
        raise ValueError("Сначала выполните login")

    usage = "Использование: sell --currency <валюта> --amount <сумма>"

    if len(args) != 4:
        raise ValueError(usage)

    options = {}

    for index in range(0, len(args), 2):
        key = args[index]
        value = args[index + 1]

        if key not in ("--currency", "--amount") or key in options:
            raise ValueError(usage)

        options[key] = value

    if set(options) != {"--currency", "--amount"}:
        raise ValueError(usage)

    try:
        amount = float(options["--amount"])
    except ValueError:
        raise ValueError("Сумма продажи должна быть числом") from None

    result = sell_currency(
        current_user,
        options["--currency"],
        amount,
    )

    code = result["currency"]

    if code in ("BTC", "ETH"):
        amount_text = f"{result['amount']:.8f}"
        balance_text = f"{result['balance']:.8f}"
    else:
        amount_text = f"{result['amount']:.2f}"
        balance_text = f"{result['balance']:.2f}"

    print(f"Успешно продано: {amount_text} {code}")
    print(f"Зачислено: {result['received_usd']:.2f} USD")
    print(f"Остаток {code}: {balance_text}")
    print(f"Остаток USD: {result['usd_balance']:.2f}")


def handle_get_rate(args: list[str]) -> None:
    """Обрабатывает запрос валютного курса"""
    usage = "Использование: get-rate --from <валюта> --to <валюта>"

    if len(args) != 4:
        raise ValueError(usage)

    options = {}

    for index in range(0, len(args), 2):
        key = args[index]
        value = args[index + 1]

        if key not in ("--from", "--to") or key in options:
            raise ValueError(usage)

        options[key] = value

    if set(options) != {"--from", "--to"}:
        raise ValueError(usage)

    result = get_exchange_rate(
        options["--from"],
        options["--to"],
    )

    from_code = result["from_currency"]
    to_code = result["to_currency"]

    print(f"Курс: 1 {from_code} = {result['rate']:.8f} {to_code}")
    print(f"Обратный курс: 1 {to_code} = {result['inverse_rate']:.10f} {from_code}")
    print(f"Обновлено (UTC): {result['updated_at']}")
    print(f"Источник: {result['source']}")
    print(f"Из кэша: {'да' if result['cached'] else 'нет'}")


def run_cli() -> None:
    """Запускает консольный интерфейс валютной платформы"""
    current_user: User | None = None

    print("Добро пожаловать в ValutaTrade Hub!")
    print(
        "Доступные команды: register, login, show-portfolio, "
        "buy, sell, get-rate, help, exit"
    )

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

            elif action == "buy":
                handle_buy(args, current_user)

            elif action == "sell":
                handle_sell(args, current_user)

            elif action == "get-rate":
                handle_get_rate(args)

            elif action == "help":
                print("register --username <имя> --password <пароль>")
                print("login --username <имя> --password <пароль>")
                print("show-portfolio [--base <валюта>]")
                print("buy --currency <валюта> --amount <сумма>")
                print("sell --currency <валюта> --amount <сумма>")
                print("get-rate --from <валюта> --to <валюта>")
                print("exit — выход из программы")

            elif action == "exit":
                print("До свидания!")
                break

            else:
                print(f"Неизвестная команда: {action}")

        except InsufficientFundsError as error:
            print(f"Ошибка: {error}")

        except CurrencyNotFoundError as error:
            print(f"Ошибка: {error}")
            print("Поддерживаемые валюты: USD, EUR, RUB, BTC, ETH")
            print("Для просмотра курса используйте команду get-rate")

        except ApiRequestError as error:
            print(f"Ошибка: {error}")
            print("Повторите попытку позже или проверьте подключение к сети")

        except (ValueError, TypeError) as error:
            print(f"Ошибка: {error}")

        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break
