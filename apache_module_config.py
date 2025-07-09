import subprocess
import os
import logging

script_path = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_path, 'app.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w')  # Логи записываются только в файл
    ]
)


def run_command(cmd):
    logging.debug(f"Запуск команды: {cmd}")
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout.strip() + ("\n" + result.stderr.strip() if result.stderr else "")
    logging.debug(f"Результат команды: {output}")
    return output.strip(), result.returncode


def check_module_item(num, description, module=None, prefix=None, should_be_enabled=True, enable_func=None, disable_func=None, force_disable=False):
    print(f"[{num}] {description}")
    logging.info(f"[{num}] {description}")
    loaded_modules = run_command("apachectl -M")[0].splitlines()

    if module:
        enabled = any(module in line for line in loaded_modules)
        if should_be_enabled and not enabled:
            print(f"❌ Модуль {module} выключен, включаем...")
            logging.warning(f"Модуль {module} выключен, включаем...")
            if enable_func:
                enable_func()
                logging.info(f"Модуль {module} включён с использованием функции enable_func.")
            else:
                run_command(f"sudo a2enmod {module.replace('_module','')}")
                print(f"[{num}] ✅ Модуль {module} включён.")
                logging.info(f"Модуль {module} включён с помощью команды a2enmod.")
        elif not should_be_enabled and enabled:
            print(f"❌ Модуль {module} включён, отключаем...")
            logging.warning(f"Модуль {module} включён, отключаем...")
            if disable_func:
                disable_func()
                logging.info(f"Модуль {module} отключён с использованием функции disable_func.")
            else:
                force_flag = " -f" if force_disable else ""
                run_command(f"sudo a2dismod {force_flag} {module.replace('_module','')}")
                print(f"✅ Модуль {module} отключён.")
                logging.info(f"Модуль {module} отключён с помощью команды a2dismod.")
        else:
            status = "включён" if enabled else "отключён"
            print(f"✅ Модуль {module} {status} (как и должен быть).")
            logging.info(f"Модуль {module} {status} (как и должен быть).")

    elif prefix:
        found = any(prefix in line for line in loaded_modules)
        if should_be_enabled and not found:
            print(f"❌ Модули с префиксом '{prefix}' не найдены, возможно надо включить.")
            logging.warning(f"Модули с префиксом '{prefix}' не найдены, возможно надо включить.") 
        elif not should_be_enabled and found:
            print(f"❌ Модули с префиксом '{prefix}' включены, рекомендуется отключить через a2dismod")
            logging.warning(f"Модули с префиксом '{prefix}' включены, рекомендуется отключить через a2dismod")
        else:
            print(f"✅ Модули с префиксом '{prefix}' {'включены' if found else 'отключены'} (как и должен быть).")
            logging.info(f"Модули с префиксом '{prefix}' {'включены' if found else 'отключены'} (как и должен быть).")
    print()
    logging.info("")

def check_permissions():
    print("=== Проверка прав доступа Apache ===")
    logging.info("=== Проверка прав доступа Apache ===")

    # 2.1 Проверка процессов
    print("[2.1] Apache запущен от имени сервисной учётной записи без прав суперпользователя")
    logging.info("[2.1] Apache запущен от имени сервисной учётной записи без прав суперпользователя")
    ps_output, _ = run_command("ps aux")
    lines = [line.strip() for line in ps_output.splitlines() if "apache2" in line or "httpd" in line]

    root_count = sum(1 for line in lines if line.startswith("root"))
    non_root_users = [line.split()[0] for line in lines if not line.startswith("root")]

    if root_count == 1:
        print("✅ Первый процесс apache2 от root — корректно (master)")
        logging.info("✅ Первый процесс apache2 от root — корректно (master)")
    else:
        print("❌ Первый процесс должен быть от root!")
        logging.error("❌ Первый процесс должен быть от root!")

    if all(user == "www-data" for user in non_root_users):
        print("✅ Все процессы (кроме master) от www-data")
        logging.info("✅ Все процессы (кроме master) от www-data")
    else:
        print(f"❌ Найдены процессы не от www-data: {', '.join(non_root_users)}")
        logging.warning(f"❌ Найдены процессы не от www-data: {', '.join(non_root_users)}")
    print()
    logging.info("")

    # 2.2 Проверка оболочки
    print("[2.2] Проверка, что у www-data оболочка /sbin/nologin")
    logging.info("[2.2] Проверка, что у www-data оболочка /sbin/nologin")
    shell_line, _ = run_command("getent passwd www-data")
    shell = shell_line.strip().split(":")[-1] if shell_line else ""
    if shell == "/sbin/nologin" or shell == "/usr/sbin/nologin":
        print(f"✅ Оболочка установлена как {shell}")
        logging.info(f"✅ Оболочка установлена как {shell}")
    else:
        print(f"❌ Оболочка не /sbin/nologin: {shell}")
        logging.error(f"❌ Оболочка не /sbin/nologin: {shell}")
    print()
    logging.info("")

    # 2.3 Проверка блокировки учётной записи
    print("[2.3] Проверка, что учётная запись www-data заблокирована для входа")
    logging.info("[2.3] Проверка, что учётная запись www-data заблокирована для входа")
    status_line, _ = run_command("passwd -S www-data")
    if "L" in status_line.split():
        print(f"✅ Учётная запись заблокирована: {status_line}")
        logging.info(f"✅ Учётная запись заблокирована: {status_line}")
    else:
        logging.error(f"❌ Учётная запись активна: {status_line}")
        logging.info("🔧 Блокируем учётную запись www-data...")
        print(f"❌ Учётная запись активна: {status_line}")
        print("🔧 Блокируем учётную запись www-data...")
        _, code = run_command("sudo usermod -L www-data")
        if code == 0:
            print("✅ Учётная запись успешно заблокирована")
            logging.info("✅ Учётная запись успешно заблокирована")
        else:
            print("❌ Не удалось заблокировать учётную запись!")
            logging.error("❌ Не удалось заблокировать учётную запись!")
    print()
    logging.info("")

    # 2.4 Проверка владельца директорий
    print("[2.4] Проверка владельца директорий Apache")
    logging.info("[2.4] Проверка владельца директорий Apache")
    # Список путей для проверки
    directories_to_check = [
        "/etc/apache2",          # Конфигурационные файлы Apache
        "/usr/share/apache2",    # Основные файлы и папки Apache
        "/var/www",              # Веб-контент
        "/etc/ssl/private",      # Приватные ключи SSL
        "/var/log/apache2",      # Лог-файлы Apache
        "/run/apache2"           # Временные файлы и PID
    ]

    # Проверка каждого пути
    for path in directories_to_check:
        print(f"Проверка для {path}...")
        logging.info(f"Проверка для {path}...")
        output, _ = run_command(f"find {path} \\! -user root")
        
        if not output.strip():
            print(f"✅ Все файлы в {path} принадлежат root")
            logging.info(f"✅ Все файлы в {path} принадлежат root")
        else:
            print(f"❌ Найдены файлы не от root в {path}")
            logging.warning(f"❌ Найдены файлы не от root в {path}")
            # Можно добавить исправление, чтобы установить владельца root
            run_command(f"sudo chown root:root {path} -R")
            print(f"✅ Установлены владельцы root:root для всех файлов в {path}")
    print()
    logging.info("")

    # 2.5 Проверка прав other
    print("[2.5] Проверка прав доступа на /etc/apache2")
    logging.info("[2.5] Проверка прав доступа на /etc/apache2")
    files_with_other_write, _ = run_command("find /etc/apache2 -perm /o=w -type f")
    if files_with_other_write.strip():
        print("❌ Найдены файлы с правами записи для other:")
        print(files_with_other_write.strip())
        logging.warning("❌ Найдены файлы с правами записи для other:")
        logging.warning(files_with_other_write.strip())
    else:
        print("✅ Права доступа на запись для other отсутствуют")
        logging.info("✅ Права доступа на запись для other отсутствуют")
    print()
    logging.info("")
    # 2.6 Проверка логов
    print("[2.6] Проверка /var/log/apache2 принадлежит root:www-data и chmod 660")
    logging.info("[2.6] Проверка /var/log/apache2 принадлежит root:www-data и chmod 660")
    # Проверяем владельца, группу и права
    owner, _ = run_command("stat -c %U /var/log/apache2")
    group, _ = run_command("stat -c %G /var/log/apache2")
    perms, _ = run_command("stat -c %a /var/log/apache2")
    
    # Если все соответствует, выводим успех
    if owner == "root" and group == "www-data" and perms == "660":
        print("✅ /var/log/apache2 соответствует требованиям")
        logging.info("✅ /var/log/apache2 соответствует требованиям")
    else:
        print("❌ /var/log/apache2 имеет некорректные владельца или права")
        logging.error("❌ /var/log/apache2 имеет некорректные владельца или права")
        # Если владельцы или права не соответствуют, исправляем
        if owner != "root" or group != "www-data":
            print("Выполняется изменение владельца и группы на root:www-data")
            logging.info("Выполняется изменение владельца и группы на root:www-data")
            run_command("sudo chown root:www-data /var/log/apache2 -R")
        
        if perms != "660":
            print("Выполняется изменение прав на 660")
            logging.info("Выполняется изменение прав на 660")
            run_command("sudo chmod 660 /var/log/apache2 -R")
        
        # Проверим снова
        print("Проверка после исправлений...")
        logging.info("Проверка после исправлений...")
        owner, _ = run_command("stat -c %U /var/log/apache2")
        group, _ = run_command("stat -c %G /var/log/apache2")
        perms, _ = run_command("stat -c %a /var/log/apache2")
        
        if owner == "root" and group == "www-data" and perms == "660":
            print("✅ /var/log/apache2 теперь соответствует требованиям")
            logging.info("✅ /var/log/apache2 теперь соответствует требованиям")
        else:
            print("❌ Ошибка при применении прав и владельцев.")
            logging.error("❌ Ошибка при применении прав и владельцев.")
    logging.info("")
    # 2.8 Проверка PID файла
    print("[2.8] Проверка прав на /run/apache2/apache2.pid")
    logging.info("[2.8] Проверка прав на /run/apache2/apache2.pid")
    # Проверяем владельца, группу и права
    pid_user, _ = run_command("stat -c %U /run/apache2/apache2.pid")
    pid_group, _ = run_command("stat -c %G /run/apache2/apache2.pid")
    pid_perm, _ = run_command("stat -c %a /run/apache2/apache2.pid")
    
    # Если все соответствует, выводим успех
    if pid_user == "root" and pid_group == "root" and pid_perm == "644":
        print("✅ /run/apache2/apache2.pid соответствует требованиям")
        logging.info("✅ /run/apache2/apache2.pid соответствует требованиям")
    else:
        print("❌ /run/apache2/apache2.pid имеет некорректные владельца или права")
        logging.error("❌ /run/apache2/apache2.pid имеет некорректные владельца или права")
        # Если владельцы или права не соответствуют, исправляем
        if pid_user != "root" or pid_group != "root":
            print("Выполняется изменение владельца и группы на root:root")
            logging.info("Выполняется изменение владельца и группы на root:root")
            run_command("sudo chown root:root /run/apache2/apache2.pid")
        
        if pid_perm != "644":
            print("Выполняется изменение прав на 644")
            logging.info("Выполняется изменение прав на 644")
            run_command("sudo chmod 644 /run/apache2/apache2.pid")
        
        # Проверим снова
        print("Проверка после исправлений...")
        logging.info("Проверка после исправлений...")
        pid_user, _ = run_command("stat -c %U /run/apache2/apache2.pid")
        pid_group, _ = run_command("stat -c %G /run/apache2/apache2.pid")
        pid_perm, _ = run_command("stat -c %a /run/apache2/apache2.pid")
        
        if pid_user == "root" and pid_group == "root" and pid_perm == "644":
            print("✅ /run/apache2/apache2.pid теперь соответствует требованиям")
            logging.info("✅ /run/apache2/apache2.pid теперь соответствует требованиям")
        else:
            print("❌ Ошибка при применении прав и владельцев.")
            logging.error("❌ Ошибка при применении прав и владельцев.")
    logging.info("")
    # 2.9 Проверка ScoreBoardFile
    print("[2.9] Проверка файла ScoreBoardFile")
    logging.info("[2.9] Проверка файла ScoreBoardFile")
    # Ищем путь к ScoreBoardFile в конфигурации
    grep_output, _ = run_command('grep -r "ScoreBoardFile" /etc/apache2/*.conf')

    if grep_output.strip():
        # Пытаемся извлечь путь к ScoreBoardFile
        import re
        match = re.search(r'ScoreBoardFile\s+(\S+)', grep_output)
        if match:
            scoreboard_path = match.group(1)

            # Проверяем, существует ли файл
            if os.path.exists(scoreboard_path):
                owner, _ = run_command(f"stat -c %U {scoreboard_path}")
                group, _ = run_command(f"stat -c %G {scoreboard_path}")
                perms, _ = run_command(f"stat -c %A {scoreboard_path}")

                # Проверяем владельца и группу
                if owner == "root" and group == "root":
                    print("✅ ScoreBoardFile имеет владельца root:root")
                    logging.info("✅ ScoreBoardFile имеет владельца root:root")
                else:
                    print("❌ Некорректные владельцы ScoreBoardFile — исправляю...")
                    logging.error("❌ Некорректные владельцы ScoreBoardFile — исправляю...")
                    run_command(f"chown root:root {scoreboard_path}")
                    print("✅ Установлены владельцы root:root")
                    logging.info("✅ Установлены владельцы root:root")

                # Проверяем права доступа: никто, кроме root и www-data, не должен иметь прав на запись
                uid, _ = run_command(f"stat -c %u {scoreboard_path}")
                gid, _ = run_command(f"stat -c %g {scoreboard_path}")
                groupname = group.strip()

                # Проверим права на запись для "other"
                if perms[8] != 'w':
                    print("✅ У других пользователей нет прав на запись")
                    logging.info("✅ У других пользователей нет прав на запись")
                else:
                    print("❌ У других пользователей есть права на запись — убираю...")
                    logging.error("❌ У других пользователей есть права на запись — убираю...")
                    run_command(f"chmod o-w {scoreboard_path}")
                    print("✅ Права на запись для других удалены")
                    logging.info("✅ Права на запись для других удалены")
            else:
                print(f"⚠️ Файл ScoreBoardFile указан, но не существует: {scoreboard_path}")
                logging.warning(f"⚠️ Файл ScoreBoardFile указан, но не существует: {scoreboard_path}")
        else:
            print("⚠️ Не удалось извлечь путь к ScoreBoardFile")
            logging.warning("⚠️ Не удалось извлечь путь к ScoreBoardFile")
    else:
        print("✅ ScoreBoardFile не найден — всё нормально")
        logging.info("✅ ScoreBoardFile не найден — всё нормально")
    print()
    logging.info("")

    # 2.10 Проверка прав для group
    print("[2.10] Проверка, что group не имеет прав на запись в /etc/apache2")
    logging.info("[2.10] Проверка, что group не имеет прав на запись в /etc/apache2")
    group_write, _ = run_command("find /etc/apache2 -perm /g=w -ls | grep -v 'lrwxrwxrwx'")
    if group_write.strip():
        print("❌ Найдены файлы с правами group=w:")
        print(group_write.strip())
        logging.warning("❌ Найдены файлы с правами group=w:")
        logging.warning(group_write.strip())
    else:
        print("✅ Права group в норме")
        logging.info("✅ Права group в норме")
    print("=== Проверка прав доступа завершена ===\n")
    logging.info("=== Проверка прав доступа завершена ===\n")

def check_access_controls():
    print("=== Проверка контроля доступа Apache ===")
    logging.info("=== Проверка контроля доступа Apache ===")
    apache_conf = "/etc/apache2/apache2.conf"

    # 3.1 Проверка <Directory />
    print("[3.1] Проверка запрета доступа к корневой директории (<Directory />)...")
    logging.info("[3.1] Проверка запрета доступа к корневой директории (<Directory />)...")
    try:
        with open(apache_conf, "r") as f:
            content = f.read()

        if '<Directory />' in content and 'Require all denied' in content:
            print("✅ Доступ к <Directory /> запрещён.")
            logging.info("✅ Доступ к <Directory /> запрещён.")
        else:
            print("❌ Доступ к <Directory /> не ограничен. Добавляем директиву...")
            logging.warning("❌ Доступ к <Directory /> не ограничен. Добавляем директиву...")
            with open(apache_conf, "a") as f:
                f.write("\n<Directory />\n    Require all denied\n</Directory>\n")
            print("✅ Директива <Directory /> добавлена.")
            logging.info("✅ Директива <Directory /> добавлена.")
    except Exception as e:
        print(f"⚠️ Ошибка при проверке 3.1: {e}")
        logging.error(f"⚠️ Ошибка при проверке 3.1: {e}")

    # 3.2 Проверка <Location /portal>
    print("[3.2] Проверка настроек доступа к /portal...")
    logging.info("[3.2] Проверка настроек доступа к /portal...")
    try:
        if '<Location /portal>' in content and 'Require valid-user' in content:
            print("✅ Доступ к /portal ограничен.")
            logging.info("✅ Доступ к /portal ограничен.")
        else:
            print("❌ Ограничения на доступ к /portal отсутствуют. Добавляем секцию...")
            logging.warning("❌ Ограничения на доступ к /portal отсутствуют. Добавляем секцию...")
            with open(apache_conf, "a") as f:
                f.write("\n<Location /portal>\n    Require valid-user\n</Location>\n")
            print("✅ Секция <Location /portal> добавлена.")
            logging.info("✅ Секция <Location /portal> добавлена.")
    except Exception as e:
        print(f"⚠️ Ошибка при проверке 3.2: {e}")
        logging.error(f"⚠️ Ошибка при проверке 3.2: {e}")

    # 3.3 Проверка AllowOverrideList
    print("[3.3] Проверка отсутствия директивы AllowOverrideList...")
    logging.info("[3.3] Проверка отсутствия директивы AllowOverrideList...")
    try:
        result = run_command("grep -rl 'AllowOverrideList' /etc/apache2")[0].splitlines()
        if result:
            print(f"❌ Найдена директива AllowOverrideList в: {', '.join(result)}")
            logging.warning(f"❌ Найдена директива AllowOverrideList в: {', '.join(result)}")
            for file in result:
                try:
                    with open(file, "r") as f:
                        lines = f.readlines()
                    with open(file, "w") as f:
                        for line in lines:
                            if "AllowOverrideList" not in line:
                                f.write(line)
                    print(f"✅ Удалена директива из {file}")
                    logging.info(f"✅ Удалена директива из {file}")
                except Exception as e:
                    print(f"⚠️ Не удалось обработать {file}: {e}")
                    logging.error(f"⚠️ Не удалось обработать {file}: {e}")
        else:
            print("✅ AllowOverrideList не найдена.")
            logging.info("✅ AllowOverrideList не найдена.")
    except Exception as e:
        print(f"⚠️ Ошибка при проверке 3.3: {e}")
        logging.error(f"⚠️ Ошибка при проверке 3.3: {e}")

    print("=== Проверка контроля доступа завершена ===\n")
    logging.info("=== Проверка контроля доступа завершена ===\n")

def append_if_missing(path, text):
    if not os.path.exists(path):
        print(f"❌ Файл не найден: {path}")
        logging.error(f"❌ Файл не найден: {path}")
        return False
    with open(path, 'r+') as f:
        content = f.read()
        if text not in content:
            f.write("\n" + text + "\n")
            logging.info(f"✅ Добавлена директива в {path}")
            return True
    logging.info(f"✅ Директива уже присутствует в {path}")        
    return False

def comment_out_line_in_file(path, line_start):
    if not os.path.exists(path):
        print(f"❌ Файл не найден: {path}")
        logging.error(f"❌ Файл не найден: {path}")
        return False
    with open(path, 'r') as f:
        lines = f.readlines()
    changed = False
    for i, line in enumerate(lines):
        if line.strip().startswith(line_start) and not line.strip().startswith('#'):
            lines[i] = '#' + line
            changed = True
    if changed:
        with open(path, 'w') as f:
            f.writelines(lines)
            logging.info(f"✅ Строки с {line_start} закомментированы в {path}")
    return changed

def file_contains(path, text):
    if not os.path.exists(path):
        logging.error(f"❌ Файл не найден: {path}")
        return False
    with open(path) as f:
        return text in f.read()

def ensure_mod_enabled(mod_name):
    out, _ = run_command(f"a2query -m {mod_name}")
    if "enabled" not in out:
        print(f"❌ Модуль {mod_name} не включён, включаем...")
        logging.warning(f"❌ Модуль {mod_name} не включён, включаем...")
        run_command(f"sudo a2enmod {mod_name}")
        logging.info(f"✅ Модуль {mod_name} включён")
        return True
    logging.info(f"✅ Модуль {mod_name} уже включён")
    return False

def check_and_apply_minimization(allowed_http_methods=None, allowed_extensions=None, hostname=None):
    if allowed_http_methods is None:
        allowed_http_methods = ["GET", "HEAD", "OPTIONS"]
    if allowed_extensions is None:
        allowed_extensions = ["css", "html", "htm", "js", "pdf", "txt", "xml", "xsl", "gif", "ico", "jpeg", "jpg", "png"]

    apache_conf = "/etc/apache2/apache2.conf"
    security_conf = "/etc/apache2/conf-available/security.conf"
    ports_conf = "/etc/apache2/ports.conf"
    www_dir = "/var/www/html"
    cgi_bin = "/usr/local/httpd/cgi-bin"

    print("=== Минимизация опций  ===")
    logging.info("=== Минимизация опций ===")

    # 4.1 Options None
    print("[4.1] Проверка Options None")
    logging.info("[4.1] Проверка Options None")
    options_block = "<Directory />\n    Options None\n</Directory>"
    if not file_contains(apache_conf, "Options None"):
        print("❌ Добавляем Options None")
        logging.warning("❌ Добавляем Options None")
        append_if_missing(apache_conf, options_block)
    else:
        print("✅ Options None есть")
        logging.info("✅ Options None есть")
    # 4.2 Удаление стандартных веб-страниц
    print("[4.2] Проверка стандартных веб-страниц")
    logging.info("[4.2] Проверка стандартных веб-страниц")
    index_html = os.path.join(www_dir, "index.html")
    if os.path.exists(index_html):
        print(f"❌ Найдена стандартная страница {index_html}, удаляем")
        try:
            os.remove(index_html)
            logging.info(f"✅ Стандартная страница {index_html} удалена")
        except Exception as e:
            print(f"Ошибка удаления {index_html}: {e}")
            logging.error(f"Ошибка удаления {index_html}: {e}")
    else:
        print("✅ Стандартные страницы отсутствуют")
        logging.info("✅ Стандартные страницы отсутствуют")
    # 4.3 Удаление стандартного CGI скрипта printenv
    print("[4.3] Проверка стандартного CGI скрипта printenv")
    logging.info("[4.3] Проверка стандартного CGI скрипта printenv")
    out, _ = run_command("find /usr -type f -name printenv")
    if out:
        print(f"❌ Найден CGI скрипт printenv: {out}, удаляем")
        logging.warning(f"❌ Найден CGI скрипт printenv: {out}, удаляем")
        for file_path in out.splitlines():
            try:
                os.remove(file_path)
                logging.info(f"✅ CGI скрипт {file_path} удалён")
            except Exception as e:
                print(f"Ошибка удаления {file_path}: {e}")
                logging.error(f"Ошибка удаления {file_path}: {e}")
    else:
        print("✅ CGI скрипт printenv отсутствует")
        logging.info("✅ CGI скрипт printenv отсутствует")
    # 4.4 Белый список HTTP методов (гибкий список)
    print("[4.4] Проверка белого списка HTTP методов")
    logging.info("[4.4] Проверка белого списка HTTP методов")
    methods_str = " ".join(allowed_http_methods)
    limit_except_block = f"""<Directory "{cgi_bin}">
    <LimitExcept {methods_str}>
        Require all denied
    </LimitExcept>
</Directory>"""
    if not file_contains(apache_conf, "<LimitExcept"):
        print("❌ Добавляем белый список HTTP методов")
        logging.warning("❌ Добавляем белый список HTTP методов")
        append_if_missing(apache_conf, limit_except_block)
    else:
        print("✅ Белый список HTTP методов есть")
        logging.info("✅ Белый список HTTP методов есть")
    # 4.5 Отключение TRACE
    print("[4.5] Проверка TraceEnable off")
    logging.info("[4.5] Проверка TraceEnable off")
    if not file_contains(security_conf, "TraceEnable off"):
        print("❌ Добавляем TraceEnable off")
        logging.warning("❌ Добавляем TraceEnable off")
        append_if_missing(security_conf, "TraceEnable off")
        run_command("sudo a2enconf security")
        logging.info("✅ Конфигурация TraceEnable off добавлена")
    else:
        print("✅ TRACE отключён")
        logging.info("✅ TRACE отключён")
    # 4.6 Отклонение устаревших HTTP протоколов
    print("[4.6] Проверка отклонения устаревших HTTP протоколов")
    logging.info("[4.6] Проверка отклонения устаревших HTTP протоколов")
    ensure_mod_enabled("rewrite")
    rewrite_rules_46 = """
RewriteEngine On
RewriteCond %{THE_REQUEST} !HTTP/1\\.1$
RewriteRule .* - [F]
"""
    conf_content = ""
    if os.path.exists(apache_conf):
        conf_content = open(apache_conf).read()
    if "RewriteEngine On" not in conf_content or "RewriteCond %{THE_REQUEST} !HTTP/1\\.1$" not in conf_content:
        print("❌ Добавляем правила отклонения устаревших протоколов")
        logging.warning("❌ Добавляем правила отклонения устаревших протоколов")
        append_if_missing(apache_conf, rewrite_rules_46)
    else:
        print("✅ Правила отклонения протоколов есть")
        logging.info("✅ Правила отклонения протоколов есть")
    # 4.7 Запрет доступа к .ht* файлам
    print("[4.7] Проверка запрета доступа к .ht* файлам")
    logging.info("[4.7] Проверка запрета доступа к .ht* файлам")
    ht_rule = """<FilesMatch "^\\.ht">
    Require all denied
</FilesMatch>"""
    if not file_contains(apache_conf, ht_rule):
        print("❌ Добавляем запрет доступа к .ht* файлам")
        logging.warning("❌ Добавляем запрет доступа к .ht* файлам")
        append_if_missing(apache_conf, ht_rule)
    else:
        print("✅ Запрет доступа к .ht* файлам есть")
        logging.info("✅ Запрет доступа к .ht* файлам есть")
    # 4.8 Ограничение расширений (гибкий список)
    print("[4.8] Проверка ограничения расширений")
    logging.info("[4.8] Проверка ограничения расширений")
    deny_all = """<FilesMatch "^.*$">
    Require all denied
</FilesMatch>"""
    allowed_regex = "|".join([ext.replace(".", "\\.") for ext in allowed_extensions])
    allow_some = f"""<FilesMatch "^.*\\.({allowed_regex})$">
    Require all granted
</FilesMatch>"""
    if deny_all not in conf_content or allow_some not in conf_content:
        print("❌ Добавляем ограничения расширений")
        logging.warning("❌ Добавляем ограничения расширений")
        append_if_missing(apache_conf, deny_all)
        append_if_missing(apache_conf, allow_some)
    else:
        print("✅ Ограничения расширений есть")
        logging.info("✅ Ограничения расширений есть")
    # 4.9 Запрет запросов по IP и устаревшим HTTP
    print("[4.9] Проверка запрета запросов по IP и устаревшим HTTP")
    logging.info("[4.9] Проверка запрета запросов по IP и устаревшим HTTP")
    ensure_mod_enabled("rewrite")
    if not hostname:
        hostname = "hostname.domain.zone"  # Заменить на реальный hostname
    ip_rewrite = f"""
RewriteEngine On
RewriteCond %{{THE_REQUEST}} HTTP\\/((0\\.9)|(1\\.0))$ [OR]
RewriteCond %{{HTTP_HOST}} !^{hostname}$
RewriteRule .* - [F]
"""
    if "RewriteCond %{THE_REQUEST} HTTP\\/((0\\.9)|(1\\.0))$" not in conf_content:
        print("❌ Добавляем запрет запросов по IP и устаревшим HTTP")
        logging.warning("❌ Добавляем запрет запросов по IP и устаревшим HTTP")
        append_if_missing(apache_conf, ip_rewrite)
    else:
        print("✅ Запрет запросов по IP есть")
        logging.info("✅ Запрет запросов по IP есть")

    # 4.10 Отключение Listen 80, включение Listen 443
    print("[4.10] Проверка Listen 80 и 443")
    logging.info("[4.10] Проверка Listen 80 и 443")
    if os.path.exists(ports_conf):
        with open(ports_conf, 'r') as f:
            ports_conf_text = f.read()
        if "Listen 80" in ports_conf_text and "#Listen 80" not in ports_conf_text:
            print("❌ Комментируем Listen 80")
            logging.warning("❌ Комментируем Listen 80")
            comment_out_line_in_file(ports_conf, "Listen 80")
        else:
            print("✅ Listen 80 уже отключён")
            logging.info("✅ Listen 80 уже отключён")
        if "Listen 443" not in ports_conf_text:
            print("❌ Добавляем Listen 443")
            logging.warning("❌ Добавляем Listen 443")
            append_if_missing(ports_conf, "Listen 443")
        else:
            print("✅ Listen 443 есть")
            logging.info("✅ Listen 443 есть")
    else:
        print(f"❌ Файл {ports_conf} не найден")
        logging.error(f"❌ Файл {ports_conf} не найден")

    # 4.11 Content-Security-Policy заголовок
    print("[4.11] Проверка Content-Security-Policy")
    logging.info("[4.11] Проверка Content-Security-Policy")
    out, _ = run_command("grep -r 'Content-Security-Policy' /etc/apache2/")
    if "Content-Security-Policy" in out:
        print("✅ CSP заголовок уже есть")
        logging.info("✅ CSP заголовок уже есть")
    else:
        print("❌ Включаем модуль headers и добавляем заголовок")
        logging.warning("❌ Включаем модуль headers и добавляем заголовок")
        changed = ensure_mod_enabled("headers")
        csp_header = 'Header always append Content-Security-Policy "frame-ancestors \'self\';"'
        if not file_contains(apache_conf, csp_header):
            append_if_missing(apache_conf, csp_header)
        if changed:
            print("⚠️ Модуль headers был включён, нужно перезапустить apache.")
            logging.warning("⚠️ Модуль headers был включён, нужно перезапустить apache.")
        print("⚠️ Возможно, потребуется перезапуск apache: sudo systemctl restart apache2")
        logging.warning("⚠️ Возможно, потребуется перезапуск apache: sudo systemctl restart apache2")

    print("=== Проверка и применение минимизации завершены ===\n")
    logging.info("=== Проверка и применение минимизации завершены ===\n")


def check_logging_settings():
    print("=== Логирование ===")
    logging.info("=== Логирование ===")

    apache_conf = "/etc/apache2/apache2.conf"
    logrotate_path = "/etc/logrotate.d/apache2"
    desired_loglevels = ["info", "notice", "core:info", "debug"]

    # === 5.1 LogLevel ===
    print("[5.1] Проверка LogLevel...")
    logging.info("[5.1] Проверка LogLevel...")
    try:
        with open(apache_conf, "r") as f:
            lines = f.readlines()

        new_lines = []
        loglevel_found = False
        updated = False

        for line in lines:
            if line.strip().startswith("LogLevel"):
                loglevel_found = True
                current_value = line.strip().split(maxsplit=1)[1] if len(line.strip().split()) > 1 else ""
                if current_value.lower() not in desired_loglevels:
                    print(f"❌ LogLevel = '{current_value}', заменяем на 'info'")
                    logging.warning(f"❌ LogLevel = '{current_value}', заменяем на 'info'")
                    new_lines.append("LogLevel info\n")
                    updated = True
                else:
                    print("✅ LogLevel корректен:", current_value)
                    logging.info(f"✅ LogLevel корректен: {current_value}")
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if not loglevel_found:
            print("❌ LogLevel не найден, добавляем LogLevel info")
            logging.warning("❌ LogLevel не найден, добавляем LogLevel info")
            new_lines.append("\nLogLevel info\n")
            updated = True

        if updated:
            with open(apache_conf, "w") as f:
                f.writelines(new_lines)
            logging.info("✅ LogLevel установлен → info")
            print("✅ LogLevel установлен → info")
    except Exception as e:
        print("❌ Ошибка при настройке LogLevel:", str(e))
        logging.error(f"❌ Ошибка при настройке LogLevel: {e}")
    print()
    logging.info("")

    # === 5.2 ErrorLog → syslog ===
    print("[5.2] Проверка ErrorLog перенаправления в syslog...")
    logging.info("[5.2] Проверка ErrorLog перенаправления в syslog...")
    errorlog_output, _ = run_command('grep -E -i "^\\s*ErrorLog\\s+\\S+" /etc/apache2/*.conf')
    if "syslog" in errorlog_output:
        print("✅ ErrorLog уже направлен в syslog:", errorlog_output.strip())
        logging.info(f"✅ ErrorLog уже направлен в syslog: {errorlog_output.strip()}")
    else:
        try:
            with open(apache_conf, "a") as f:
                f.write('\nErrorLog "syslog:local1"\n')
            print("✅ ErrorLog перенаправлен в syslog (apache2.conf)")
            logging.info("✅ ErrorLog перенаправлен в syslog (apache2.conf)")
            subprocess.run(["systemctl", "restart", "apache2"], check=False)
            print("🔁 Apache перезапущен")
            logging.info("🔁 Apache перезапущен")
        except Exception as e:
            print("❌ Ошибка при добавлении ErrorLog:", str(e))
            logging.error(f"❌ Ошибка при добавлении ErrorLog: {e}")
    print()
    logging.info("")
    # === 5.3 AccessLog → CEF ===
    print("[5.3] Проверка формата AccessLog (CEF)...")
    logging.info("[5.3] Проверка формата AccessLog (CEF)...")
    cef_check, _ = run_command('grep -ir "logformat" /etc/apache2/')
    if "CEF:" in cef_check:
        print("✅ Найден формат CEF в LogFormat")
        logging.info("✅ Найден формат CEF в LogFormat")
    else:
        try:
            cef_format = '''\nLogFormat "CEF:0|Apache|apache||%>s|%m %U%q|Unknown|end=%{%b %d %Y %H:%M:%S}t app=HTTP cs2=%H suser=%u shost=%h src=%a dhost=%V dpt=%p dproc=apache request=%U requestMethod=%m fname=%f cs1Label=Virtual Host cs1=%v cn1Label=Response Time cn1=%T out=%B cs4Label=Referer cs4=%{Referer}i dvchost=%v dvc=%A deviceProcessName=apache_access_log requestClientApplication=%{User-Agent}i cs3Label=X-Forwarded-For cs3=%{X-Forwarded-For}i" cef\nCustomLog /var/log/apache2/access.log cef\n'''
            with open(apache_conf, "a") as f:
                f.write(cef_format)
            print("✅ CEF формат добавлен в apache2.conf")
            logging.info("✅ CEF формат добавлен в apache2.conf")
            subprocess.run(["systemctl", "restart", "apache2"], check=False)
            print("🔁 Apache перезапущен")
            logging.info("🔁 Apache перезапущен")
        except Exception as e:
            print("❌ Ошибка при добавлении CEF формата:", str(e))
            logging.error(f"❌ Ошибка при добавлении CEF формата: {e}")
    print()
    logging.info("")
    # === 5.4 Ротация логов ===
    print("[5.4] Проверка ротации логов Apache...")
    logging.info("[5.4] Проверка ротации логов Apache...")
    if os.path.isfile(logrotate_path):
        with open(logrotate_path, "r") as f:
            content = f.read()
        if "daily" in content and "rotate 90" in content:
            print("✅ Ротация логов настроена корректно (daily + 90 ротаций)")
            logging.info("✅ Ротация логов настроена корректно (daily + 90 ротаций)")
        else:
            print("❌ Ротация настроена некорректно. Обновляем...")
            logging.warning("❌ Ротация настроена некорректно. Обновляем...")
            try:
                new_rotate = '''/var/log/apache2/*.log {
    daily
    rotate 90
    missingok
    notifempty
    compress
    delaycompress
    sharedscripts
    postrotate
        /etc/init.d/apache2 reload > /dev/null
    endscript
}'''
                with open(logrotate_path, "w") as f:
                    f.write(new_rotate)
                print("✅ Конфигурация ротации логов Apache обновлена")
                logging.info("✅ Конфигурация ротации логов Apache обновлена")
            except Exception as e:
                print("❌ Ошибка при обновлении ротации:", str(e))
                logging.error(f"❌ Ошибка при обновлении ротации: {e}")
    else:
        print("❌ Файл ротации логов Apache не найден:", logrotate_path)
        logging.error(f"❌ Файл ротации логов Apache не найден: {logrotate_path}")
    print("\n=== Проверки логирования завершены ===\n")
    logging.info("\n=== Проверки логирования завершены ===\n")



def read_file(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                content = f.read()
            logging.info(f"Чтение файла: {path}")
            return content
        except Exception as e:
            logging.error(f"Ошибка при чтении файла {path}: {e}")
            return ""
    else:
        logging.warning(f"Файл не найден при чтении: {path}")
        return ""

def write_file(path, content):
    try:
        with open(path, "w") as f:
            f.write(content)
        logging.info(f"Запись файла: {path}")
    except Exception as e:
        logging.error(f"Ошибка при записи файла {path}: {e}")

def replace_or_append(path, directive_start, new_directive, label=""):
    """
    Заменяет строки, начинающиеся с directive_start, на new_directive.
    Если таких строк нет — добавляет new_directive в конец файла.
    """
    if not os.path.exists(path):
        print(f"❌ {label}Файл {path} не найден")
        logging.error(f"{label}Файл не найден: {path}")
        return

    lines = []
    replaced = False
    with open(path, "r") as f:
        for line in f:
            if line.strip().startswith(directive_start):
                if not replaced:
                    lines.append(new_directive + "\n")
                    replaced = True
                    logging.info(f"{label}Заменена директива {directive_start} → {new_directive}")
                # Если несколько строк с этим директивами — пропускаем остальные
            else:
                lines.append(line)
    if not replaced:
        lines.append(new_directive + "\n")
        logging.info(f"{label}Добавлена директива в конец: {new_directive}")

    write_file(path, "".join(lines))
    print(f"✅ {label}Установлено: {new_directive.strip()}")

def insert_into_virtualhost_if_missing(path, directive, label=""):
    """
    Вставляет директиву внутрь блока <VirtualHost *:443>, если её там нет.
    """
    if not os.path.exists(path):
        print(f"❌ {label}Файл {path} не найден")
        logging.error(f"{label}Файл не найден: {path}")
        return

    with open(path, "r") as f:
        content = f.read()

    if directive in content:
        print(f"✅ {label}{directive.strip()} уже присутствует")
        logging.info(f"{label}Директива уже присутствует: {directive.strip()}")
        return

    start = content.find("<VirtualHost *:443>")
    end = content.find("</VirtualHost>", start)
    if start == -1 or end == -1:
        print(f"❌ {label}Блок <VirtualHost *:443> не найден в {path}")
        logging.error(f"{label}Блок <VirtualHost *:443> не найден в {path}")
        return

    new_content = content[:end] + f"\n    {directive}\n" + content[end:]
    write_file(path, new_content)
    print(f"✅ {label}Добавлено в VirtualHost: {directive.strip()}")
    logging.info(f"{label}Добавлено в VirtualHost: {directive.strip()}")

def check_ssl_tls_settings():
    print("=== SSL/TLS Конфигурация ===")
    logging.info("=== SSL/TLS Конфигурация ===")
    apache_conf      = "/etc/apache2/apache2.conf"
    ssl_conf         = "/etc/apache2/mods-available/ssl.conf"
    default_ssl_conf = "/etc/apache2/sites-available/default-ssl.conf"
    private_key_dir  = "/etc/ssl/private"

    # Вспомогательные функции
    def replace_directive(path, prefix, new_line, label=""):
        """
        Заменяет все строки, начинающиеся с prefix, на new_line.
        Если ни одной такой строки нет — добавляет new_line в конец файла.
        """
        if not os.path.exists(path):
            print(f"❌ {label}Файл {path} не найден")
            logging.error(f"{label}Файл {path} не найден")
            return
        lines, replaced = [], False
        with open(path, "r") as f:
            for ln in f:
                if ln.strip().startswith(prefix):
                    if not replaced:
                        lines.append(new_line + "\n")
                        replaced = True
                    # пропускаем остальные
                else:
                    lines.append(ln)
        if not replaced:
            lines.append(new_line + "\n")
        with open(path, "w") as f:
            f.writelines(lines)
        print(f"✅ {label}Установлено: {new_line}")
        logging.info(f"{label}Установлено: {new_line}")

    def insert_into_vhost(path, directive, label=""):
        """
        Вставляет directive внутрь первого блока <VirtualHost *:443>.
        """
        if not os.path.exists(path):
            print(f"❌ Файл {path} не найден")
            logging.error(f"{label}Файл {path} не найден")
            return
        content = open(path).read()
        if directive in content:
            print(f"✅ {directive} уже присутствует в {path}")
            return
        start = content.find("<VirtualHost *:443>")
        end   = content.find("</VirtualHost>", start)
        if start == -1 or end == -1:
            print(f"❌ Не найден блок <VirtualHost *:443> в {path}")
            return
        new_content = content[:end] + f"    {directive}\n" + content[end:]
        with open(path, "w") as f:
            f.write(new_content)
        print(f"✅ Добавлено в VirtualHost: {directive}")
        logging.info(f"{label}Добавлено в VirtualHost: {directive}")
    # 6.1 SSLEngine и сертификаты
    print("[6.1] Проверка SSLEngine и сертификатов...")
    logging.info("[6.1] Проверка SSLEngine и сертификатов...")
    ssl_eng, _ = run_command('grep -R "^\s*SSLEngine" /etc/apache2/ | grep -v "#"')
    cert_f, _  = run_command('grep -R "^\s*SSLCertificateFile" /etc/apache2/ | grep -v "#"')
    key_f, _   = run_command('grep -R "^\s*SSLCertificateKeyFile" /etc/apache2/ | grep -v "#"')
    if "SSLEngine On" in ssl_eng and cert_f and key_f:
        print("✅ SSL Engine и сертификаты уже настроены.")
        logging.info("SSL Engine и сертификаты уже настроены.")
    else:
        print("❌ Исправляю default-ssl.conf...")
        logging.warning("Исправляю default-ssl.conf для настроек SSL")
        if os.path.exists(default_ssl_conf):
            for directive in (
                "SSLEngine On",
                "SSLCertificateFile /etc/ssl/certs/ssl-cert-snakeoil.pem",
                "SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key"
            ):
                insert_into_vhost(default_ssl_conf, directive, "[6.1] ")
            run_command("sudo a2ensite default-ssl.conf")
        else:
            print("❌ default-ssl.conf не найден — SSL не настроен автоматически")
            logging.error("default-ssl.conf не найден — SSL не настроен автоматически")

    # 6.2 Права на приватный ключ
    print("[6.2] Проверка прав на приватный ключ...")
    logging.info("[6.2] Проверка прав на приватный ключ")
    if os.path.isdir(private_key_dir):
        owner, _ = run_command(f"stat -c %U {private_key_dir}")
        group, _ = run_command(f"stat -c %G {private_key_dir}")
        perms, _ = run_command(f"stat -c %a {private_key_dir}")
        if owner=="root" and group=="root" and perms=="400":
            print("✅ Права и владельцы приватного ключа корректны.")
            logging.info("Права и владельцы приватного ключа корректны.")
        else:
            print("❌ Исправляю владельца и права...")
            logging.warning("Исправляю владельца и права приватного ключа")
            run_command(f"sudo chown root:root {private_key_dir} -R")
            run_command(f"sudo chmod 400 {private_key_dir} -R")
    else:
        print("❌ Каталог приватных ключей не найден.")
        logging.error("Каталог приватных ключей не найден.")

    # 6.3 SSLProtocol
    print("[6.3] Настройка SSLProtocol...")
    logging.info("[6.3] Настройка SSLProtocol")
    replace_directive(
        ssl_conf,
        "SSLProtocol",
        "SSLProtocol -all +TLSv1.2 +TLSv1.3",
        "[6.3] "
    )

    # 6.4 Безопасные cipher suites
    print("[6.4] Настройка SSLHonorCipherOrder и SSLCipherSuite...")
    logging.info("[6.4] Настройка SSLHonorCipherOrder и SSLCipherSuite")
    replace_directive(apache_conf,
                      "SSLHonorCipherOrder",
                      "SSLHonorCipherOrder On",
                      "[6.4] ")
    replace_directive(apache_conf,
                      "SSLCipherSuite",
                      "SSLCipherSuite ALL:!EXP:!NULL:!ADH:!LOW:!SSLv2:!SSLv3:!MD5:!RC4:!aNULL:!3DES:!IDEA",
                      "[6.4] ")

    # 6.5 SSLInsecureRenegotiation off
    print("[6.5] Отключение SSLInsecureRenegotiation...")
    logging.info("[6.5] Отключение SSLInsecureRenegotiation")
    replace_directive(apache_conf,
                      "SSLInsecureRenegotiation",
                      "SSLInsecureRenegotiation off",
                      "[6.5] ")

    # 6.6 SSLCompression off
    print("[6.6] Отключение SSLCompression...")
    logging.info("[6.6] Отключение SSLCompression")
    replace_directive(apache_conf,
                      "SSLCompression",
                      "SSLCompression off",
                      "[6.6] ")

    # 6.7 HSTS
    print("[6.7] Включение HSTS...")
    logging.info("[6.7] Включение HSTS")
    insert_into_vhost(default_ssl_conf,
                      'Header always set Strict-Transport-Security "max-age=15678000; includeSubDomains"',
                      "[6.7] ")

    # 6.8 ServerTokens Prod
    print("[6.8] Установка ServerTokens Prod...")
    logging.info("[6.8] Установка ServerTokens Prod")
    replace_directive(apache_conf,
                      "ServerTokens",
                      "ServerTokens Prod",
                      "[6.8] ")

    # 6.9 ServerSignature Off
    print("[6.9] Отключение ServerSignature...")
    logging.info("[6.9] Отключение ServerSignature")
    replace_directive(apache_conf,
                      "ServerSignature",
                      "ServerSignature Off",
                      "[6.9] ")

    # 6.10 FileETag None
    print("[6.10] Настройка FileETag None...")
    logging.info("[6.10] Настройка FileETag None")
    replace_directive(apache_conf,
                      "FileETag",
                      "FileETag None",
                      "[6.10] ")

    print("\n=== Проверки SSL/TLS завершены ===\n")
    logging.info("=== Проверки SSL/TLS завершены ===")

def set_dos_prevention():
    """
    Функция для настройки параметров, предотвращающих отказ в обслуживании.
    Настройки для Timeout, KeepAlive, MaxKeepAliveRequests, KeepAliveTimeout, RequestReadTimeout.
    """

    apache_conf = "/etc/apache2/apache2.conf"

    # Вспомогательная функция для замены или добавления директив в конфигурационные файлы
    def replace_directive(path, prefix, new_line, label=""):
        if not os.path.exists(path):
            print(f"❌ Файл {path} не найден")
            logging.error(f"{label}Файл {path} не найден")
            return
        lines = []
        replaced = False
        with open(path, "r") as f:
            for ln in f:
                if ln.strip().startswith(prefix):
                    if not replaced:
                        lines.append(new_line + "\n")
                        replaced = True
                else:
                    lines.append(ln)
        if not replaced:
            lines.append(new_line + "\n")
        with open(path, "w") as f:
            f.writelines(lines)
        print(f"✅ Установлено: {new_line}")
        logging.info(f"{label}Установлено: {new_line}")
    # 7.1 Директива Timeout
    print("[7.1] Проверка и настройка Timeout...")
    logging.info("[7.1] Проверка и настройка Timeout")
    timeout_setting = "Timeout 20"
    replace_directive(apache_conf, "Timeout", timeout_setting, "[7.1] ")

    # 7.2 Директива KeepAlive
    print("[7.2] Проверка и настройка KeepAlive...")
    logging.info("[7.2] Проверка и настройка KeepAlive")
    keepalive_setting = "KeepAlive On"
    replace_directive(apache_conf, "KeepAlive", keepalive_setting, "[7.2] ")

    # 7.3 Значение MaxKeepAliveRequests
    print("[7.3] Проверка и настройка MaxKeepAliveRequests...")
    logging.info("[7.3] Проверка и настройка MaxKeepAliveRequests")
    max_keepalive_requests = "MaxKeepAliveRequests 100"
    replace_directive(apache_conf, "MaxKeepAliveRequests", max_keepalive_requests, "[7.3] ")

    # 7.4 Значение KeepAliveTimeout
    print("[7.4] Проверка и настройка KeepAliveTimeout...")
    logging.info("[7.4] Проверка и настройка KeepAliveTimeout")
    keepalive_timeout = "KeepAliveTimeout 15"
    replace_directive(apache_conf, "KeepAliveTimeout", keepalive_timeout, "[7.4] ")

    # 7.5 Значение RequestReadTimeout
    print("[7.5] Проверка и настройка RequestReadTimeout...")
    logging.info("[7.5] Проверка и настройка RequestReadTimeout")
    request_read_timeout = "RequestReadTimeout header=20-40,MinRate=500 body=20,MinRate=500"
    replace_directive(apache_conf, "RequestReadTimeout", request_read_timeout, "[7.5] ")

    print("\n=== Меры по предотвращению отказа в обслуживании завершены ===\n")
    logging.info("=== Меры по предотвращению отказа в обслуживании завершены ===")

def set_request_limits():
    """
    Функция для настройки ограничений по запросам в конфигурации Apache.
    Настройки для LimitRequestLine, LimitRequestFields, LimitRequestFieldsize, LimitRequestBody.
    """

    apache_conf = "/etc/apache2/sites-enabled/default-ssl.conf"

    # Вспомогательная функция для замены или добавления директив в конфигурационные файлы
    def replace_directive(path, prefix, new_line, label=""):
        if not os.path.exists(path):
            print(f"❌ Файл {path} не найден")
            logging.error(f"{label}Файл {path} не найден")
            return

        lines = []
        inside_virtualhost = False  # флаг, чтобы отслеживать, находимся ли мы в блоке VirtualHost
        directive_found = False  # флаг для проверки, найдена ли директива

        with open(path, "r") as f:
            for ln in f:
                if "<VirtualHost" in ln:  # если нашли открытие блока VirtualHost
                    inside_virtualhost = True

                if "</VirtualHost>" in ln:  # если нашли закрытие блока VirtualHost
                    inside_virtualhost = False

                # Если находимся в блоке <VirtualHost>, проверяем наличие директивы
                if inside_virtualhost and ln.strip().startswith(prefix):
                    directive_found = True

                lines.append(ln)

        # Если директивы не было в блоке <VirtualHost>, добавляем её
        if not directive_found:
            for i in range(len(lines)):
                if "<VirtualHost" in lines[i]:  # нашли начало блока <VirtualHost>
                    lines.insert(i + 1, new_line + "\n")  # добавляем директиву сразу после этого
                    print(f"✅ Установлено: {new_line}")
                    logging.info(f"{label}Установлено: {new_line}")
                    break
        else:
            print(f"✅ Директива уже существует, пропуск добавления: {new_line}")
            logging.info(f"{label}Директива уже существует: {new_line}")
        # Записываем обратно в конфиг
        with open(path, "w") as f:
            f.writelines(lines)

    # 8.1 Директива LimitRequestLine
    print("[8.1] Проверка и настройка LimitRequestLine...")
    logging.info("[8.1] Проверка и настройка LimitRequestLine")
    limit_request_line = "LimitRequestLine 8190"
    replace_directive(apache_conf, "LimitRequestLine", limit_request_line, "[8.1] ")

    # 8.2 Директива LimitRequestFields
    print("[8.2] Проверка и настройка LimitRequestFields...")
    logging.info("[8.2] Проверка и настройка LimitRequestFields")
    limit_request_fields = "LimitRequestFields 100"
    replace_directive(apache_conf, "LimitRequestFields", limit_request_fields, "[8.2] ")

    # 8.3 Директива LimitRequestFieldsize
    print("[8.3] Проверка и настройка LimitRequestFieldsize...")
    logging.info("[8.3] Проверка и настройка LimitRequestFieldsize")
    limit_request_fieldsize = "LimitRequestFieldsize 49152"
    replace_directive(apache_conf, "LimitRequestFieldsize", limit_request_fieldsize, "[8.3] ")

    # 8.4 Директива LimitRequestBody
    print("[8.4] Проверка и настройка LimitRequestBody...")
    logging.info("[8.4] Проверка и настройка LimitRequestBody")
    limit_request_body = "LimitRequestBody 102400"
    replace_directive(apache_conf, "LimitRequestBody", limit_request_body, "[8.4] ")

    print("\n=== Ограничения по запросам настроены ===\n")
    logging.info("=== Ограничения по запросам настроены ===")

def set_browser_security():
    """
    Функция для настройки заголовков безопасности в конфигурации Apache.
    Настройки для X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy.
    """

    apache_conf = "/etc/apache2/sites-enabled/default-ssl.conf"

    # Вспомогательная функция для замены или добавления директив в конфигурационные файлы
    def replace_directive(path, new_line, label=""):
        if not os.path.exists(path):
            print(f"❌ Файл {path} не найден")
            logging.error(f"{label}Файл {path} не найден")
            return

        lines = []
        inside_virtualhost = False  # флаг, чтобы отслеживать, находимся ли мы в блоке VirtualHost
        directive_found = False  # флаг для проверки, найдена ли директива в блоке

        with open(path, "r") as f:
            for ln in f:
                if "<VirtualHost" in ln:  # если нашли открытие блока VirtualHost
                    inside_virtualhost = True
                if "</VirtualHost>" in ln:  # если нашли закрытие блока VirtualHost
                    inside_virtualhost = False

                # Если находимся в блоке <VirtualHost>, проверяем наличие директивы
                if inside_virtualhost and new_line.strip() in ln:
                    directive_found = True  # Директива уже найдена

                lines.append(ln)

        # Если директивы не было в блоке <VirtualHost>, добавляем её
        if not directive_found:
            for i in range(len(lines)):
                if "<VirtualHost" in lines[i]:  # нашли начало блока <VirtualHost>
                    lines.insert(i + 1, new_line + "\n")  # добавляем директиву сразу после этого
                    print(f"✅ {label}Установлено: {new_line}")
                    logging.info(f"{label}Установлено: {new_line}")
                    break
        else:
            print(f"✅ Директива уже существует, пропуск добавления: {new_line}")
            logging.info(f"{label}Директива уже существует: {new_line}")
        # Записываем обратно в конфиг
        with open(path, "w") as f:
            f.writelines(lines)

    # 9.1 Включение и настройка X-Frame-Options
    print("[9.1] Проверка и настройка X-Frame-Options...")
    logging.info("[9.1] Проверка и настройка X-Frame-Options")
    x_frame_options = "Header always set X-Frame-Options SAMEORIGIN"
    replace_directive(apache_conf, x_frame_options, "[9.1] ")

    # 9.2 Включение и настройка X-Content-Type-Options
    print("[9.2] Проверка и настройка X-Content-Type-Options...")
    logging.info("[9.2] Проверка и настройка X-Content-Type-Options")
    x_content_type_options = "Header always set X-Content-Type-Options nosniff"
    replace_directive(apache_conf, x_content_type_options, "[9.2] ")

    # 9.3 Включение и настройка X-XSS-Protection
    print("[9.3] Проверка и настройка X-XSS-Protection...")
    logging.info("[9.3] Проверка и настройка X-XSS-Protection")
    x_xss_protection = 'Header always set X-XSS-Protection "1; mode=block"'
    replace_directive(apache_conf, x_xss_protection, "[9.3] ")

    # 9.4 Включение и настройка Referrer-Policy
    print("[9.4] Проверка и настройка Referrer-Policy...")
    logging.info("[9.4] Проверка и настройка Referrer-Policy")
    referrer_policy = 'Header always set Referrer-Policy "no-referrer"'
    replace_directive(apache_conf, referrer_policy, "[9.4] ")

    print("\n=== Безопасность браузера настроена ===\n")
    logging.info("=== Безопасность браузера настроена ===")



def restart_apache():
    output, code = run_command("sudo systemctl restart apache2")
    if code != 0:
        print("❌ Ошибка при перезапуске apache2!")
        logging.error(f"Ошибка при перезапуске apache2: {output}")
        print("Вывод:", output)
        return False

    # Проверяем статус после рестарта
    status_output, status_code = run_command("sudo systemctl is-active apache2")
    if status_code == 0 and status_output.strip() == "active":
        print("✅ Apache успешно перезапущен и работает.")
        logging.info("Apache успешно перезапущен и работает.")
        return True
    else:
        print("❌ Apache не запущен после перезапуска!")
        logging.error(f"Apache не запущен после перезапуска, статус: {status_output.strip()}")
        print("Статус:", status_output)
        # Подсмотреть последние ошибки в логах
        logs, _ = run_command("sudo tail -n 10 /var/log/apache2/error.log")
        print("Последние строки лога ошибок Apache:\n", logs)
        logging.error(f"Последние строки лога ошибок Apache:\n{logs}")
        return False

def main():
    print("=== Проверка и настройка модулей Apache для www-data ===")
    logging.info("=== Проверка и настройка модулей Apache для www-data ===")
    # 1.1 — auth и ldap
    loaded_modules = run_command("apachectl -M")[0].splitlines()
    print("[1.1] Проверка модулей авторизации (auth) и ldap")
    logging.info("[1.1] Проверка модулей авторизации (auth) и ldap")
    auth_mods = [line.strip() for line in loaded_modules if "auth" in line]
    ldap_mods = [line.strip() for line in loaded_modules if "ldap" in line]
    print("Активные модули auth:")
    if auth_mods:
        for mod in auth_mods:
            print(" ", mod)
            logging.info(f"Активный модуль auth: {mod}")
    else:
        print(" (нет)")
        logging.info("Нет активных модулей auth")
    if not ldap_mods:
        print("Активных модулей ldap не найдено")
        logging.info("Нет активных модулей ldap")
    else:
        print("Активные модули ldap:")
        for mod in ldap_mods:
            print(" ", mod)
            logging.info(f"Активный модуль ldap: {mod}")
    print("При необходимости отключить неиспользуемые модули через a2dismod\n")
    logging.info("Запуск check_module_item для модулей 1.2–1.11")
    check_module_item("1.2", "Модуль log_config ВКЛЮЧЕН", module="log_config_module", should_be_enabled=True)
    check_module_item("1.3", "Модуль WebDAV ОТКЛЮЧЕН", module="dav_module", should_be_enabled=False)
    check_module_item("1.4", "Модуль mod_status ОТКЛЮЧЕН", module="status_module", should_be_enabled=False,
                      disable_func=lambda: run_command("sudo a2dismod status"))
    check_module_item("1.5", "Модуль autoindex_module ОТКЛЮЧЕН", module="autoindex_module", should_be_enabled=False,
                      disable_func=lambda: run_command("sudo a2dismod autoindex -f"), force_disable=True)
    check_module_item("1.6", "Модули proxy_* ОТКЛЮЧЕНЫ", prefix="proxy_", should_be_enabled=False)
    check_module_item("1.7", "Модуль userdir ОТКЛЮЧЕН", prefix="userdir_", should_be_enabled=False)
    check_module_item("1.8", "Модуль mod_info ОТКЛЮЧЕН", module="info_module", should_be_enabled=False)
    check_module_item("1.9", "Модули mod_auth_digest ОТКЛЮЧЕНЫ", module="auth_digest_module", should_be_enabled=False)
    check_module_item("1.10", "Модули mod_auth_basic ОТКЛЮЧЕНЫ", module="auth_basic_module", should_be_enabled=False,
                      disable_func=lambda: run_command("sudo a2dismod auth_basic -f"), force_disable=True)
    check_module_item("1.11", "Модуль mod_ssl ВКЛЮЧЕН", module="ssl_module", should_be_enabled=True,
                      enable_func=lambda: (run_command("sudo a2enmod ssl"),
                                          run_command("sudo a2ensite default-ssl.conf")))

    logging.info("Включаем модуль headers")
    subprocess.run(["sudo", "a2enmod", "headers"], check=True)
    logging.info("Запуск check_permissions")
    check_permissions()
    logging.info("Запуск check_access_controls")
    check_access_controls()
    logging.info("Запуск check_and_apply_minimization")
    check_and_apply_minimization()
    logging.info("Запуск check_logging_settings")
    check_logging_settings()
    logging.info("Запуск check_ssl_tls_settings")
    check_ssl_tls_settings()
    logging.info("Запуск set_dos_prevention")
    set_dos_prevention()
    logging.info("Запуск set_request_limits")
    set_request_limits()
    logging.info("Запуск set_browser_security")
    set_browser_security()
    logging.info("Перезагрузка Apache")
    restart_apache()
if __name__ == "__main__":
    main()
