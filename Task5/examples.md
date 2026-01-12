# Примеры использования GraphQL API для сервиса client-info

## Сравнение REST vs GraphQL

### Проблема с REST API

При использовании текущего REST API для получения полной информации о клиенте требуется **3 отдельных HTTP запроса**:

```http
GET /v1/clients/123
GET /v1/clients/123/documents
GET /v1/clients/123/relatives
```

Это приводит к:
- Увеличению нагрузки на сервис
- Замедлению работы приложения
- Сложности синхронизации данных

### Решение с GraphQL

С GraphQL все данные можно получить **одним запросом**:

## Примеры GraphQL запросов

### 1. Получение всех данных клиента (замена 3 REST вызовов)

```graphql
query GetCompleteClientInfo($clientId: ID!) {
  client(id: $clientId) {
    id
    name
    age
    documents {
      id
      type
      number
      issueDate
      expiryDate
    }
    relatives {
      id
      relationType
      name
      age
    }
  }
}

# Переменные
{
  "clientId": "123"
}
```

**Результат:**
```json
{
  "data": {
    "client": {
      "id": "123",
      "name": "Иван Петров",
      "age": 35,
      "documents": [
        {
          "id": "doc1",
          "type": "Паспорт",
          "number": "1234 567890",
          "issueDate": "2015-01-15",
          "expiryDate": "2025-01-15"
        },
        {
          "id": "doc2",
          "type": "Водительские права",
          "number": "77 01 123456",
          "issueDate": "2020-03-10",
          "expiryDate": "2030-03-10"
        }
      ],
      "relatives": [
        {
          "id": "rel1",
          "relationType": "Супруга",
          "name": "Мария Петрова",
          "age": 32
        },
        {
          "id": "rel2",
          "relationType": "Сын",
          "name": "Александр Петров",
          "age": 8
        }
      ]
    }
  }
}
```

### 2. Выборочная загрузка данных

**Сценарий:** Нужна только базовая информация о клиенте и его документы (без родственников)

```graphql
query GetClientWithDocuments($clientId: ID!) {
  client(id: $clientId) {
    name
    age
    documents {
      type
      expiryDate
    }
  }
}
```

**Преимущество:** Загружаются только нужные поля, что экономит трафик и ускоряет ответ.

### 3. Минимальный запрос для проверки статуса

**Сценарий:** Нужно проверить, существует ли клиент и какого он возраста

```graphql
query CheckClientAge($clientId: ID!) {
  client(id: $clientId) {
    age
  }
}
```

**Результат:**
```json
{
  "data": {
    "client": {
      "age": 35
    }
  }
}
```

### 4. Загрузка списка клиентов с выборочными данными

```graphql
query GetClientsOverview {
  clients {
    id
    name
    age
    documents {
      type
    }
  }
}
```

### 5. Отдельные запросы для совместимости с REST

Если нужна обратная совместимость, можно использовать отдельные запросы:

```graphql
# Эквивалент GET /clients/{id}/documents
query GetClientDocuments($clientId: ID!) {
  clientDocuments(clientId: $clientId) {
    id
    type
    number
    issueDate
    expiryDate
  }
}

# Эквивалент GET /clients/{id}/relatives
query GetClientRelatives($clientId: ID!) {
  clientRelatives(clientId: $clientId) {
    id
    relationType
    name
    age
  }
}
```

## Оптимизация производительности

### Сравнение нагрузки на сервис

| Сценарий | REST API | GraphQL | Экономия |
|----------|----------|---------|----------|
| Полная информация о клиенте | 3 запроса | 1 запрос | **66%** |
| Только документы | 1 запрос | 1 запрос | 0% |
| Клиент + документы | 2 запроса | 1 запрос | **50%** |
| 10 клиентов с документами | 20 запросов | 1 запрос | **95%** |

### Примеры мутаций для расширения функциональности

```graphql
# Обновление информации о клиенте
mutation UpdateClient($id: ID!, $input: ClientInput!) {
  updateClient(id: $id, input: $input) {
    id
    name
    age
  }
}

# Добавление нового документа
mutation AddDocument($clientId: ID!, $input: DocumentInput!) {
  addDocument(clientId: $clientId, input: $input) {
    id
    type
    number
    issueDate
    expiryDate
  }
}

# Переменные для добавления документа
{
  "clientId": "123",
  "input": {
    "type": "Полис ОМС",
    "number": "1234567890123456",
    "issueDate": "2024-01-01",
    "expiryDate": "2025-01-01"
  }
}
```

## Ключевые преимущества GraphQL решения

1. **Снижение RPS на 66%** для типичных сценариев получения полной информации о клиенте
2. **Гибкость запросов** - возможность получать только нужные поля
3. **Единая точка входа** для всех операций с данными клиента
4. **Типизация** и автодокументирование API
5. **Обратная совместимость** с существующими паттернами доступа к данным
6. **Расширяемость** - легко добавлять новые поля без версионирования API

## Рекомендации по внедрению

1. **Поэтапная миграция:** Начать с наиболее часто используемых запросов
2. **Кеширование:** Использовать DataLoader паттерн для оптимизации N+1 проблем
3. **Мониторинг:** Отслеживать сложность запросов для предотвращения DDoS атак
4. **Аутентификация:** Интегрировать с существующей системой JWT токенов