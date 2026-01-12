# Решение о применении Transactional Outbox паттерна в Event-Driven архитектуре InsureTech

## Исполнительное резюме

**РЕШЕНИЕ: ДА, применить Transactional Outbox паттерн во всех критических микросервисах InsureTech системы**

Данное решение обосновано критической важностью консистентности данных в страховой системе, регулятивными требованиями к аудиту операций и необходимостью обеспечения ACID свойств для финансовых транзакций.

---

## Анализ требований

### Предметная область InsureTech

Страховая система InsureTech включает следующие критические бизнес-процессы:

1. **Policy Management** - создание, изменение, продление, отмена полисов
2. **Customer Onboarding** - регистрация, верификация, KYC процедуры
3. **Claims Processing** - подача, обработка, одобрение/отклонение требований
4. **Risk Assessment** - оценка рисков, динамическое ценообразование
5. **Payment Processing** - платежи, биллинг, взаиморасчеты
6. **Regulatory Compliance** - аудит, отчетность, соответствие требованиям

### Критические требования

#### 1. Консистентность данных (ACID)
- **Atomicity**: Операции с полисами должны быть атомарными
- **Consistency**: Состояние системы должно быть всегда валидным
- **Isolation**: Параллельные операции не должны влиять друг на друга
- **Durability**: Подтвержденные операции должны быть постоянными

#### 2. Регулятивные требования
- **SOX (Sarbanes-Oxley)**: Аудит всех финансовых операций
- **GDPR**: Отслеживание обработки персональных данных
- **PCI DSS**: Безопасность платежных операций
- **Insurance Regulatory**: Отчетность перед страховыми регуляторами

#### 3. Бизнес-критические SLA
- **Policy Creation Time**: < 2 минут end-to-end
- **Claim Processing**: < 24 часа для standard claims
- **Risk Assessment**: < 5 секунд для pricing
- **Data Consistency**: 100% для финансовых операций

---

## Анализ паттернов Event-Driven архитектуры

### Альтернативы Transactional Outbox

#### 1. Dual Writes
```java
// НЕПОДХОДЯЩИЙ подход для InsureTech
@Transactional
public void createPolicy(Policy policy) {
    policyRepository.save(policy);
    kafkaProducer.send("policy-events", policyCreatedEvent); // ⚠️ НЕ транзакционно
}
```
**Проблемы**:
- Нет гарантий доставки события при сбое Kafka
- Возможна потеря событий при partial failures
- НЕДОПУСТИМО для страховых операций

#### 2. Database Triggers
```sql
-- Автоматическая публикация событий через DB triggers
CREATE TRIGGER policy_events_trigger
AFTER INSERT OR UPDATE ON policies
FOR EACH ROW EXECUTE FUNCTION publish_policy_event();
```
**Проблемы**:
- Tight coupling между DB и messaging system
- Сложность обработки ошибок Kafka
- Ограниченные возможности для retry logic

#### 3. Transactional Outbox (РЕКОМЕНДУЕТСЯ)
```java
@Transactional
public void createPolicy(Policy policy) {
    Policy savedPolicy = policyRepository.save(policy);
    OutboxEvent event = new OutboxEvent(
        "Policy",
        savedPolicy.getId(),
        "PolicyCreated",
        policyCreatedEventData
    );
    outboxRepository.save(event); // ✅ В той же транзакции
}
```
**Преимущества**:
- Гарантированная консистентность данных
- Надежная доставка событий
- Audit trail из коробки
- Возможность replay событий

---

## Архитектурное решение

### Компоненты Transactional Outbox

#### 1. Outbox Table Structure

```sql
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP,
    failure_reason TEXT,

    -- Для обеспечения ordering
    sequence_number BIGSERIAL,

    -- Для deduplication
    idempotency_key VARCHAR(255) UNIQUE,

    -- Для partitioning в больших системах
    partition_key VARCHAR(100),

    -- Индексы для оптимальной производительности
    INDEX idx_outbox_unprocessed (created_at) WHERE processed_at IS NULL,
    INDEX idx_outbox_aggregate (aggregate_type, aggregate_id, sequence_number),
    INDEX idx_outbox_retry (next_retry_at) WHERE processed_at IS NULL AND next_retry_at IS NOT NULL,
    INDEX idx_outbox_partition (partition_key, created_at)
);
```

#### 2. Service Implementation Pattern

```java
@Service
@Transactional
public class PolicyService {

    private final PolicyRepository policyRepository;
    private final OutboxEventRepository outboxRepository;
    private final PolicyEventMapper eventMapper;

    public PolicyCreatedResult createPolicy(CreatePolicyCommand command) {
        // 1. Валидация бизнес-правил
        validatePolicyRules(command);

        // 2. Создание основной сущности
        Policy policy = new Policy(command);
        policy.calculatePremium();
        policy.setStatus(PolicyStatus.DRAFT);

        Policy savedPolicy = policyRepository.save(policy);

        // 3. Создание события в той же транзакции
        PolicyCreatedEvent eventData = eventMapper.toEvent(savedPolicy);
        OutboxEvent outboxEvent = OutboxEvent.builder()
            .aggregateType("Policy")
            .aggregateId(savedPolicy.getId().toString())
            .eventType("PolicyCreated")
            .eventData(JsonUtils.toJson(eventData))
            .eventVersion(1)
            .idempotencyKey(command.getIdempotencyKey())
            .partitionKey(savedPolicy.getCustomerId().toString())
            .build();

        outboxRepository.save(outboxEvent);

        return PolicyCreatedResult.success(savedPolicy);
    }

    // Аналогично для update, cancel и других операций
}
```

#### 3. Debezium CDC Configuration

```json
{
    "name": "policy-outbox-connector",
    "config": {
        "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
        "database.hostname": "policy-db.internal",
        "database.port": "5432",
        "database.user": "debezium",
        "database.password": "${vault:policy-db-password}",
        "database.dbname": "policy_service",
        "database.server.name": "policy-service",

        "table.include.list": "public.outbox_events",
        "tombstones.on.delete": "false",

        "transforms": "outbox",
        "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
        "transforms.outbox.table.field.event.type": "event_type",
        "transforms.outbox.table.field.event.id": "id",
        "transforms.outbox.table.field.event.key": "aggregate_id",
        "transforms.outbox.route.topic.replacement": "policy-events",

        "producer.max.request.size": "1048576",
        "producer.compression.type": "snappy",
        "producer.enable.idempotence": "true"
    }
}
```

---

## Сервисы требующие Transactional Outbox

### 1. Policy Management Service (Критический приоритет)

**События**:
- `PolicyCreated` - новый полис создан
- `PolicyUpdated` - изменения условий полиса
- `PolicyRenewed` - продление полиса
- `PolicyCancelled` - отмена полиса
- `PolicyActivated` - активация после оплаты

**Критичность**: ВЫСОКАЯ
**Обоснование**: Финансовые операции, регулятивные требования

### 2. Customer Service (Высокий приоритет)

**События**:
- `CustomerRegistered` - новый клиент
- `CustomerVerified` - прошел KYC
- `CustomerUpdated` - изменение данных
- `CustomerSuspended` - блокировка аккаунта

**Критичность**: ВЫСОКАЯ
**Обоснование**: GDPR compliance, персональные данные

### 3. Claims Processing Service (Критический приоритет)

**События**:
- `ClaimSubmitted` - подача требования
- `ClaimInvestigated` - расследование начато
- `ClaimApproved` - одобрено к выплате
- `ClaimRejected` - отклонено
- `ClaimPaid` - выплата произведена

**Критичность**: КРИТИЧЕСКАЯ
**Обоснование**: Финансовые выплаты, fraud prevention

### 4. Risk Assessment Service (Средний приоритет)

**События**:
- `RiskCalculated` - оценка завершена
- `RiskThresholdExceeded` - превышен лимит
- `FraudDetected` - обнаружена подозрительная активность

**Критичность**: СРЕДНЯЯ
**Обоснование**: Не финансовые операции, но важны для pricing

### 5. Payment Service (Критический приоритет)

**События**:
- `PaymentInitiated` - платеж начат
- `PaymentCompleted` - платеж успешен
- `PaymentFailed` - платеж не прошел
- `RefundProcessed` - возврат выполнен

**Критичность**: КРИТИЧЕСКАЯ
**Обоснование**: PCI DSS compliance, финансовые операции

---

## Преимущества для InsureTech домена

### 1. Регулятивное соответствие

```sql
-- Полный audit trail всех операций
SELECT
    oe.created_at,
    oe.aggregate_type,
    oe.aggregate_id,
    oe.event_type,
    oe.event_data->>'userId' as user_id,
    oe.event_data->>'amount' as amount
FROM outbox_events oe
WHERE oe.aggregate_type = 'Policy'
    AND oe.created_at BETWEEN '2024-01-01' AND '2024-12-31'
ORDER BY oe.created_at;
```

### 2. Disaster Recovery

```sql
-- Replay событий после сбоя
SELECT * FROM outbox_events
WHERE created_at > '2024-01-15 10:30:00'
    AND aggregate_type IN ('Policy', 'Claim', 'Payment')
ORDER BY sequence_number;
```

### 3. Business Intelligence

```sql
-- Аналитика по созданию полисов
SELECT
    DATE(created_at) as day,
    COUNT(*) as policies_created,
    SUM((event_data->>'premium')::decimal) as total_premium
FROM outbox_events
WHERE event_type = 'PolicyCreated'
    AND created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY day;
```

---

## Операционные рекомендации

### 1. Мониторинг и алерты

```yaml
outbox_monitoring:
  metrics:
    - name: "outbox_unprocessed_events"
      query: "SELECT COUNT(*) FROM outbox_events WHERE processed_at IS NULL"
      threshold: 1000
      alert_level: "warning"

    - name: "outbox_processing_lag"
      query: "SELECT EXTRACT(EPOCH FROM NOW() - MIN(created_at)) FROM outbox_events WHERE processed_at IS NULL"
      threshold: 300  # 5 minutes
      alert_level: "critical"

    - name: "outbox_failed_events"
      query: "SELECT COUNT(*) FROM outbox_events WHERE retry_count >= max_retries"
      threshold: 10
      alert_level: "high"

  dashboards:
    - "Outbox Events Processing Rate"
    - "Event Type Distribution"
    - "Processing Latency by Service"
    - "Failed Events Trend"
```

### 2. Очистка старых событий

```sql
-- Автоматическая очистка через 7 лет (regulatory requirement)
DELETE FROM outbox_events
WHERE processed_at IS NOT NULL
    AND processed_at < NOW() - INTERVAL '7 years'
    AND aggregate_type NOT IN ('Policy', 'Claim'); -- Критические типы храним дольше

-- Архивирование в cold storage
INSERT INTO outbox_events_archive
SELECT * FROM outbox_events
WHERE processed_at < NOW() - INTERVAL '1 year';
```

### 3. Performance optimization

```sql
-- Partitioning по времени для больших таблиц
CREATE TABLE outbox_events_y2024m01 PARTITION OF outbox_events
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Параллельная обработка по partition_key
CREATE INDEX CONCURRENTLY idx_outbox_partition_processing
ON outbox_events (partition_key, created_at)
WHERE processed_at IS NULL;
```

---

## Риски и митигация

### 1. Производительность Outbox таблицы
**Риск**: Большой объем событий замедляет работу
**Митигация**:
- Partitioning по времени
- Регулярная архивация старых событий
- Асинхронная обработка с batch processing

### 2. Дублирование событий
**Риск**: At-least-once semantics Kafka создают дубли
**Митигация**:
- Idempotency keys для deduplication
- Идемпотентные event handlers
- Consumer-side deduplication

### 3. Schema evolution
**Риск**: Изменения схем событий ломают consumers
**Митигация**:
- Schema Registry с backward compatibility
- Event versioning в outbox
- Graceful degradation для unknown events

### 4. Dead letter queues
**Риск**: Накопление failed events
**Митигация**:
- Automated retry с exponential backoff
- Manual intervention procedures
- Alert system для критических failures

---

## Заключение

Применение Transactional Outbox паттерна в InsureTech системе обосновано:

1. **Критическими требованиями к консистентности данных** в финансовой сфере
2. **Регулятивными требованиями** к аудиту и отслеживанию операций
3. **Бизнес-критическими SLA** для обработки полисов и требований
4. **Необходимостью надежной доставки событий** для всех участников системы

Реализация должна включать comprehensive monitoring, automated cleanup procedures и disaster recovery capabilities для обеспечения enterprise-grade reliability.

**Следующие шаги**:
1. Внедрение в Policy Management Service (приоритет 1)
2. Расширение на Claims Processing Service (приоритет 2)
3. Интеграция с Customer Service (приоритет 3)
4. Полная миграция всех критических сервисов (6 месяцев)