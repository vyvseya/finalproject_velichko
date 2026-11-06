import shlex

from valutatrade_hub.core.usecases import register_user


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


def run_cli() -> None:
    """Запускает консольный интерфейс валютной платформы"""
    print("Добро пожаловать в ValutaTrade Hub!")
    print("Доступные команды: register, help, exit")

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

            elif action == "help":
                print("register --username <имя> --password <пароль>")
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
