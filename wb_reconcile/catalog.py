"""Рабочие названия из ТЗ; это не физические поля и не финансовые формулы."""

WEEKLY = (
    ('units', 'Ед. хранения', 'WB реал,ШТ'),
    ('gross', 'С НДС', 'WB реализ,Итого'),
    ('payment', 'Сумма заливки', 'Итого продажи руб_'),
    ('commission', 'Ретро-бонус', 'Комиссия (полка)'),
    ('logistics', 'Логистический бонус', 'Логистика Итого'),
    ('penalties', 'Санкции', 'Штрафы'),
    ('acquiring', 'Эквайринг', 'Возмещение эквайринга'),
)

MONTHLY = (
    ('pvz', 'Возмещение за выдачу и возврат товаров на ПВЗ'),
    ('transport', 'Возмещение издержек'),
    ('penalties', 'Штрафы'),
    ('agent_fee', 'Вознаграждение WB без НДС + НДС с вознаграждения WB'),
    ('promotion', 'Оказание услуг «WB Продвижение»'),
    ('media', 'Оказание услуг «WB Медиа»'),
    ('acquiring', 'Возмещение эквайринга'),
)

SOURCES = {
    'daily': ('cube', 'wb_reports'),
    'weekly': ('one_c', 'cube'),
    'monthly': ('wb_documents', 'cube', 'one_c'),
}


def metrics(mode: str) -> tuple[str, ...]:
    if mode == 'daily':
        return ('payment',)
    return tuple(row[0] for row in (WEEKLY if mode == 'weekly' else MONTHLY))
