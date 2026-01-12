# Инструкции по нагрузочному тестированию с Locust

## Установка Locust

### Вариант 1: Через pip
```powershell
pip install locust
```

### Вариант 2: Через pip3
```powershell
pip3 install locust
```

### Вариант 3: Через Python модуль
```powershell
python -m pip install locust
```

### Вариант 4: С виртуальным окружением
```powershell
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Установить Locust
pip install locust
```

## Подготовка к тестированию

### 1. Применить все манифесты Kubernetes
```bash
kubectl apply -f scaletestapp-deployment.yaml
kubectl apply -f scaletestapp-service.yaml
kubectl apply -f scaletestapp-hpa.yaml
```

### 2. Настроить port-forward для доступа к приложению
```bash
# В отдельном терминале запустить port-forward
kubectl port-forward service/scaletestapp-service 8080:8080
```

### 3. Проверить доступность приложения
```bash
# Проверить health endpoint
curl http://localhost:8080/health

# Проверить id endpoint
curl http://localhost:8080/id
```

## Запуск нагрузочного тестирования

### В PowerShell:

```powershell
# Перейти в папку Task2
cd architecture-insuretech\Task2

# Запустить Locust
locust

# Или если не работает, через Python модуль:
python -m locust
```

### Параметры веб-интерфейса Locust:

1. Откройте браузер и перейдите на http://localhost:8089
2. Настройте параметры:
   - **Number of users**: 10-50 (начните с малого)
   - **Spawn rate**: 5-10 users per second
   - **Host**: http://localhost:8080 (должно быть уже заполнено)
3. Нажмите "Start swarming"

### Альтернативный запуск из командной строки:

```powershell
# Запуск без веб-интерфейса
locust --headless --users 20 --spawn-rate 5 --run-time 5m

# С логированием
locust --headless --users 50 --spawn-rate 10 --run-time 10m --logfile locust.log
```

## Мониторинг автомасштабирования

### В отдельном терминале следите за HPA:
```bash
# Мониторинг HPA в реальном времени
kubectl get hpa scaletestapp-hpa --watch

# Мониторинг подов
kubectl get pods -l app=scaletestapp --watch

# Просмотр использования ресурсов
kubectl top pods -l app=scaletestapp
```

### Просмотр логов приложения:
```bash
# Логи текущих подов
kubectl logs -f deployment/scaletestapp

# Логи конкретного пода
kubectl logs -f <pod-name>
```

## Ожидаемое поведение

1. **Начальное состояние**: 1 реплика
2. **При нагрузке**: когда утилизация памяти превысит 80%, HPA начнет создавать новые реплики
3. **Масштабирование**: количество подов будет увеличиваться до максимум 10
4. **После снижения нагрузки**: HPA постепенно уменьшит количество подов обратно к 1

## Полезные команды для отладки

```bash
# Проверить статус metrics-server
kubectl get deployment metrics-server -n kube-system

# Подробная информация об HPA
kubectl describe hpa scaletestapp-hpa

# События в кластере
kubectl get events --sort-by=.metadata.creationTimestamp

# Проверить лимиты ресурсов подов
kubectl describe pod -l app=scaletestapp
```

## Устранение проблем

### Если HPA не масштабирует:
1. Убедитесь, что metrics-server работает
2. Проверьте, что у подов установлены `requests` для памяти
3. Подождите несколько минут - HPA проверяет метрики каждые 15-60 секунд

### Если Locust не запускается:
1. Проверьте установку: `pip list | grep locust`
2. Проверьте версию Python: `python --version`
3. Попробуйте переустановить: `pip uninstall locust && pip install locust`

### Если приложение недоступно:
1. Проверьте port-forward: `kubectl port-forward service/scaletestapp-service 8080:8080`
2. Проверьте статус подов: `kubectl get pods -l app=scaletestapp`
3. Проверьте service: `kubectl get service scaletestapp-service`