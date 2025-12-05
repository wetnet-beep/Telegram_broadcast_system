# -*- coding: utf-8 -*-
"""
МОДУЛЬ ДЛЯ СКАЧИВАНИЯ ФАЙЛОВ С GITHUB
"""
import requests
import os
import zipfile
import io
from typing import Optional, List

class GitHubDownloader:
    """Класс для работы с GitHub API и скачивания файлов"""
    
    def __init__(self, token: str = None):
        """
        Инициализация загрузчика
        
        Args:
            token: GitHub Personal Access Token
        """
        self.token = token
        self.headers = {
            'Authorization': f'token {token}' if token else None,
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def download_repo(self, repo_url: str, output_dir: str = "downloaded_repo") -> str:
        """
        Скачать весь репозиторий
        
        Args:
            repo_url: Ссылка на репозиторий (формат: user/repo)
            output_dir: Папка для сохранения
            
        Returns:
            Путь к скачанному репозиторию
        """
        print(f"📥 Скачивание репозитория: {repo_url}")
        
        # Формируем URL для скачивания zip-архива
        if "github.com" in repo_url:
            repo_url = repo_url.split("github.com/")[-1].replace(".git", "")
        
        zip_url = f"https://api.github.com/repos/{repo_url}/zipball/main"
        
        try:
            # Скачиваем архив
            response = requests.get(zip_url, headers=self.headers if self.headers['Authorization'] else {})
            response.raise_for_status()
            
            # Создаем папку для сохранения
            os.makedirs(output_dir, exist_ok=True)
            
            # Распаковываем архив
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                zip_file.extractall(output_dir)
                extracted_folder = zip_file.namelist()[0].split('/')[0]
                full_path = os.path.join(output_dir, extracted_folder)
            
            print(f"✅ Репозиторий скачан: {full_path}")
            return full_path
            
        except Exception as e:
            print(f"❌ Ошибка при скачивании: {e}")
            return ""
    
    def download_file(self, repo_url: str, file_path: str, output_path: str) -> bool:
        """
        Скачать конкретный файл из репозитория
        
        Args:
            repo_url: Ссылка на репозиторий
            file_path: Путь к файлу в репозитории
            output_path: Куда сохранить файл
            
        Returns:
            True если успешно
        """
        try:
            # Получаем содержимое файла
            api_url = f"https://api.github.com/repos/{repo_url}/contents/{file_path}"
            response = requests.get(api_url, headers=self.headers if self.headers['Authorization'] else {})
            response.raise_for_status()
            
            data = response.json()
            
            # Декодируем base64 если это файл
            if data.get('encoding') == 'base64':
                import base64
                content = base64.b64decode(data['content'])
            else:
                content = data['content'].encode('utf-8')
            
            # Сохраняем файл
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(content)
            
            print(f"✅ Файл скачан: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при скачивании файла: {e}")
            return False
    
    def get_repo_files(self, repo_url: str, path: str = "") -> List[str]:
        """
        Получить список файлов в репозитории
        
        Args:
            repo_url: Ссылка на репозиторий
            path: Путь внутри репозитория
            
        Returns:
            Список файлов
        """
        try:
            api_url = f"https://api.github.com/repos/{repo_url}/contents/{path}"
            response = requests.get(api_url, headers=self.headers if self.headers['Authorization'] else {})
            response.raise_for_status()
            
            files = []
            for item in response.json():
                if item['type'] == 'file':
                    files.append(item['path'])
                elif item['type'] == 'dir':
                    files.extend(self.get_repo_files(repo_url, item['path']))
            
            return files
            
        except Exception as e:
            print(f"❌ Ошибка при получении файлов: {e}")
            return []
    
    def download_from_code_input(self, code_input: str, output_file: str = "downloaded_code.py") -> bool:
        """
        Скачать файл по введенному коду/ссылке
        
        Args:
            code_input: Код/ссылка от пользователя
            output_file: Куда сохранить
            
        Returns:
            True если успешно
        """
        # Если это прямая ссылка на raw файл
        if "raw.githubusercontent.com" in code_input:
            try:
                response = requests.get(code_input)
                response.raise_for_status()
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                print(f"✅ Файл скачан по прямой ссылке: {output_file}")
                return True
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                return False
        
        # Если это ссылка на репозиторий
        elif "github.com" in code_input:
            # Пытаемся извлечь user/repo из ссылки
            parts = code_input.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                repo = f"{parts[0]}/{parts[1]}"
                return self.download_repo(repo, "downloads")
        
        # Если это user/repo формат
        elif "/" in code_input and "." not in code_input:
            return self.download_repo(code_input, "downloads")
        
        # Если это код напрямую
        else:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(code_input)
                print(f"✅ Код сохранен как: {output_file}")
                return True
            except Exception as e:
                print(f"❌ Ошибка сохранения: {e}")
                return False
        
        return False

# Пример использования
if __name__ == "__main__":
    downloader = GitHubDownloader()
    
    # Пример 1: Скачать весь репозиторий
    # downloader.download_repo("username/repository")
    
    # Пример 2: Скачать конкретный файл
    # downloader.download_file("username/repo", "path/to/file.py", "local_file.py")
    
    # Пример 3: Скачать по введенному коду
    user_input = input("Введите код/ссылку: ")
    downloader.download_from_code_input(user_input)
