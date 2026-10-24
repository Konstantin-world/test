import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  blockSec, priority, composeSession,
  WARMUP_SEC, REFLECTION_SEC, MIN_SESSION_SEC, SESSION_PRESETS_SEC, GOAL_WEIGHTS,
} from '../src/engine/session-composer.js';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const catalog = JSON.parse(readFileSync(resolve(ROOT, 'content/exercises.json'), 'utf8')).exercises;
const mvp = catalog.filter((e) => e.mvp);

// ─── синтетический каталог для точных проверок ─────────────────────────────
const mk = (id, domain, durationSec, blocksPerSession = 1) => ({
  id, domain, durationSec, trial: { blocksPerSession },
  difficulty: { params: [{ key: 'x', type: 'int', at0: 1, at1: 5 }] },
});

describe('blockSec', () => {
  test('делит длительность на число блоков', () => {
    assert.equal(blockSec(mk('a', 'logic', 180, 3)), 60);
    assert.equal(blockSec(mk('b', 'logic', 150, 1)), 150);
  });
  test('blocksPerSession по умолчанию 1', () => {
    assert.equal(blockSec({ durationSec: 120 }), 120);
  });
  test('ноль блоков отклоняется', () => {
    assert.throws(() => blockSec({ durationSec: 120, trial: { blocksPerSession: 0 } }), RangeError);
  });
  test('совпадает с реальным каталогом', () => {
    // dual_n_back: 180с / 3 блока = 60с — самое дешёвое в MVP
    const dual = mvp.find((e) => e.id === 'dual_n_back');
    assert.equal(blockSec(dual), 60);
  });
});

describe('priority', () => {
  const ex = mk('ex', 'attention', 120);

  test('проседающий домен важнее сильного', () => {
    const weak = priority({ exercise: ex, domainScores: { attention: 0.2 } });
    const strong = priority({ exercise: ex, domainScores: { attention: 0.9 } });
    assert.ok(weak > strong, `weak ${weak} должно быть > strong ${strong}`);
  });

  test('домен без данных получает умеренный приоритет, не максимальный', () => {
    const unknown = priority({ exercise: ex, domainScores: { logic: 0.5 } });
    const worst = priority({ exercise: ex, domainScores: { attention: 0.0 } });
    assert.ok(unknown < worst, 'иначе новичок получит только незнакомые упражнения');
    assert.ok(unknown > 0);
  });

  test('домен из последней сессии сильно штрафруется', () => {
    const fresh = priority({ exercise: ex, recentDomains: ['logic'] });
    const justUsed = priority({ exercise: ex, recentDomains: ['attention'] });
    const yesterday = priority({ exercise: ex, recentDomains: ['logic', 'attention'] });
    assert.ok(justUsed < yesterday, 'вчера — мягче, чем сегодня');
    assert.ok(yesterday < fresh, '«два дня подряд» из брифа соблюдается');
  });

  test('цель усиливает релевантные домены', () => {
    const base = priority({ exercise: ex });
    const withGoal = priority({ exercise: ex, goal: 'focus' });
    assert.ok(withGoal > base, 'attention входит в цель focus');
    assert.equal(GOAL_WEIGHTS.focus.attention, 2.0);
  });

  test('неизвестная цель не ломает расчёт', () => {
    assert.ok(priority({ exercise: ex, goal: 'nonexistent' }) > 0);
  });

  test('долгий простой даёт бонус, но ограниченный', () => {
    const now = priority({ exercise: ex, daysSinceUsed: { ex: 0 } });
    const week = priority({ exercise: ex, daysSinceUsed: { ex: 7 } });
    const year = priority({ exercise: ex, daysSinceUsed: { ex: 365 } });
    assert.ok(week > now);
    assert.ok(year > week);
    assert.ok(year / now < 1.5, 'бонус не должен превышать ~+20% и доминировать над weakness');
  });
});

describe('composeSession — границы', () => {
  test('бюджет ниже MIN_SESSION_SEC отклоняется', () => {
    assert.throws(
      () => composeSession({ budgetSec: 180, catalog: mvp }),
      /MIN_SESSION_SEC/
    );
  });

  test('сообщение об ошибке ссылается на доку', () => {
    assert.throws(() => composeSession({ budgetSec: 180, catalog: mvp }), /open-questions/);
  });

  test('все пресеты UI не ниже минимума', () => {
    for (const p of SESSION_PRESETS_SEC) {
      assert.ok(p >= MIN_SESSION_SEC, `пресет ${p}с ниже MIN_SESSION_SEC=${MIN_SESSION_SEC}`);
    }
  });

  test('пустой каталог отклоняется', () => {
    assert.throws(() => composeSession({ budgetSec: 600, catalog: [] }), /catalog пуст/);
  });

  test('не-числовой бюджет отклоняется', () => {
    assert.throws(() => composeSession({ budgetSec: '600', catalog: mvp }), TypeError);
  });

  test('минимальный бюджет даёт ровно одно упражнение (решение A+C)', () => {
    // 300 − 45 − 30 = 225с основной части; самые дешёвые блоки по 60с
    const s = composeSession({ budgetSec: MIN_SESSION_SEC, catalog: mvp });
    assert.ok(s.blocks.length >= 1);
    assert.ok(s.totalSec <= MIN_SESSION_SEC);
  });
});

describe('composeSession — структура', () => {
  test('разминка и рефлексия всегда присутствуют', () => {
    const s = composeSession({ budgetSec: 900, catalog: mvp });
    assert.equal(s.warmupSec, WARMUP_SEC);
    assert.equal(s.reflectionSec, REFLECTION_SEC);
    assert.equal(s.totalSec, WARMUP_SEC + REFLECTION_SEC + s.blocks.reduce((a, b) => a + b.sec, 0));
  });

  test('не превышает бюджет', () => {
    for (const budget of SESSION_PRESETS_SEC) {
      const s = composeSession({ budgetSec: budget, catalog: mvp });
      assert.ok(s.totalSec <= budget, `бюджет ${budget}: total ${s.totalSec}`);
    }
  });

  test('один домен максимум дважды за сессию', () => {
    for (const budget of SESSION_PRESETS_SEC) {
      const s = composeSession({ budgetSec: budget, catalog: mvp });
      const counts = {};
      for (const b of s.blocks) counts[b.domain] = (counts[b.domain] ?? 0) + 1;
      for (const [dom, n] of Object.entries(counts)) {
        assert.ok(n <= 2, `домен ${dom} взят ${n} раз при бюджете ${budget}`);
      }
    }
  });

  test('блоки неделимы: leftover объясняется предупреждением', () => {
    const s = composeSession({ budgetSec: 900, catalog: mvp });
    if (s.totalSec < 900 - 60) {
      assert.ok(s.warnings.some((w) => /leftover/.test(w)), 'должно быть объяснение');
    }
  });

  test('более длинная сессия содержит не меньше упражнений', () => {
    const short = composeSession({ budgetSec: 300, catalog: mvp });
    const long = composeSession({ budgetSec: 1200, catalog: mvp });
    assert.ok(long.blocks.length >= short.blocks.length);
    assert.ok(long.totalSec >= short.totalSec);
  });
});

describe('composeSession — персонализация', () => {
  test('проседающий домен попадает в сессию раньше сильного', () => {
    const scores = {};
    for (const d of new Set(mvp.map((e) => e.domain))) scores[d] = 0.9;
    scores.logic = 0.05; // провал

    const s = composeSession({ budgetSec: 600, catalog: mvp, domainScores: scores });
    assert.ok(
      s.blocks.some((b) => b.domain === 'logic'),
      `слабый домен не попал в сессию: ${s.blocks.map((b) => b.domain).join(', ')}`
    );
    assert.equal(s.blocks[0].domain, 'logic', 'слабый домен должен идти первым');
  });

  test('цель exam сдвигает состав в сторону логики и языка', () => {
    const scores = {};
    for (const d of new Set(mvp.map((e) => e.domain))) scores[d] = 0.5;

    const plain = composeSession({ budgetSec: 1200, catalog: mvp, domainScores: scores });
    const exam = composeSession({ budgetSec: 1200, catalog: mvp, domainScores: scores, goal: 'exam' });

    const share = (s, doms) => s.blocks.filter((b) => doms.includes(b.domain)).length / s.blocks.length;
    const target = ['logic', 'language'];
    assert.ok(
      share(exam, target) >= share(plain, target),
      `exam: ${share(exam, target)} vs plain: ${share(plain, target)}`
    );
  });

  test('домен из прошлой сессии не берётся первым', () => {
    const s = composeSession({
      budgetSec: 900, catalog: mvp, recentDomains: [mvp[0].domain],
    });
    assert.notEqual(
      s.blocks[0].domain, mvp[0].domain,
      '«не повторять один домен два дня подряд» из брифа нарушено'
    );
  });

  test('excludeIds исключает упражнение', () => {
    const s = composeSession({
      budgetSec: 1200, catalog: mvp, excludeIds: new Set(['stroop_test', 'sudoku']),
    });
    const ids = s.blocks.map((b) => b.exerciseId);
    assert.ok(!ids.includes('stroop_test'));
    assert.ok(!ids.includes('sudoku'));
  });
});

describe('composeSession — детерминизм', () => {
  test('одинаковые входы дают одинаковый результат', () => {
    const a = composeSession({ budgetSec: 900, catalog: mvp, domainScores: { logic: 0.3 } });
    const b = composeSession({ budgetSec: 900, catalog: mvp, domainScores: { logic: 0.3 } });
    assert.deepEqual(a.blocks, b.blocks);
  });

  test('все выбранные упражнения существуют в каталоге', () => {
    const s = composeSession({ budgetSec: 1200, catalog: mvp });
    const ids = new Set(catalog.map((e) => e.id));
    for (const b of s.blocks) {
      assert.ok(ids.has(b.exerciseId), `неизвестное упражнение ${b.exerciseId}`);
    }
  });
});
