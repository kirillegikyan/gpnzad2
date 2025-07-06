
print('hello world!')
import json
import subprocess
from datetime import datetime

# Загрузка правил из файла
with open("rules.json", "r", encoding="utf-8") as f:
    rules = json.load(f)

log_file = "log.txt"

def write_log(message):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - {message}\n")

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def main():
    write_log("=== Запуск проверки правил ===")
    for i, rule in enumerate(rules, 1):
        header = f"[{i}] {rule['id']} {rule['sub_id']}: {rule['description']}"
        print(header)
        write_log(header)
        success = False

        for cmd in rule["commands"]:
            stdout, stderr, code = run_command(cmd)
            write_log(f"  Команда: {cmd}")
            write_log(f"  stdout: {stdout}")
            if stderr:
                write_log(f"  stderr: {stderr}")
            if code == 0 and stdout:
                success = True
                break

        if success:
            msg = "  Условие выполнено. Переход к следующему правилу."
            print(msg)
            write_log(msg)
        else:
            msg = f"  Условие не выполнено. Возможное исправление: {rule['fix']}"
            print(msg)
            write_log(msg)
        print()

    write_log("=== Проверка завершена ===")

if __name__ == "__main__":
    main()
