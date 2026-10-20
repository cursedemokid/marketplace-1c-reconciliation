"""Представление результата и трассировка значений до исходных строк."""

from .engine import Run


def report_sheets(run: Run) -> dict[str, list[tuple]]:
    summary = [
        ('Параметр', 'Значение'),
        ('Набор данных', 'ДЕМОНСТРАЦИЯ — искусственные данные' if run.demo else 'Реальные источники НЕ ПОДКЛЮЧЕНЫ'),
        ('Запуск', run.run_id), ('Создан UTC', run.created_at), ('Режим', run.selected.mode),
        ('Начало', run.selected.start.isoformat()), ('Конец', run.selected.end.isoformat()),
        ('Версия правил', 'demo-v1' if run.demo else 'draft-v2 — не утверждены'),
        ('Статус', run.status), ('Сравнений', len(run.comparisons)),
        ('Расхождений', sum(r.status == 'расхождение' for r in run.comparisons)),
        ('Знак', 'Левая сторона минус правая; для реальных данных не утверждён'),
        ('Точность', 'Все значения сохранены текстом без округления и потери десятичных знаков'),
    ]
    comparisons = [('Период', 'Показатель', 'Организация', 'Кабинет', 'Сегмент', 'Валюта', 'Единица',
                    'Левый источник', 'Правый источник', 'Слева', 'Справа', 'Разница', 'Статус',
                    'Исходные строки слева', 'Исходные строки справа', 'Примечание')]
    for row in run.comparisons:
        key = row.key
        comparisons.append((key.bucket, key.metric, key.organization, key.cabinet, key.segment, key.currency,
                            key.unit, row.left_source, row.right_source, row.left, row.right, row.difference,
                            row.status, '; '.join(row.left_refs), '; '.join(row.right_refs), row.note))
    sources = [('Источник', 'Версия снимка', 'Идентификатор строки', 'Период', 'Показатель', 'Значение',
                'Организация', 'Кабинет', 'Сегмент', 'Валюта', 'Единица')]
    coverage = [('Источник', 'Версия снимка', 'Полнота', 'Число строк', 'Страницы', 'Замечание')]
    documents = [('Идентификатор строки документа', 'Период', 'Услуга', 'Значение', 'Примечание')]
    for snapshot in run.snapshots:
        coverage.append((snapshot.source, snapshot.version, 'полные' if snapshot.complete else 'неполные',
                         len(snapshot.records), 'не применимо' if run.demo else 'не загружались', snapshot.issue))
        for record in snapshot.records:
            key = record.key
            sources.append((snapshot.source, snapshot.version, record.reference, key.bucket, key.metric,
                            record.value, key.organization, key.cabinet, key.segment, key.currency, key.unit))
            if snapshot.source == 'wb_documents':
                documents.append((record.reference, key.bucket, key.metric, record.value,
                                  'Искусственная строка; извлечение документов не реализовано'))
    if len(documents) == 1:
        documents.append((None, None, None, None, 'Документы не загружались в этом запуске'))
    return {'Сводка': summary, 'Сравнения': comparisons, 'Источники': sources,
            'Покрытие': coverage, 'Документы': documents}
