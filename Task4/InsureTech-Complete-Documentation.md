# InsureTech Architecture - Полная документация

## Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Core App Web API](#core-app-web-api)
3. [OSAGO Aggregator API](#osago-aggregator-api)
4. [Решения по интеграции сервисов](#решения-по-интеграции-сервисов)
5. [Паттерны отказоустойчивости](#паттерны-отказоустойчивости)
6. [Архитектурные решения](#архитектурные-решения)

---

## Обзор архитектуры

InsureTech представляет собой микросервисную архитектуру для страховой платформы с event-driven подходом и встроенными паттернами отказоустойчивости.

### Основные компоненты:
- **core-app** (3 экз.) - Центральный сервис бизнес-логики
- **ins-product-aggregator** (3 экз.) - Агрегатор страховых продуктов
- **osago-aggregator** (3 экз.) - Специализированный агрегатор ОСАГО
- **client-info** (3 экз.) - Сервис клиентских данных
- **ins-comp-settlement** (3 экз.) - Сервис взаиморасчетов

### Системы хранения данных:
- **core-db** - PostgreSQL для основных данных
- **osago-aggregator-db** - PostgreSQL для ОСАГО с регуляторными требованиями
- **client-info-db** - PostgreSQL для клиентских данных
- **ins-comp-settlement-db** - PostgreSQL для взаиморасчетов

### Event-driven архитектура:
- **Apache Kafka Cluster** - Центральная платформа для событий
- **Schema Registry** - Управление схемами событий
- **Event Store** - Audit trail и compliance
- **Debezium CDC** - Change Data Capture через Outbox pattern
- **Stream Processing** - Real-time обработка с Kafka Streams

---

## Core App Web API

### Обзор API

Core-app предоставляет REST API для веб-приложения (React) с операциями по управлению страховыми продуктами.

**Базовый URL:** `/api/v1/web`
**Протокол:** REST API + WebSocket для real-time уведомлений
**Формат данных:** JSON
**Аутентификация:** JWT Bearer Token

### Основные операции

#### 1. Аутентификация и авторизация

```http
POST /api/v1/web/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Ответ:**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "refresh_token_here",
    "user": {
      "id": "user-123",
      "email": "user@example.com",
      "name": "Иван Петров",
      "role": "CLIENT"
    },
    "expiresIn": 3600
  }
}
```

#### 2. Получение страховых продуктов

```http
GET /api/v1/web/products
Authorization: Bearer {token}
Query Parameters:
  - category: osago|casco|life|property
  - region: 77
  - vehicleType: car|motorcycle|truck
```

**Ответ:**
```json
{
  "success": true,
  "data": {
    "products": [
      {
        "id": "product-osago-123",
        "type": "OSAGO",
        "name": "ОСАГО Базовый",
        "description": "Обязательное страхование автогражданской ответственности",
        "provider": "osago-aggregator",
        "minPremium": 3500.0,
        "maxCoverage": 500000.0,
        "available": true,
        "features": [
          "Покрытие ущерба до 500,000 руб",
          "Европротокол",
          "24/7 поддержка"
        ]
      }
    ]
  }
}
```

#### 3. Расчет стоимости страховки

```http
POST /api/v1/web/calculate
Content-Type: application/json
Authorization: Bearer {token}

{
  "productType": "OSAGO",
  "vehicle": {
    "vin": "XTA21124050123456",
    "registrationNumber": "А123БВ777"
  },
  "drivers": [
    {
      "licenseNumber": "77 АА 123456",
      "birthDate": "1985-03-15"
    }
  ],
  "period": {
    "startDate": "2024-01-15",
    "duration": 12
  }
}
```

#### 4. Создание заявки на полис

```http
POST /api/v1/web/policies
Content-Type: application/json
Authorization: Bearer {token}

{
  "calculationId": "calc-web-789",
  "selectedOffer": "sberins",
  "personalData": {
    "firstName": "Иван",
    "lastName": "Петров",
    "passport": {
      "series": "4509",
      "number": "123456"
    }
  },
  "contactData": {
    "phone": "+7 905 123-45-67",
    "email": "ivan.petrov@example.com"
  }
}
```

#### 5. WebSocket для real-time уведомлений

```javascript
// Подключение к WebSocket
const ws = new WebSocket('wss://api.insuretech.com/ws/notifications');

ws.onmessage = function(event) {
  const notification = JSON.parse(event.data);
  // Обработка уведомлений
};

// Примеры уведомлений:
{
  "type": "POLICY_STATUS_UPDATED",
  "data": {
    "policyId": "policy-123",
    "status": "ISSUED",
    "message": "Ваш полис ОСАГО готов к скачиванию"
  }
}
```

---

## OSAGO Aggregator API

### Обзор API

osago-aggregator предоставляет REST API для core-app с операциями по обязательному страхованию автогражданской ответственности (ОСАГО).

**Базовый URL:** `/api/v1/osago`
**Протокол:** REST API + Rate Limiting + Circuit Breaker
**Формат данных:** JSON
**Аутентификация:** Bearer Token / API Key

### Основные операции

#### 1. Расчет стоимости ОСАГО

```http
POST /api/v1/osago/calculate
Content-Type: application/json
Authorization: Bearer {token}

{
  "vehicle": {
    "vin": "XTA21124050123456",
    "registrationNumber": "А123БВ777",
    "make": "LADA",
    "model": "Vesta",
    "year": 2022,
    "enginePower": 106,
    "category": "B"
  },
  "drivers": [
    {
      "licenseNumber": "77 АА 123456",
      "birthDate": "1985-03-15",
      "licenseDate": "2010-06-20",
      "experience": 13
    }
  ],
  "policy": {
    "startDate": "2024-01-15",
    "duration": 12,
    "isLimitedDrivers": true,
    "region": "77",
    "usage": "personal"
  }
}
```

**Ответ:**
```json
{
  "success": true,
  "data": {
    "calculationId": "calc-123456789",
    "basePremium": 4118.0,
    "coefficients": {
      "territorialCoefficient": 2.0,
      "bonusMalusCoefficient": 0.95,
      "ageExperienceCoefficient": 1.0,
      "powerCoefficient": 1.1,
      "seasonalCoefficient": 1.0,
      "driverLimitCoefficient": 1.0
    },
    "totalPremium": 8595.58,
    "validUntil": "2024-01-15T14:30:00Z",
    "insuranceCompanies": [
      {
        "id": "sberins",
        "name": "СберСтрахование",
        "premium": 8595.58,
        "discount": 0,
        "available": true
      }
    ]
  }
}
```

#### 2. Проверка VIN номера

```http
GET /api/v1/osago/vehicle/vin/{vin}/info
Authorization: Bearer {token}
```

#### 3. Проверка водительского удостоверения

```http
GET /api/v1/osago/driver/license/{license}/info
Authorization: Bearer {token}
```

#### 4. Создание заявки на полис

```http
POST /api/v1/osago/policy/create
Content-Type: application/json
Authorization: Bearer {token}

{
  "calculationId": "calc-123456789",
  "selectedCompany": "sberins",
  "policyholder": {
    "type": "individual",
    "firstName": "Иван",
    "lastName": "Петров",
    "patronymic": "Сергеевич",
    "birthDate": "1985-03-15",
    "passport": {
      "series": "4509",
      "number": "123456",
      "issueDate": "2005-04-10",
      "issuedBy": "ОУФМС России по г. Москве"
    }
  }
}
```

#### 5. Получение статуса заявки

```http
GET /api/v1/osago/policy/application/{applicationId}/status
Authorization: Bearer {token}
```

### Особенности реализации OSAGO API

#### Rate Limiting
- **100 расчетов/минуту** на клиента
- **10 заявок/минуту** на создание полисов
- **1000 запросов/минуту** на информационные endpoint'ы

#### Circuit Breaker
- Открывается при **60%+ ошибок** за 1 минуту
- **Fallback**: кешированные данные из osago-aggregator-db
- **Recovery**: проверка через 30 секунд

#### Кеширование
- **Коэффициенты**: 1 час
- **VIN данные**: 24 часа
- **Водительские данные**: 6 часов
- **Тарифы компаний**: 30 минут

#### Аудит и соответствие РСА
Все операции логируются в osago-aggregator-db для соответствия требованиям Российского Союза Автостраховщиков.

---

## Решения по интеграции сервисов

### Выбор средств интеграции по типам взаимодействий

#### 1. REST API (Синхронные интеграции)

**Применение:**
- **Web UI ↔ core-app**: Пользовательские операции (CRUD операции с полисами, клиентами)
- **core-app ↔ client-info**: Получение/обновление клиентских данных
- **core-app ↔ ins-product-aggregator**: Получение продуктов и тарифов
- **core-app ↔ osago-aggregator**: Получение продуктов ОСАГО и управление полисами
- **Партнеры → core-app**: API для создания заявок на страхование
- **core-app → Платежный сервис**: Инициация платежных операций

**Обоснование выбора:**
- Простота реализации и отладки
- Широкая поддержка инструментами
- Подходит для операций request-response
- Хорошая совместимость с Spring Boot

#### 2. Apache Kafka Events (Асинхронные интеграции)

**Применение:**
- **Policy Events**: Создание, обновление, отмена полисов
- **Customer Events**: Регистрация, верификация клиентов
- **Claim Events**: Подача и обработка страховых требований
- **Risk Events**: Оценка рисков и fraud detection
- **Notification Events**: Уведомления клиентам
- **Audit Events**: Логирование для соответствия требованиям

**Обоснование выбора:**
- Высокая пропускная способность для больших объемов
- Гарантии доставки и порядка сообщений
- Replay возможности для восстановления
- Горизонтальная масштабируемость

#### 3. GraphQL API (Гибкие интеграции)

**Применение:**
- **ins-product-aggregator ↔ Некоторые современные страховые компании**
- **Web UI → Backend aggregation layer** (будущее развитие)

**Обоснование выбора:**
- Более эффективная передача данных (только нужные поля)
- Снижение количества запросов
- Лучше для сложных запросов к продуктовым каталогам

#### 4. gRPC (Высокопроизводительные интеграции)

**Применение:**
- **core-app ↔ ins-comp-settlement**: Высокочастотные операции взаиморасчетов
- **Внутренние сервисы с высокими требованиями к производительности**

**Обоснование выбора:**
- Более высокая производительность чем REST
- Строгая типизация через Protocol Buffers
- Би-директional streaming для real-time операций
- Лучше для внутренних интеграций

#### 5. WebSockets (Real-time коммуникация)

**Применение:**
- **Web UI ↔ core-app**: Real-time уведомления пользователям
- **Статус обработки заявок**: Живые обновления статуса
- **Чат поддержки**: Интеграция с системой поддержки

**Обоснование выбора:**
- Мгновенные уведомления без polling
- Снижение нагрузки на сервер
- Лучший user experience

---

## Паттерны отказоустойчивости

### Rate Limiting

#### Где применить:
1. **Публичные API endpoints для партнеров**
   - Лимит: 1000 запросов/минуту на партнера
   - Защита от злоупотреблений и DDoS

2. **Внешние страховые API**
   - Лимит: согласно SLA страховой компании
   - Предотвращение превышения квот

3. **Платежный сервис**
   - Лимит: 10 платежей/минуту на клиента
   - Защита от случайного дублирования

4. **OSAGO Aggregator API**
   - Лимит: 100 расчетов/минуту на клиента
   - Лимит: 10 заявок/минуту на создание полисов
   - Лимит: 1000 информационных запросов/минуту

#### Реализация:
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: partners-api
          uri: http://core-app
          filters:
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 1000
                redis-rate-limiter.burstCapacity: 2000
```

### Circuit Breaker

#### Где применить:
1. **core-app → ins-product-aggregator**
   - При недоступности агрегатора продуктов
   - Fallback: Кэшированные данные продуктов

2. **ins-product-aggregator → Страховые компании API**
   - При сбоях внешних систем
   - Fallback: Последние известные тарифы

3. **core-app → osago-aggregator**
   - При недоступности ОСАГО агрегатора
   - Fallback: Кешированные тарифы ОСАГО из БД

4. **osago-aggregator → РСА API**
   - При сбоях API Российского Союза Автостраховщиков
   - Fallback: Локально кешированные данные

5. **core-app → Платежный сервис**
   - При недоступности платежной системы
   - Fallback: Отложенная обработка платежей

#### Реализация:
```java
@Component
public class InsuranceProductService {

    @CircuitBreaker(name = "insurance-products", fallbackMethod = "getCachedProducts")
    @TimeLimiter(name = "insurance-products")
    public CompletableFuture<List<Product>> getProducts() {
        return productAggregator.fetchProducts();
    }

    public CompletableFuture<List<Product>> getCachedProducts(Exception ex) {
        return CompletableFuture.completedFuture(productCache.getLastKnownProducts());
    }
}
```

### Retry

#### Где применить:
1. **Kafka Producers**
   - При временных сбоях брокеров
   - Exponential backoff с jitter

2. **Database операции**
   - При deadlocks или временной недоступности
   - Максимум 3 попытки

3. **HTTP вызовы к внешним API**
   - При сетевых ошибках (5xx, timeouts)
   - Максимум 3 попытки с увеличивающейся задержкой

#### Реализация:
```java
@Retryable(
    value = {DataAccessException.class},
    maxAttempts = 3,
    backoff = @Backoff(delay = 1000, multiplier = 2)
)
public Policy savePolicy(Policy policy) {
    return policyRepository.save(policy);
}
```

### Timeout

#### Где применить:
1. **HTTP клиенты**
   - Connect timeout: 5 секунд
   - Read timeout: 30 секунд

2. **Database запросы**
   - Query timeout: 60 секунд для сложных запросов
   - Connection timeout: 10 секунд

3. **Kafka operations**
   - Producer timeout: 30 секунд
   - Consumer poll timeout: 5 секунд

#### Реализация:
```yaml
spring:
  datasource:
    hikari:
      connection-timeout: 10000
      validation-timeout: 5000
  kafka:
    producer:
      acks: all
      retries: 3
      request-timeout-ms: 30000
```

---

## Архитектурные решения

### Учет множественных экземпляров сервисов

#### Влияние множественных экземпляров на паттерны отказоустойчивости

**Rate Limiting с множественными экземплярами:**
- **Проблема**: Лимиты должны быть общими для всех экземпляров сервиса
- **Решение**: Centralized Rate Limiting через Redis
- **Реализация**: Shared counter в Redis для всех экземпляров core-app, ins-product-aggregator, osago-aggregator

**Circuit Breaker с множественными экземплярами:**
- **Проблема**: Состояние Circuit Breaker должно быть синхронизировано
- **Решение**: Shared state в Redis или Hazelcast
- **Реализация**: Все 3 экземпляра каждого сервиса проверяют общее состояние

**Retry с множественными экземплярами:**
- **Проблема**: Retry может попасть на тот же неработающий экземпляр
- **Решение**: Load Balancer исключает неработающие экземпляры
- **Реализация**: Health checks + automatic failover

**Timeout с множественными экземплярами:**
- **Проблема**: Разные экземпляры могут иметь разную производительность
- **Решение**: Единые timeout настройки для всех экземпляров
- **Реализация**: Централизованная конфигурация через Config Server

### Load Balancing

#### Kubernetes Service:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: core-app-service
spec:
  selector:
    app: core-app
  ports:
    - port: 8080
      targetPort: 8080
  type: ClusterIP
  sessionAffinity: ClientIP  # Для sticky sessions если нужно
```

### Health Checks

#### Liveness и Readiness Probes:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: core-app
spec:
  template:
    spec:
      containers:
      - name: core-app
        livenessProbe:
          httpGet:
            path: /actuator/health/liveness
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /actuator/health/readiness
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Архитектура баз данных

#### Специализированные БД по доменам:

1. **core-db (PostgreSQL)**
   - **Назначение**: Центральная БД для тарифов страховых компаний и заявок клиентов
   - **Связи**: core-app (3 экземпляра)
   - **Паттерны**: JDBC connection pooling, database timeouts

2. **ins-comp-settlement-db (PostgreSQL)**
   - **Назначение**: Данные о взаиморасчетах со страховыми компаниями
   - **Связи**: ins-comp-settlement (3 экземпляра)
   - **Паттерны**: gRPC + Retry + Timeout для высокопроизводительных операций

3. **client-info-db (PostgreSQL)**
   - **Назначение**: Клиентские данные (ФИО, телефон, паспорт)
   - **Связи**: client-info (3 экземпляра)
   - **Паттерны**: REST API + Circuit Breaker для надежности

4. **osago-aggregator-db (PostgreSQL)**
   - **Назначение**:
     - Кеширование ОСАГО тарифов для быстрого ответа
     - Хранение VIN номеров и водительских данных
     - Регуляторное логирование для соответствия требованиям РСА
     - Fallback данные при недоступности внешних API
   - **Связи**: osago-aggregator (3 экземпляра)
   - **Паттерны**: JDBC + Connection Pooling
   - **Специфика**: Соответствие требованиям Российского Союза Автостраховщиков

### Event-driven архитектура

#### Kafka Consumer Groups:
```java
@KafkaListener(
    topics = "policy-events",
    groupId = "policy-processing-group",
    containerFactory = "kafkaListenerContainerFactory"
)
public void handlePolicyEvent(@Payload PolicyEvent event,
                             @Header("kafka_receivedPartitionId") int partition) {
    // Обработка с учетом партиции для ordering гарантий
}
```

#### Service Discovery:
```yaml
eureka:
  client:
    service-url:
      defaultZone: http://eureka-server:8761/eureka
  instance:
    health-check-url-path: /actuator/health
    status-page-url-path: /actuator/info
```

### Мониторинг и наблюдаемость

#### Ключевые метрики:
- **REST API**: Response time, error rate, throughput
- **Kafka**: Consumer lag, producer throughput, error rate
- **Circuit Breakers**: Open/closed state, failure rate
- **Rate Limiting**: Throttled requests, quota usage

#### Алерты:
- API response time > 5 секунд
- Consumer lag > 1000 сообщений
- Circuit breaker open > 5 минут
- Error rate > 5%

#### Трассировка:
- **Zipkin/Jaeger** для distributed tracing
- **Correlation IDs** для связывания запросов
- **MDC logging** для контекстной информации

### Безопасность

#### JWT токены:
- Короткое время жизни (1 час)
- Refresh токены для обновления сессии
- Rate Limiting: 1000 запросов/час на пользователя
- CORS настройки для фронтенд домена

#### Валидация:
- Входящие данные: строгая валидация схем JSON
- Бизнес-правила: проверка возраста, стажа, региона
- Безопасность: XSS и SQL injection защита

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Некорректные данные запроса |
| 401 | Неавторизованный доступ |
| 403 | Доступ запрещен |
| 404 | Данные не найдены |
| 409 | Конфликт (например, полис уже существует) |
| 422 | Ошибка валидации данных |
| 429 | Превышен лимит запросов (Rate Limiting) |
| 500 | Внутренняя ошибка сервера |
| 503 | Сервис временно недоступен (Circuit Breaker) |

---

## Заключение

Данная архитектура обеспечивает:

1. **Масштабируемость**: Горизонтальное масштабирование через множественные экземпляры сервисов
2. **Отказоустойчивость**: Комплексные паттерны защиты от сбоев
3. **Производительность**: Оптимизированные протоколы интеграции
4. **Соответствие требованиям**: Регуляторное соответствие для страховой индустрии
5. **Наблюдаемость**: Полный мониторинг и трассировка операций
6. **Безопасность**: Многоуровневая защита данных и API

Архитектура готова к промышленному использованию и соответствует современным стандартам разработки микросервисных систем.