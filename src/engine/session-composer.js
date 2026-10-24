/**
 * session-composer.js — сборка ежедневной «Умной зарядки».
 *
 * Продуктовые решения, зафиксированные в open-questions.md №1 (вариант A+C):
 *   - минимальная сессия — 5 минут, обещание «от 3 минут» снято как невыполнимое;
 *   - в самой короткой сессии — ОДНО упражнение, а не «3–5 микро-игр»;
 *   - длительность блока упражнения не урезается, иначе метрики теряют
 *     сравнимость между сессиями разной длины и «Индекс ясности» перестаёт
 *     быть измерением.
 *
 * Структура сессии (бриф, раздел 3):
 *   разминка → основная часть → рефлексия
 */

/** Секунды на разминку. Бриф даёт 30–60с; берём середину. */
export const WARMUP_SEC = 45;
/** Секунды на рефлексию. */
export const REFLECTION_SEC = 30;
/**
 * Минимальная длительность сессии.
 * НЕ 180с: при бюджете 180 − 45 − 30 = 105с в основную часть не влезает
 * ни один блок самого короткого упражнения (60с) с запасом, и уж точно
 * не влезает «3–5 микро-игр». Проверено tools/validate-content.mjs.
 */
export const MIN_SESSION_SEC = 300;

/** Пресеты выбора времени в UI. */
export const SESSION_PRESETS_SEC = [300, 600, 900, 1200];

/**
 * Цели пользователя → приоритет доменов (бриф, раздел 3).
 * Домены, не перечисленные в цели, получают вес 1.0 — цель усиливает,
 * а не исключает остальное.
 */
export const GOAL_WEIGHTS = {
  memory: { working_memory: 2.0, episodic_memory: 2.0 },
  focus: { attention: 2.0, processing_speed: 1.5 },
  clarity: { cognitive_flexibility: 1.5, processing_speed: 1.5, logic: 1.5 },
  exam: { logic: 2.0, language: 2.0, working_memory: 1.5, attention: 1.5 },
};

/**
 * Длительность одного блока упражнения.
 * @param {{durationSec: number, trial?: {blocksPerSession?: number}}} ex
 */
export function blockSec(ex) {
  const blocks = ex.trial?.blocksPerSession ?? 1;
  if (blocks < 1) throw new RangeError(`blocksPerSession must be >= 1, got ${blocks}`);
  return Math.round(ex.durationSec / blocks);
}

/**
 * Приоритет упражнения для отбора. Больше = берём раньше.
 *
 * Слагаемые:
 *   weakness    — 1 − оценка домена: проседающий домен важнее сильного
 *   variety     — штраф за домен, который уже был в последних сессиях
 *   goal        — вес из цели пользователя
 *   fresh       — лёгкий бонус упражнениям, которые давно не открывали
 *
 * @param {Object} p
 * @param {Object} p.exercise
 * @param {Record<string, number>} p.domainScores 0..1 по каждому домену
 * @param {string[]} p.recentDomains домены последних N сессий (свежие первыми)
 * @param {keyof GOAL_WEIGHTS} [p.goal]
 * @param {Record<string, number>} [p.daysSinceUsed] exerciseId → дней с последней сессии
 */
export function priority({ exercise, domainScores = {}, recentDomains = [], goal = null, daysSinceUsed = {} }) {
  const dom = exercise.domain;
  const score = Number.isFinite(domainScores[dom]) ? clamp01(domainScores[dom]) : 0.5;

  // Домен, который не тренировали, считаем «проседающим» умеренно,
  // а не максимально: иначе новичок получит только незнакомые упражнения.
  const hasData = Object.prototype.hasOwnProperty.call(domainScores, dom);
  const weakness = hasData ? 1 - score : 0.6;

  // «Не повторять один и тот же домен два дня подряд» (бриф, раздел 3).
  // Штраф тем больше, чем свежее повтор.
  let variety = 1.0;
  if (recentDomains[0] === dom) variety = 0.15;
  else if (recentDomains[1] === dom) variety = 0.6;

  const goalWeight = (goal && GOAL_WEIGHTS[goal]?.[dom]) || 1.0;

  const age = Number.isFinite(daysSinceUsed[exercise.id]) ? daysSinceUsed[exercise.id] : 0;
  const fresh = 1 + Math.min(age, 14) / 70; // максимум +20% за две недели простоя

  return weakness * variety * goalWeight * fresh;
}

/**
 * Собрать сессию.
 *
 * @param {Object} input
 * @param {number} input.budgetSec доступное время пользователя
 * @param {Array} input.catalog упражнения из content/exercises.json (mvp-фильтр — на вызывающем)
 * @param {Record<string, number>} [input.domainScores]
 * @param {string[]} [input.recentDomains]
 * @param {string} [input.goal]
 * @param {Record<string, number>} [input.daysSinceUsed]
 * @param {Set<string>} [input.excludeIds] упражнения, которые нельзя брать
 * @returns {{warmupSec:number, reflectionSec:number, totalSec:number,
 *            blocks: Array<{exerciseId:string, domain:string, sec:number}>,
 *            warnings: string[]}}
 */
export function composeSession({
  budgetSec,
  catalog,
  domainScores = {},
  recentDomains = [],
  goal = null,
  daysSinceUsed = {},
  excludeIds = new Set(),
}) {
  const warnings = [];

  if (!Number.isFinite(budgetSec)) throw new TypeError(`budgetSec must be a number, got ${budgetSec}`);
  if (budgetSec < MIN_SESSION_SEC) {
    throw new RangeError(
      `budgetSec=${budgetSec} ниже MIN_SESSION_SEC=${MIN_SESSION_SEC}. ` +
      `Сессия короче 5 минут несобираема — см. docs/spec/open-questions.md №1.`
    );
  }
  if (!Array.isArray(catalog) || catalog.length === 0) {
    throw new Error('catalog пуст');
  }

  const overhead = WARMUP_SEC + REFLECTION_SEC;
  let remaining = budgetSec - overhead;
  if (remaining <= 0) {
    throw new RangeError(`бюджет ${budgetSec}с не покрывает разминку и рефлексию (${overhead}с)`);
  }

  const ranked = catalog
    .filter((ex) => !excludeIds.has(ex.id))
    .map((ex) => ({
      ex,
      sec: blockSec(ex),
      p: priority({ exercise: ex, domainScores, recentDomains, goal, daysSinceUsed }),
    }))
    // сначала дорогие по приоритету; при равенстве — дешевле по времени,
    // чтобы плотнее заполнить бюджет
    .sort((a, b) => b.p - a.p || a.sec - b.sec);

  const cheapest = ranked.reduce((m, r) => (r.sec < m ? r.sec : m), Infinity);
  if (cheapest > remaining) {
    throw new RangeError(
      `бюджет основной части ${remaining}с меньше самого короткого блока ${cheapest}с`
    );
  }

  const blocks = [];
  const usedDomains = new Set();

  for (const r of ranked) {
    if (remaining <= 0) break;
    if (r.sec > remaining) continue; // не влезает — пробуем следующее
    // Разнообразие внутри сессии: домен берём максимум дважды.
    // Без этого композитор набьёт сессию одним доменом с худшей оценкой.
    const countInSession = blocks.filter((b) => b.domain === r.ex.domain).length;
    if (countInSession >= 2) continue;

    blocks.push({ exerciseId: r.ex.id, domain: r.ex.domain, sec: r.sec });
    usedDomains.add(r.ex.domain);
    remaining -= r.sec;
  }

  if (blocks.length === 0) {
    throw new Error('не удалось собрать ни одного блока — проверьте каталог и бюджет');
  }

  const totalSec = overhead + blocks.reduce((s, b) => s + b.sec, 0);

  if (blocks.length === 1) {
    warnings.push(
      `Собрано одно упражнение: бюджет ${budgetSec}с оставляет ${budgetSec - overhead}с ` +
      `на основную часть. Это ожидаемо для короткой сессии (решение A+C).`
    );
  }
  if (totalSec < budgetSec - 60) {
    warnings.push(
      `Сессия заняла ${totalSec}с из ${budgetSec}с: leftover ${budgetSec - totalSec}с. ` +
      `Блоки неделимы, добить нечем — это нормальное поведение, а не баг.`
    );
  }

  return {
    warmupSec: WARMUP_SEC,
    reflectionSec: REFLECTION_SEC,
    totalSec,
    blocks,
    domainsCovered: [...usedDomains],
    warnings,
  };
}

/** @param {number} v */
function clamp01(v) {
  return Math.min(1, Math.max(0, v));
}
