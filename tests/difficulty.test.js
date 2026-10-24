import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { clampIndex, interpParam, resolveParams, difficultyTable } from '../src/engine/difficulty.js';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const catalog = JSON.parse(readFileSync(resolve(ROOT, 'content/exercises.json'), 'utf8')).exercises;

describe('clampIndex', () => {
  test('зажимает в [0, 1]', () => {
    assert.equal(clampIndex(-5), 0);
    assert.equal(clampIndex(0), 0);
    assert.equal(clampIndex(0.5), 0.5);
    assert.equal(clampIndex(1), 1);
    assert.equal(clampIndex(99), 1);
  });
  test('NaN и Infinity отклоняются', () => {
    assert.throws(() => clampIndex(NaN), TypeError);
    assert.throws(() => clampIndex(Infinity), TypeError);
    assert.throws(() => clampIndex(undefined), TypeError);
  });
});

describe('interpParam — int', () => {
  const p = { key: 'n', type: 'int', at0: 1, at1: 4 };
  test('концы точные', () => {
    assert.equal(interpParam(p, 0), 1);
    assert.equal(interpParam(p, 1), 4);
  });
  test('середина округляется', () => {
    assert.equal(interpParam(p, 0.5), Math.round(2.5), 'round(2.5)=3 (Math.round, не banker\'s)');
    assert.equal(Number.isInteger(interpParam(p, 0.33)), true);
  });
  test('монотонно не убывает', () => {
    let prev = -Infinity;
    for (let i = 0; i <= 100; i++) {
      const v = interpParam(p, i / 100);
      assert.ok(v >= prev, `немонотонно на d=${i / 100}: ${v} < ${prev}`);
      prev = v;
    }
  });
  test('отрицательный диапазон (at1 < at0) тоже работает', () => {
    const down = { key: 'ms', type: 'int', at0: 3000, at1: 1500 };
    assert.equal(interpParam(down, 0), 3000);
    assert.equal(interpParam(down, 0.5), 2250);
    assert.equal(interpParam(down, 1), 1500);
  });
});

describe('interpParam — float', () => {
  const p = { key: 'targetRate', type: 'float', at0: 0.3, at1: 0.18 };
  test('концы и середина', () => {
    assert.equal(interpParam(p, 0), 0.3);
    assert.equal(interpParam(p, 1), 0.18);
    assert.equal(interpParam(p, 0.5), 0.24);
  });
  test('округление до 3 знаков, без артефактов float', () => {
    const v = interpParam(p, 0.33);
    assert.equal(v, Math.round(v * 1000) / 1000);
    assert.ok(String(v).length < 8, `слишком длинное представление: ${v}`);
  });
});

describe('interpParam — enum', () => {
  const p = { key: 'mode', type: 'enum', values: ['a', 'b', 'c', 'd'] };
  test('концы и середина', () => {
    assert.equal(interpParam(p, 0), 'a');
    assert.equal(interpParam(p, 1), 'd');
    assert.equal(interpParam(p, 0.5), 'c'); // round(1.5)=2
  });
  test('никогда не выходит за границы массива', () => {
    for (let i = 0; i <= 100; i++) {
      const v = interpParam(p, i / 100);
      assert.ok(p.values.includes(v), `d=${i / 100} дало ${v}`);
    }
  });
  test('enum из 2 значений переключается на середине', () => {
    const two = { key: 'orderMatters', type: 'enum', values: [false, true] };
    assert.equal(interpParam(two, 0), false);
    assert.equal(interpParam(two, 0.4), false);
    assert.equal(interpParam(two, 0.6), true);
    assert.equal(interpParam(two, 1), true);
  });
  test('пустой enum — ошибка, а не undefined', () => {
    assert.throws(() => interpParam({ key: 'x', type: 'enum', values: [] }, 0.5), /no values/);
  });
});

describe('interpParam — ошибки', () => {
  test('неизвестный тип отклоняется', () => {
    assert.throws(() => interpParam({ key: 'x', type: 'string', at0: 1, at1: 2 }, 0.5), /unknown param type/);
  });
});

describe('resolveParams', () => {
  test('возвращает все параметры упражнения', () => {
    const ex = catalog.find((e) => e.id === 'dual_n_back');
    const p = resolveParams(ex, 0.5);
    assert.deepEqual(Object.keys(p).sort(), ex.difficulty.params.map((x) => x.key).sort());
    assert.equal(p.n, 3);            // 1 → 4, середина = 2.5 → round = 3
    assert.equal(p.stimulusMs, 2250);
    assert.equal(p.gapMs, 350);
    assert.equal(p.targetRate, 0.24);
  });

  test('d=0 даёт самый лёгкий профиль', () => {
    const ex = catalog.find((e) => e.id === 'stroop_test');
    const p = resolveParams(ex, 0);
    for (const def of ex.difficulty.params) {
      const expected = def.type === 'enum' ? def.values[0] : def.at0;
      assert.deepEqual(p[def.key], expected, `параметр ${def.key}`);
    }
  });

  test('d=1 даёт самый тяжёлый профиль', () => {
    const ex = catalog.find((e) => e.id === 'stroop_test');
    const p = resolveParams(ex, 1);
    for (const def of ex.difficulty.params) {
      const expected = def.type === 'enum' ? def.values[def.values.length - 1] : def.at1;
      assert.deepEqual(p[def.key], expected, `параметр ${def.key}`);
    }
  });
});

describe('инварианты по всему каталогу', () => {
  test('каждое упражнение разрешается при d=0, 0.5, 1 без ошибок', () => {
    for (const ex of catalog) {
      for (const d of [0, 0.5, 1]) {
        assert.doesNotThrow(() => resolveParams(ex, d), `${ex.id} при d=${d}`);
      }
    }
  });

  test('все параметры действительно меняются со сложностью', () => {
    // Иначе параметр мёртвый: занимает место в каталоге и путает ревью.
    for (const ex of catalog) {
      for (const p of ex.difficulty.params) {
        const lo = interpParam(p, 0);
        const hi = interpParam(p, 1);
        assert.notDeepEqual(lo, hi, `${ex.id}.${p.key}: at0 === at1`);
      }
    }
  });

  test('временные параметры при d=1 короче, чем при d=0', () => {
    // Семантическая проверка направления: «сложнее» = меньше времени.
    for (const ex of catalog) {
      for (const p of ex.difficulty.params) {
        if (p.type === 'int' && /(Ms|Sec)$/.test(p.key) && /Limit|Window|Exposure|Stimulus|Gap|Peek|Cue|Flip|Time/i.test(p.key)) {
          assert.ok(p.at1 < p.at0, `${ex.id}.${p.key}: ограничение времени должно ужесточаться (at0=${p.at0}, at1=${p.at1})`);
        }
      }
    }
  });

  test('Rate-параметры остаются в [0,1] на всей кривой', () => {
    for (const ex of catalog) {
      for (const p of ex.difficulty.params) {
        if (!/Rate$/.test(p.key)) continue;
        for (let i = 0; i <= 10; i++) {
          const v = interpParam(p, i / 10);
          assert.ok(v >= 0 && v <= 1, `${ex.id}.${p.key} при d=${i / 10}: ${v}`);
        }
      }
    }
  });
});

describe('difficultyTable', () => {
  test('строит таблицу для ревью', () => {
    const ex = catalog.find((e) => e.id === 'dual_n_back');
    const t = difficultyTable(ex);
    assert.equal(t.length, ex.difficulty.params.length);
    assert.equal(t[0].at.length, 5); // точки по умолчанию
  });
  test('принимает свои точки', () => {
    const ex = catalog.find((e) => e.id === 'dual_n_back');
    const t = difficultyTable(ex, [0, 1]);
    assert.equal(t[0].at.length, 2);
  });
});
