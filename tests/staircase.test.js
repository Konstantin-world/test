/**
 * staircase.test.js — тесты адаптивного контроллера.
 *
 * Ключевой тест здесь — `converges to 79.4%`. Он проверяет не «код запускается»,
 * а что реализованная точка схождения совпадает с теоретической из Levitt (1971).
 * Если кто-то поменяет правило на 1-up/2-down или сломает halving шага,
 * этот тест покраснеет.
 *
 * Запуск: node --test tests/
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { Staircase, theoreticalConvergence } from '../src/engine/staircase.js';

// ─── детерминированный ГПСЧ ────────────────────────────────────────────────
// Без сида тест на сходимость будет флапать на CI — худший вид теста.
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Психофизическая кривая: вероятность правильного ответа при сложности d.
 * Логистическая функция с порогом mu и крутизной sigma.
 */
function psychometric(d, mu, sigma) {
  return 1 / (1 + Math.exp((d - mu) / sigma));
}

/** Прогнать синтетического пользователя. */
function simulate({ trials = 4000, mu = 0.5, sigma = 0.1, seed = 42, d0 = 0.3, options = {} }) {
  const rnd = mulberry32(seed);
  const sc = new Staircase(d0, options);
  for (let i = 0; i < trials; i++) {
    const p = psychometric(sc.difficulty, mu, sigma);
    sc.respond(rnd() < p);
  }
  return sc;
}

// ─── детерминированное поведение ───────────────────────────────────────────
describe('правило лестницы', () => {
  test('повышение после 3 подряд правильных', () => {
    const sc = new Staircase(0.5);
    assert.equal(sc.respond(true).direction, 0, 'после 1-го правильного — без шага');
    assert.equal(sc.respond(true).direction, 0, 'после 2-го — без шага');
    const r = sc.respond(true);
    assert.equal(r.direction, +1, 'после 3-го — шаг вверх');
    assert.ok(r.d > 0.5, 'сложность выросла');
  });

  test('понижение после 1 ошибки', () => {
    const sc = new Staircase(0.5);
    const r = sc.respond(false);
    assert.equal(r.direction, -1);
    assert.ok(r.d < 0.5, 'сложность упала');
  });

  test('серия правильных сбрасывается ошибкой', () => {
    const sc = new Staircase(0.5);
    sc.respond(true);
    sc.respond(true);
    sc.respond(false); // сброс correctRun
    assert.equal(sc.correctRun, 0);
    // теперь снова нужно 3 подряд
    sc.respond(true);
    sc.respond(true);
    assert.equal(sc.respond(true).direction, +1);
  });

  test('настраиваемое правило 1-up/2-down', () => {
    const sc = new Staircase(0.5, { correctsToStepUp: 2 });
    assert.equal(sc.respond(true).direction, 0);
    assert.equal(sc.respond(true).direction, +1, 'шаг уже после 2-го');
  });
});

describe('границы и развороты', () => {
  test('не уходит ниже floor', () => {
    const sc = new Staircase(0.1, { floor: 0.05 });
    for (let i = 0; i < 500; i++) sc.respond(false);
    assert.equal(sc.difficulty, 0.05);
  });

  test('не уходит выше ceiling', () => {
    const sc = new Staircase(0.95);
    for (let i = 0; i < 500; i++) sc.respond(true);
    assert.equal(sc.difficulty, 1.0);
  });

  test('floor >= ceiling отклоняется', () => {
    assert.throws(() => new Staircase(0.5, { floor: 1.0, ceiling: 0.5 }), RangeError);
  });

  test('разворот фиксируется и уменьшает шаг', () => {
    const sc = new Staircase(0.5, { initialStep: 0.08, minStep: 0.02, halveAfterReversals: 2 });
    assert.equal(sc.step, 0.08);

    // вверх до разворота
    for (let i = 0; i < 9; i++) sc.respond(true); // 3 разворота вверх
    // ошибка → разворот вниз
    sc.respond(false);
    assert.ok(sc.reversals.length >= 1, `разворот зафиксирован, got ${sc.reversals.length}`);

    // после 2-го разворота шаг должен уменьшиться
    for (let i = 0; i < 30; i++) sc.respond(i % 4 === 3 ? false : true);
    assert.ok(sc.step < 0.08, `шаг уменьшился: ${sc.step}`);
    assert.ok(sc.step >= 0.02, `шаг не ниже minStep: ${sc.step}`);
  });

  test('шаг не опускается ниже minStep', () => {
    const sc = new Staircase(0.5, { initialStep: 0.08, minStep: 0.02, halveAfterReversals: 1 });
    for (let i = 0; i < 400; i++) sc.respond(i % 4 === 3 ? false : true);
    assert.equal(sc.step, 0.02);
  });
});

describe('оценка порога', () => {
  test('null пока разворотов мало', () => {
    const sc = new Staircase(0.5);
    assert.equal(sc.threshold(), null);
    sc.reversals.push(0.4);
    assert.equal(sc.threshold(), null, '1 разворот — ещё рано');
    sc.reversals.push(0.5);
    assert.equal(sc.threshold(), null, '2 разворота — оба отбрасываются');
  });

  test('первые два разворота отбрасываются', () => {
    const sc = new Staircase(0.5);
    sc.reversals.push(0.10, 0.20, 0.40, 0.42, 0.44, 0.46);
    // slice(2, 6) → [0.40, 0.42, 0.44, 0.46] → mean 0.43
    assert.ok(Math.abs(sc.threshold() - 0.43) < 1e-9, `got ${sc.threshold()}`);
  });

  test('без отбрасывания оценка смещена к стартовой точке', () => {
    const sc = new Staircase(0.5);
    sc.reversals.push(0.10, 0.20, 0.40, 0.42, 0.44, 0.46);
    const naive = sc.reversals.reduce((s, v) => s + v, 0) / sc.reversals.length;
    assert.ok(naive < sc.threshold(), 'наивное среднее занижает порог');
  });
});

// ─── КЛЮЧЕВОЙ ТЕСТ: эмпирическая точка схождения ───────────────────────────
describe('точка схождения', () => {
  test('1-up/3-down сходится к 79.4% (чистая лестница)', () => {
    const MU = 0.5;
    const SIGMA = 0.10;
    const sc = simulate({ trials: 6000, mu: MU, sigma: SIGMA, seed: 12345, antiFrustration: null });

    // вторая половина прогона — после схождения
    const half = Math.floor(sc.history.length / 2);
    const tail = sc.history.slice(half);
    const acc = tail.filter((h) => h.correct).length / tail.length;

    const target = theoreticalConvergence(3); // 0.794
    assert.ok(
      Math.abs(acc - target) < 0.025,
      `фактическая точность ${acc.toFixed(4)} vs теоретическая ${target} (±0.025)`
    );

    // Уровень должен установиться там, где психофизическая кривая даёт 79.4%.
    // Инверсия p(d) = 1/(1+exp((d-mu)/sigma)):  d = mu + sigma * ln((1-p)/p)
    const expectedD = MU + SIGMA * Math.log((1 - target) / target);
    const meanD = tail.reduce((s, h) => s + h.d, 0) / tail.length;
    assert.ok(
      Math.abs(meanD - expectedD) < 0.05,
      `средний d ${meanD.toFixed(4)} vs ожидаемый ${expectedD.toFixed(4)}`
    );
  });

  test('1-up/2-down сходится к 70.7% — контроль правила', () => {
    const sc = simulate({
      trials: 6000, mu: 0.5, sigma: 0.1, seed: 777,
      options: { correctsToStepUp: 2, antiFrustration: null },
    });
    const tail = sc.history.slice(Math.floor(sc.history.length / 2));
    const acc = tail.filter((h) => h.correct).length / tail.length;
    assert.ok(Math.abs(acc - 0.7071) < 0.03, `got ${acc.toFixed(4)}, expected ~0.7071`);
  });

  test('точность 79.4% НЕ попадает в 70.7% — правила различимы', () => {
    // Защита от «теста, который проходит при любой реализации».
    // Если оба правила дают одно и число, тест бессмысленен.
    assert.ok(Math.abs(theoreticalConvergence(3) - theoreticalConvergence(2)) > 0.05);
  });

  test('анти-фрустрация СДВИГАЕТ точку схождения (замер drift)', () => {
    const pure = simulate({ trials: 6000, mu: 0.5, sigma: 0.1, seed: 12345, antiFrustration: null });
    const softened = simulate({
      trials: 6000, mu: 0.5, sigma: 0.1, seed: 12345,
      options: { antiFrustration: { maxConsecutiveDowns: 2, pauseTrials: 5 } },
    });
    const accOf = (sc) => {
      const tail = sc.history.slice(Math.floor(sc.history.length / 2));
      return tail.filter((h) => h.correct).length / tail.length;
    };
    const aPure = accOf(pure);
    const aSoft = accOf(softened);

    // Документируем факт: подавление step-down'ов делает игру сложнее,
    // точность падает ниже целевых 79.4%.
    assert.ok(aSoft < aPure, `softened ${aSoft.toFixed(4)} должно быть < pure ${aPure.toFixed(4)}`);
    // eslint-disable-next-line no-console
    console.log(
      `      drift от anti-frustration: 79.4% → ${(aSoft * 100).toFixed(1)}% ` +
      `(чистая лестница: ${(aPure * 100).toFixed(1)}%)`
    );
  });

  test('всегда правильный пользователь доходит до ceiling', () => {
    const sc = simulate({ trials: 400, mu: 5.0, sigma: 0.1, seed: 1 });
    assert.equal(sc.difficulty, 1.0);
  });

  test('всегда ошибающийся пользователь доходит до floor', () => {
    const sc = new Staircase(0.5);
    for (let i = 0; i < 400; i++) sc.respond(false);
    assert.equal(sc.difficulty, 0.05);
  });

  test('сходится из разных стартовых точек', () => {
    for (const d0 of [0.05, 0.3, 0.9]) {
      const sc = simulate({ trials: 8000, mu: 0.5, sigma: 0.1, seed: 99, d0 });
      const tail = sc.history.slice(Math.floor(sc.history.length / 2));
      const acc = tail.filter((h) => h.correct).length / tail.length;
      assert.ok(
        Math.abs(acc - 0.794) < 0.03,
        `d0=${d0}: точность ${acc.toFixed(4)} — лестница должна забывать стартовую точку`
      );
    }
  });
});

describe('защита от некорректного ввода', () => {
  test('respond() принимает только boolean', () => {
    const sc = new Staircase(0.5);
    assert.throws(() => sc.respond('true'), TypeError);
    assert.throws(() => sc.respond(1), TypeError);
    assert.throws(() => sc.respond(null), TypeError);
    assert.throws(() => sc.respond(undefined), TypeError);
  });

  test('неверные опции отклоняются', () => {
    assert.throws(() => new Staircase(0.5, { correctsToStepUp: 0 }), RangeError);
    assert.throws(() => new Staircase(0.5, { errorsToStepDown: 0 }), RangeError);
  });
});

describe('персистентность между сессиями', () => {
  test('toJSON/fromJSON сохраняет состояние', () => {
    const sc = new Staircase(0.4);
    for (let i = 0; i < 40; i++) sc.respond(i % 5 !== 0);
    const restored = Staircase.fromJSON(JSON.parse(JSON.stringify(sc.toJSON())));

    assert.equal(restored.difficulty, sc.difficulty);
    assert.equal(restored.step, sc.step);
    assert.equal(restored.trials, sc.trials);
    assert.deepEqual(restored.reversals, sc.reversals);
    assert.equal(restored.threshold(), sc.threshold());
  });

  test('восстановленный контроллер продолжает с той же точки', () => {
    const sc = new Staircase(0.4);
    for (let i = 0; i < 40; i++) sc.respond(i % 5 !== 0);
    const restored = Staircase.fromJSON(sc.toJSON());

    const a = sc.respond(true);
    const b = restored.respond(true);
    assert.equal(a.d, b.d);
  });

  test('состояние сериализуется в JSON без циклов', () => {
    const sc = new Staircase(0.4);
    sc.respond(true);
    const json = JSON.stringify(sc.toJSON());
    assert.ok(json.length > 0);
    assert.doesNotThrow(() => JSON.parse(json));
  });
});

describe('метрики', () => {
  test('observedAccuracy считает долю правильных', () => {
    const sc = new Staircase(0.5);
    sc.respond(true);
    sc.respond(false);
    sc.respond(true);
    sc.respond(true);
    assert.ok(Math.abs(sc.observedAccuracy - 0.75) < 1e-9);
  });

  test('observedAccuracy = 0 до первого ответа', () => {
    assert.equal(new Staircase(0.5).observedAccuracy, 0);
  });

  test('history пишет каждую пробу', () => {
    const sc = new Staircase(0.5);
    for (let i = 0; i < 17; i++) sc.respond(i % 2 === 0);
    assert.equal(sc.history.length, 17);
    assert.equal(sc.trials, 17);
  });
});
