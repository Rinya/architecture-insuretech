from locust import HttpUser, between, task

class ScaleTestAppUser(HttpUser):
    wait_time = between(0.5, 2)  # Более короткие интервалы для создания нагрузки

    # URL приложения (нужно будет изменить на реальный адрес после port-forward)
    host = "http://localhost:8080"

    @task(3)  # Вес 3 - будет выполняться чаще
    def health_check(self):
        """Проверка состояния приложения"""
        self.client.get("/health")

    @task(2)  # Вес 2
    def get_pod_id(self):
        """Получение идентификатора пода"""
        self.client.get("/id")

    @task(1)  # Вес 1 - будет выполняться реже
    def stress_memory(self):
        """Создание дополнительной нагрузки для тестирования утилизации памяти"""
        # Делаем несколько быстрых запросов подряд
        for i in range(5):
            self.client.get("/health")
            self.client.get("/id")