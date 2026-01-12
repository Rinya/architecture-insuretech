# Настройка HPA для scaletestapp

## Описание

Данная конфигурация настраивает динамическое масштабирование приложения scaletestapp на основе утилизации оперативной памяти.

## Файлы конфигурации

- `scaletestapp-deployment.yaml` - Deployment приложения
- `scaletestapp-service.yaml` - Service для доступа к приложению
- `scaletestapp-hpa.yaml` - HPA для автомасштабирования

## Параметры HPA

- **Целевая утилизация памяти**: 80%
- **Минимальное количество реплик**: 1
- **Максимальное количество реплик**: 10
- **Политика масштабирования вверх**: до 100% увеличения каждые 15 сек или максимум 2 пода за 60 сек
- **Политика масштабирования вниз**: максимум 10% уменьшения каждые 60 сек с периодом стабилизации 5 минут

## Предварительные требования

Убедитесь, что в кластере установлен metrics-server:

```bash
# Проверить наличие metrics-server
kubectl get deployment metrics-server -n kube-system

# Если metrics-server не установлен, установить его:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

## Применение конфигурации

```bash
# Применить все манифесты
kubectl apply -f .

# Или по отдельности:
kubectl apply -f scaletestapp-deployment.yaml
kubectl apply -f scaletestapp-service.yaml
kubectl apply -f scaletestapp-hpa.yaml
```

## Мониторинг HPA

```bash
# Проверить статус HPA
kubectl get hpa scaletestapp-hpa

# Подробная информация об HPA
kubectl describe hpa scaletestapp-hpa

# Мониторинг в реальном времени
kubectl get hpa scaletestapp-hpa --watch

# Проверить метрики подов
kubectl top pods -l app=scaletestapp
```

## Тестирование автомасштабирования

Для проверки работы HPA можно создать нагрузку на приложение:

```bash
# Перенаправить порт для доступа к приложению
kubectl port-forward service/scaletestapp-service 8080:8080

# В другом терминале создать нагрузку
# Пример скрипта для создания нагрузки на память:
while true; do
  curl -s http://localhost:8080/health > /dev/null
  curl -s http://localhost:8080/id > /dev/null
done
```

## Ожидаемое поведение

1. При утилизации памяти выше 80% HPA будет увеличивать количество подов
2. При снижении нагрузки HPA будет постепенно уменьшать количество подов
3. Количество подов всегда будет в диапазоне от 1 до 10