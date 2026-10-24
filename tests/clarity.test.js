import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  speedIndex, exerciseScore, domainScore, regularity, clarityIndex,
  cognitiveAge, CognitiveAgeBlockedError,
  TARGET_SESSIONS_28D, MIN_SESSIONS_FOR_INDEX,
} from '../src/engine/clarity.js';

describe('speedIndex', () => {
  test('личный рекорд даёт ровно 1.0', () => {
    assert.equal(speedIndex(500, 500), 1.0);
  });
  test('быстрее рекорда — рост, но потолок 1.2', () => {
    assert.equal(speedIndex(500, 450), 500 / 450);
    assert.equal(speedIndex(500, 100), 1.2, 'капается сверху');
  });
  test('медленнее рекорда — падение, но пол 0.5', () => {
    assert.equal(speedIndex(500, 700), 500 / 700);
    assert.equal(speedIndex(500, 100000), 0.5, 'капается снизу');
  });
  test('нет данных о времени → нейтральные 1.0', () => {
    assert.equal(speedIndex(undefined, 500), 1.0);
    assert.equal(speedIndex(500, undefined), 1.0);
    assert.equal(speedIndex(NaN, 500), 1.0);
  });
  test('неположительные значения → 1.0, а не Infinity', () => {
    assert.equal(speedIndex(500, 0), 1.0);
    assert.equal(speedIndex(0, 500), 1.0);
    assert.equal(speedIndex(-1, 500), 1.0);
  });
});

describe('exerciseScore', () => {
  test('d × accuracy × speedIndex', () => {
    assert.ok(Math.abs(exerciseScore({ d: 0.5, accuracy: 0.8 }) - 0.4) < 1e-9);
  });
  test('учитывает скорость', () => {
    const base = exerciseScore({ d: 0.5, accuracy: 0.8 });
    const fast = exerciseScore({ d: 0.5, accuracy: 0.8, meanRtMs: 400, personalBestRtMs: 500 });
    assert.ok(fast > base, 'быстрее рекорда → выше вклад');
  });
  test('мусор на входе не роняет, а даёт 0', () => {
    assert.equal(exerciseScore({ d: NaN, accuracy: NaN }), 0);
    assert.equal(exerciseScore({}), 0);
  });
  test('значения за пределами [0,1] зажимаются', () => {
    assert.ok(exerciseScore({ d: 5, accuracy: 5 }) <= 1.2 * 1.2);
    assert.ok(exerciseScore({ d: -1, accuracy: -1 }) >= 0);
  });
});

describe('domainScore', () => {
  test('null для пустого домена', () => {
    assert.equal(domainScore([]), null);
    assert.equal(domainScore(undefined), null);
  });
  test('среднее по упражнениям', () => {
    const s = domainScore([
      { d: 0.5, accuracy: 0.8 },   // 0.40
      { d: 1.0, accuracy: 1.0 },   // 1.00
    ]);
    assert.ok(Math.abs(s - 0.7) < 1e-9);
  });
});

describe('regularity', () => {
  test('0 сессий → 0', () => assert.equal(regularity(0), 0));
  test('половина нормы → 0.5', () => assert.equal(regularity(TARGET_SESSIONS_28D / 2), 0.5));
  test('норма → 1', () => assert.equal(regularity(TARGET_SESSIONS_28D), 1));
  test('сверх нормы капается на 1', () => assert.equal(regularity(TARGET_SESSIONS_28D * 5), 1));
  test('отрицательное и мусор → 0', () => {
    assert.equal(regularity(-5), 0);
    assert.equal(regularity(NaN), 0);
    assert.equal(regularity(undefined), 0);
  });
});

describe('clarityIndex', () => {
  test('ручной расчёт: один домен, полная регулярность', () => {
    const r = clarityIndex({
      domains: [{ domain: 'attention', weight: 1, results: [{ d: 0.5, accuracy: 0.8 }] }],
      sessionsLast28: TARGET_SESSIONS_28D,
    });
    // raw = 0.5*0.8 = 0.4 ; R = 1 ; multiplier = 1.0 ; CI = round(40)
    assert.equal(r.raw, 0.4);
    assert.equal(r.regularity, 1);
    assert.equal(r.regularityMultiplier, 1);
    assert.equal(r.value, 40);
    assert.equal(r.enoughData, true);
  });

  test('ручной расчёт с весами доменов', () => {
    const r = clarityIndex({
      domains: [
        { domain: 'a', weight: 1, results: [{ d: 0.5, accuracy: 0.8 }] }, // 0.40
        { domain: 'b', weight: 3, results: [{ d: 1.0, accuracy: 1.0 }] }, // 1.00
      ],
      sessionsLast28: 6, // R = 0.5 → multiplier 0.875
    });
    // raw = (1*0.4 + 3*1.0)/4 = 0.85 ; CI = round(100*0.85*0.875) = round(74.375)
    assert.equal(r.raw, 0.85);
    assert.equal(r.regularityMultiplier, 0.875);
    assert.equal(r.value, 74);
  });

  test('домены без данных исключаются из числителя И знаменателя', () => {
    const withEmpty = clarityIndex({
      domains: [
        { domain: 'a', weight: 1, results: [{ d: 1.0, accuracy: 1.0 }] },
        { domain: 'b', weight: 5, results: [] }, // должен быть проигнорирован
      ],
      sessionsLast28: TARGET_SESSIONS_28D,
      totalSessions: 10,
    });
    assert.equal(withEmpty.raw, 1.0, 'пустой домен не тянет индекс вниз');
    assert.equal(withEmpty.breakdown.length, 1);
    assert.equal(withEmpty.value, 100);
  });

  test('мало данных → value=null, а не 0', () => {
    const r = clarityIndex({
      domains: [{ domain: 'a', results: [{ d: 0.5, accuracy: 0.5 }] }],
      sessionsLast28: 1,
    });
    assert.equal(r.value, null, '«нет данных» и «ноль баллов» — разные сообщения');
    assert.equal(r.enoughData, false);
  });

  test('порог MIN_SESSIONS_FOR_INDEX работает', () => {
    assert.equal(MIN_SESSIONS_FOR_INDEX, 2);
    const mk = (n) => clarityIndex({
      domains: [{ domain: 'a', results: [{ d: 0.5, accuracy: 0.5 }] }],
      sessionsLast28: n,
    });
    assert.equal(mk(1).value, null);
    assert.ok(mk(2).value !== null);
  });

  test('нет доменов вообще → value=null', () => {
    const r = clarityIndex({ domains: [], sessionsLast28: 30, totalSessions: 30 });
    assert.equal(r.value, null);
    assert.equal(r.enoughData, false);
  });

  test('множитель регулярности всегда в [0.75, 1.0]', () => {
    // Ключевое продуктовое свойство: регулярность НЕ может обнулить индекс.
    for (let s = 0; s <= 40; s++) {
      const r = clarityIndex({
        domains: [{ domain: 'a', results: [{ d: 1.0, accuracy: 1.0 }] }],
        sessionsLast28: s, totalSessions: 20,
      });
      assert.ok(r.regularityMultiplier >= 0.75, `s=${s}: ${r.regularityMultiplier}`);
      assert.ok(r.regularityMultiplier <= 1.0, `s=${s}: ${r.regularityMultiplier}`);
    }
  });

  test('индекс в [0, 100] на любых входах', () => {
    const extreme = clarityIndex({
      domains: Array.from({ length: 8 }, (_, i) => ({
        domain: `d${i}`, weight: 10,
        results: [{ d: 1, accuracy: 1, meanRtMs: 100, personalBestRtMs: 500 }],
      })),
      sessionsLast28: 100, totalSessions: 100,
    });
    assert.ok(extreme.value >= 0 && extreme.value <= 100, `got ${extreme.value}`);
  });

  test('breakdown раскрывает вклад каждого домена (заявленная прозрачность)', () => {
    const r = clarityIndex({
      domains: [
        { domain: 'attention', weight: 1, results: [{ d: 0.8, accuracy: 0.9 }] },
        { domain: 'logic', weight: 1, results: [{ d: 0.3, accuracy: 0.6 }] },
      ],
      sessionsLast28: 12, totalSessions: 12,
    });
    assert.equal(r.breakdown.length, 2);
    for (const b of r.breakdown) {
      assert.ok('domain' in b && 'weight' in b && 'score' in b);
    }
  });
});

describe('когнитивный возраст намеренно не реализован', () => {
  // open-questions.md №6: любая такая цифра без возрастных норм — выдумка.
  // Тест фиксирует, что никто не добавил её «по-тихому».
  test('cognitiveAge() бросает, а не возвращает число', () => {
    assert.throws(() => cognitiveAge(), CognitiveAgeBlockedError);
  });
  test('сообщение объясняет причину и ссылается на доку', () => {
    assert.throws(() => cognitiveAge(), /возрастные нормы/);
    assert.throws(() => cognitiveAge(), /open-questions/);
  });
});
