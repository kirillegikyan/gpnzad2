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

def suppress_ah00558_warning():
    try:
        conf_path = "/etc/apache2/conf-available/servername.conf"
        with open(conf_path, "w") as f:
            f.write("ServerName localhost\n")
        subprocess.run(["a2enconf", "servername"], check=True)
        subprocess.run(["systemctl", "reload", "apache2"], check=True)
        print("✅ Установлен ServerName localhost — предупреждение AH00558 устранено")
        logging.info("ServerName localhost установлен")
    except Exception as e:
        print("⚠️ Не удалось установить ServerName localhost")
        logging.error(f"Ошибка при установке ServerName: {e}")

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

    suppress_ah00558_warning()

    logging.info("=== Настройка завершена ===")
    print(f"\n✅ Настройка завершена. Лог: {LOG_FILE}")
    print("ℹ️ Не забудь перезапустить Apache: sudo systemctl restart apache2")

if __name__ == "__main__":
    main()
