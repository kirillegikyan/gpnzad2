#!/usr/bin/env python3
import subprocess
import logging
import os
import shutil
from pathlib import Path

def get_apachectl_command():
    for cmd in ['apache2ctl', 'apachectl']:
        path = shutil.which(cmd) or f"/usr/sbin/{cmd}"
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    raise FileNotFoundError("Не найдена команда apachectl или apache2ctl")

APACHECTL = get_apachectl_command()
SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "apache_module_check.log"

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s %(message)s')

modules_required = {
    'log_config': True,
    'dav_': False,
    'status_module': False,
    'autoindex_module': False,
    'proxy_': False,
    'userdir': False,
    'info_module': False,
    'auth_digest_module': False,
    'auth_basic_module': False,
    'ssl_module': True,
}

mod_actions = {
    'status_module': ['a2dismod', 'status'],
    'autoindex_module': ['a2dismod', 'autoindex', '-f'],
    'auth_basic_module': ['a2dismod', 'auth_basic', '-f'],
    'ssl_module': [
        ['a2enmod', 'ssl'],
        ['a2ensite', 'default-ssl.conf']
    ],
}

# 🔍 Проверка модуля
def check_module(mod_pattern):
    try:
        result = subprocess.run([APACHECTL, '-M'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return any(mod_pattern in line for line in result.stdout.splitlines())
    except Exception as e:
        logging.error(f"Ошибка при проверке модуля {mod_pattern}: {e}")
        return None

def execute_command(cmd):
    try:
        subprocess.run(cmd, check=True)
        logging.info(f"✅ Выполнена команда: {' '.join(cmd)}")
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Ошибка при выполнении команды: {' '.join(cmd)} — {e}")

# 🔧 Проверка неиспользуемых auth*/ldap модулей
def disable_unused_auth_modules():
    try:
        result = subprocess.run([APACHECTL, '-M'], stdout=subprocess.PIPE, text=True)
        lines = result.stdout.splitlines()
        active_modules = [line.strip().split()[0] for line in lines if 'auth_' in line or 'ldap' in line]
        allowed_auth_modules = ['auth_basic_module', 'auth_digest_module']
        for mod in active_modules:
            if not any(allowed in mod for allowed in allowed_auth_modules):
                mod_name = mod.replace('_module', '')
                print(f"🔻 Отключение неиспользуемого модуля: {mod_name}")
                logging.info(f"Отключение неразрешённого auth/ldap модуля: {mod_name}")
                execute_command(['a2dismod', mod_name])
    except Exception as e:
        logging.error(f"Ошибка при отключении auth/ldap модулей: {e}")

# 🔧 Проверка, от какого пользователя работает Apache
def check_apache_user():
    try:
        result = subprocess.run(['ps', 'axo', 'user,comm'], stdout=subprocess.PIPE, text=True)
        users = set()
        for line in result.stdout.splitlines():
            if 'apache2' in line or 'httpd' in line:
                user = line.strip().split()[0]
                users.add(user)

        if 'root' in users:
            users.discard('root')
        if len(users) == 1:
            user = users.pop()
            print(f"✅ Apache работает от сервисного пользователя: {user}")
            logging.info(f"Apache работает от пользователя: {user}")
        else:
            print(f"⚠️ Обнаружены процессы Apache под разными пользователями: {users}")
            logging.warning(f"Несколько пользователей Apache: {users}")
    except Exception as e:
        print("❌ Ошибка при проверке пользователя Apache")
        logging.error(f"Ошибка при проверке пользователя Apache: {e}")

# 🔧 Проверка безопасной конфигурации
def check_system_hardening():
    try:
        with open("/etc/passwd") as f:
            for line in f:
                if "www-data" in line and "/sbin/nologin" in line:
                    print("✅ www-data использует /sbin/nologin")
                    break
            else:
                print("❌ www-data не использует /sbin/nologin")
    except Exception as e:
        logging.error(f"Ошибка в 2.2: {e}")

    try:
        with open("/etc/shadow") as f:
            for line in f:
                if line.startswith("www-data:"):
                    if line.split(":")[1].startswith("!"):
                        print("✅ Учётка www-data заблокирована")
                    else:
                        print("❌ Учётка www-data НЕ заблокирована — исправляем...")
                        execute_command(['usermod', '-L', 'www-data'])
                    break
    except Exception as e:
        logging.error(f"Ошибка в 2.3: {e}")

    for path in ['/etc/apache2', '/usr/share/apache2']:
        try:
            result = subprocess.run(['find', path, '!', '-user', 'root'], stdout=subprocess.PIPE, text=True)
            if result.stdout.strip():
                print(f"⚠️ Некорректный владелец в {path}, исправляем...")
                subprocess.run(['chown', 'root:root', '-R', path])
            else:
                print(f"✅ Все файлы в {path} принадлежат root")
        except Exception as e:
            logging.error(f"Ошибка в 2.4: {e}")

    try:
        subprocess.run(['chmod', '755', '-R', '/etc/apache2'])
        print("✅ Права 755 на /etc/apache2")
    except Exception as e:
        logging.error(f"Ошибка в 2.5: {e}")

    try:
        u = subprocess.run(['stat', '-c', '%U', '/var/log/apache2'], stdout=subprocess.PIPE, text=True).stdout.strip()
        g = subprocess.run(['stat', '-c', '%G', '/var/log/apache2'], stdout=subprocess.PIPE, text=True).stdout.strip()
        p = subprocess.run(['stat', '-c', '%a', '/var/log/apache2'], stdout=subprocess.PIPE, text=True).stdout.strip()
        if u != 'root' or g != 'www-data' or p != '660':
            print("⚠️ /var/log/apache2 имеет неверные владельцы/права, исправляем...")
            subprocess.run(['chown', 'root:www-data', '-R', '/var/log/apache2'])
            subprocess.run(['chmod', '660', '-R', '/var/log/apache2'])
        else:
            print("✅ /var/log/apache2 настроен корректно")
    except Exception as e:
        logging.error(f"Ошибка в 2.6: {e}")

    try:
        pidfile = '/run/apache2/apache2.pid'
        u = subprocess.run(['stat', '-c', '%U', pidfile], stdout=subprocess.PIPE, text=True).stdout.strip()
        g = subprocess.run(['stat', '-c', '%G', pidfile], stdout=subprocess.PIPE, text=True).stdout.strip()
        p = subprocess.run(['stat', '-c', '%a', pidfile], stdout=subprocess.PIPE, text=True).stdout.strip()
        if u != 'root' or g != 'root' or p != '644':
            print("⚠️ PID-файл имеет неверные владельцы/права, исправляем...")
            subprocess.run(['chown', 'root:root', pidfile])
            subprocess.run(['chmod', '644', pidfile])
        else:
            print("✅ PID-файл корректен")
    except Exception as e:
        logging.error(f"Ошибка в 2.8: {e}")

# 🔧 Проверка ScoreBoardFile (п.2.9)
def check_scoreboard_file():
    print("\n🔍 Проверка ScoreBoardFile (п.2.9)")
    result = subprocess.run("grep -r 'ScoreBoardFile' /etc/apache2/*.conf", shell=True, stdout=subprocess.PIPE, text=True)
    if result.stdout:
        lines = result.stdout.splitlines()
        for line in lines:
            path = line.split(":")[0]
            stat_u = subprocess.run(f"stat -c %U {path}", shell=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            stat_g = subprocess.run(f"stat -c %G {path}", shell=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            if stat_u == "root" and stat_g == "root":
                print(f"✅ ScoreBoardFile: {path} принадлежит root:root")
            else:
                print(f"❌ ScoreBoardFile: {path} — устанавливаем владельца root:root")
                subprocess.run(f"chown root:root {path}", shell=True)
    else:
        print("ℹ️ ScoreBoardFile не найден в конфигурации")

# 🔧 Проверка прав на запись для group
def check_group_write_perm():
    print("\n🔍 Проверка прав на запись для group (п.2.10)")
    result = subprocess.run("find /etc/apache2 -perm /g=w -ls | grep -v 'lrwxrwxrwx'", shell=True, stdout=subprocess.PIPE, text=True)
    if result.stdout:
        print("❌ Обнаружены права group на запись — исправляем...")
        subprocess.run("chmod -R g-w /etc/apache2", shell=True)
    else:
        print("✅ Права на запись для group ограничены")

# 🔧 Проверка ограничений на доступ к веб-контенту (п.3.2)
def check_access_control():
    print("\n🔍 Проверка ограничений на доступ к веб-контенту (п.3.2)")

    # Читаем конфигурацию
    conf_path = "/etc/apache2/apache2.conf"
    
    with open(conf_path, "r") as f:
        config = f.read()

    # Проверяем, существует ли блок <Location /portal>
    if "<Location /portal>" not in config:
        print("❌ Блок <Location /portal> не найден. Добавляем его...")
        with open(conf_path, "a") as f:
            f.write("\n<Location /portal>\n    Require valid-user\n</Location>\n")
        print("✅ Добавлен блок <Location /portal> с директивой Require valid-user.")
    else:
        # Проверяем, если в блоке <Location /portal> уже есть требуемая директива
        if "Require valid-user" not in config.split("<Location /portal>")[1].split("</Location>")[0]:
            # Если нет, добавляем директиву
            with open(conf_path, "a") as f:
                f.write("\n<Location /portal>\n    Require valid-user\n</Location>\n")
            print("✅ Добавлено ограничение Require valid-user в <Location /portal>")
        else:
            print("ℹ️ Ограничение Require valid-user уже присутствует в конфигурации.")
def remove_allow_override_list():
    print("\n🔍 Проверка и удаление директивы AllowOverrideList (п.3.3)")
    
    # Проверяем, есть ли директива AllowOverrideList в конфигурационных файлах
    result = subprocess.run("grep -r 'AllowOverrideList' /etc/apache2/*.conf", shell=True, stdout=subprocess.PIPE, text=True)
    
    if result.stdout:
        print("❌ Найдена директива AllowOverrideList — удаляем её...")
        
        # Получаем все файлы конфигурации
        config_files = result.stdout.splitlines()
        
        for file in config_files:
            file_path = file.split(":")[0]
            
            # Открываем файл и удаляем строки с AllowOverrideList
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            with open(file_path, 'w') as f:
                for line in lines:
                    if "AllowOverrideList" not in line:
                        f.write(line)
            
            print(f"✅ Директива AllowOverrideList удалена из {file_path}")
        
        # Перезагружаем Apache, чтобы изменения вступили в силу
       
    else:
        print("✅ AllowOverrideList отсутствует в конфигурации.")

# 🛠 Функция для подавления предупреждения AH00558
def suppress_ah00558_warning():
    try:
        # Путь к конфигурационному файлу для установки ServerName
        conf_path = "/etc/apache2/conf-available/servername.conf"
        
        # Проверяем, существует ли уже конфигурация ServerName
        if not os.path.exists(conf_path):
            # Если не существует, создаем конфигурацию
            with open(conf_path, "w") as f:
                f.write("ServerName localhost\n")
            subprocess.run(["a2enconf", "servername"], check=True)
            subprocess.run(["systemctl", "reload", "apache2"], check=True)
            print("✅ Установлен ServerName localhost — предупреждение AH00558 устранено")
            logging.info("ServerName localhost установлен")
        else:
            print("✅ ServerName уже установлен — предупреждение AH00558 устранено")
    except Exception as e:
        print("⚠️ Не удалось установить ServerName localhost")
        logging.error(f"Ошибка при установке ServerName: {e}")

# 🛠 Функция для перезагрузки Apache с использованием полного пути systemctl
def restart_apache():
    systemctl_path = shutil.which("systemctl")  # Находит полный путь к systemctl
    if systemctl_path:
        subprocess.run([systemctl_path, "restart", "apache2"], check=True)
        print("ℹ️ Apache перезагружен для применения изменений")
    else:
        print("❌ systemctl не найден в системе")
# 🔧 Проверка директивы AllowOverrideList (п.3.3)

def main():
    print("🔧 Настройка Apache модулей...")
    logging.info("=== Запуск настройки Apache ===")

    disable_unused_auth_modules()

    for mod, should_be_enabled in modules_required.items():
        is_enabled = check_module(mod)
        if is_enabled is None:
            continue

        status = "включён" if is_enabled else "отключён"
        expected = "включён" if should_be_enabled else "отключён"

        if is_enabled == should_be_enabled:
            print(f"✅ {mod} уже {status}")
        else:
            print(f"⚠️ {mod} сейчас {status}, нужно: {expected}")
            actions = mod_actions.get(mod)
            if actions:
                if isinstance(actions[0], list):
                    for act in actions:
                        execute_command(act)
                else:
                    execute_command(actions)
            else:
                cmd = ['a2enmod', mod] if should_be_enabled else ['a2dismod', mod]
                execute_command(cmd)

    print("\n🔍 Проверка пользователя Apache (п.2.1)")
    check_apache_user()

    print("\n🔐 Проверка безопасной конфигурации (п.2.2 – 2.8)")
    check_system_hardening()

    # **Добавление проверок 3.1-3.3**
    check_scoreboard_file()
    check_group_write_perm()
    check_access_control()  # Проверка доступа к директориям ОС
    remove_allow_override_list()

    suppress_ah00558_warning()

    logging.info("=== Настройка завершена ===")
    print(f"\n✅ Настройка завершена. Лог: {LOG_FILE}")
    print("ℹ️ Не забудь перезагрузить Apache вручную, если скрипт не сделал это автоматически.")
    restart_apache()  # Перезагружаем Apache только в конце


if __name__ == "__main__":
    main()
