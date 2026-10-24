/**
 * clarity.js — «Индекс ясности».
 *
 * Формула утверждена продуктом (open-questions.md №3). Ключевое решение:
 * множитель регулярности намеренно МЯГКИЙ (0.75 + 0.25·R). Если регулярность
 * влияет сильнее, индекс начинает показывать «сколько дней ты заходил»,
 * а не «насколько ты стал лучше» — ровно та нечестность, в которой бриф
 * обвиняет конкурентов.
 *
 *   S_domain = mean по упражнениям домена от (d · accuracy · speedIndex)
 *   speedIndex = clamp(personalBestRt / currentRt, 0.5, 1.2)
 *   CI_raw  = Σ(w_d · S_d) / Σ(w_d)        только по доменам С ДАННЫМИ
 *   R       = min(1, sessionsLast28 / TARGET_SESSIONS_28D)
 *   CI      = round(100 · CI_raw · (0.75 + 0.25 · R))
 */

/** Сколько тренировок за 28 дней считается полной регулярностью (≈3 в неделю). */
export const TARGET_SESSIONS_28D = 12;

/** Минимум сессий, после которого индекс вообще показываем. */
export const MIN_SESSIONS_FOR_INDEX = 2;

/** @param {number} v @param {number} lo @param {number} hi */
function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v));
}

/**
 * Индекс скорости: насколько текущая реакция близка к личному рекорду.
 *
 * Отношение personalBest / current: чем быстрее пользователь сейчас,
 * тем меньше current и тем больше отношение. Личный рекорд даёт ровно 1.0.
 *
 * Границы [0.5, 1.2]:
 *   - 1.2 сверху — наградить рекорд, но не дать одной удачной пробе раздуть
 *     индекс (+20% к вкладу упражнения — потолок);
 *   - 0.5 снизу — плохой день (недосып, болезнь) не должен обнулять прогресс.
 *
 * @param {number} personalBestRtMs
 * @param {number} currentRtMs
 * @returns {number} 1.0 если данных о времени нет
 */
export function speedIndex(personalBestRtMs, currentRtMs) {
  if (!Number.isFinite(personalBestRtMs) || !Number.isFinite(currentRtMs)) return 1.0;
  if (currentRtMs <= 0 || personalBestRtMs <= 0) return 1.0;
  return clamp(personalBestRtMs / currentRtMs, 0.5, 1.2);
}

/**
 * Вклад одного результата упражнения.
 * @param {{d: number, accuracy: number, meanRtMs?: number, personalBestRtMs?: number}} r
 */
export function exerciseScore(r) {
  const d = clamp(Number(r.d) || 0, 0, 1);
  const acc = clamp(Number(r.accuracy) || 0, 0, 1);
  const sp = speedIndex(r.personalBestRtMs, r.meanRtMs);
  return d * acc * sp;
}

/**
 * Оценка домена: среднее по его упражнениям.
 * @param {Array<{d:number,accuracy:number,meanRtMs?:number,personalBestRtMs?:number}>} results
 */
export function domainScore(results) {
  if (!Array.isArray(results) || results.length === 0) return null;
  const sum = results.reduce((s, r) => s + exerciseScore(r), 0);
  return clamp(sum / results.length, 0, 1.2);
}

/**
 * Множитель регулярности.
 * @param {number} sessionsLast28
 */
export function regularity(sessionsLast28) {
  const n = Number.isFinite(sessionsLast28) ? Math.max(0, sessionsLast28) : 0;
  return clamp(n / TARGET_SESSIONS_28D, 0, 1);
}

/**
 * Индекс ясности.
 *
 * @param {Object} input
 * @param {Array<{domain: string, weight?: number, results: Array}>} input.domains
 *        Домены С РЕЗУЛЬТАТАМИ. Домен без данных передавать не нужно — он
 *        исключается и из числителя, и из знаменателя. Иначе новый пользователь
 *        стартует с CI≈0, что бессмысленно и демотивирует.
 * @param {number} input.sessionsLast28
 * @param {number} [input.totalSessions] общее число сессий за всё время
 * @returns {{value: number|null, raw: number, regularity: number,
 *            breakdown: Array<{domain:string, weight:number, score:number}>,
 *            enoughData: boolean}}
 */
export function clarityIndex({ domains = [], sessionsLast28 = 0, totalSessions = null }) {
  const breakdown = [];
  let num = 0;
  let den = 0;

  for (const dom of domains) {
    const score = domainScore(dom.results);
    if (score === null) continue; // домен без данных — исключаем целиком
    const w = Number.isFinite(dom.weight) && dom.weight > 0 ? dom.weight : 1.0;
    breakdown.push({ domain: dom.domain, weight: w, score: round(score, 4) });
    num += w * score;
    den += w;
  }

  const R = regularity(sessionsLast28);
  const raw = den > 0 ? clamp(num / den, 0, 1) : 0;
  const sessions = totalSessions ?? sessionsLast28;
  const enough = den > 0 && sessions >= MIN_SESSIONS_FOR_INDEX;

  return {
    // null, а не 0: «нет данных» и «ноль баллов» — разные сообщения пользователю
    value: enough ? Math.round(100 * raw * (0.75 + 0.25 * R)) : null,
    raw: round(raw, 4),
    regularity: round(R, 4),
    regularityMultiplier: round(0.75 + 0.25 * R, 4),
    breakdown,
    enoughData: enough,
  };
}

/**
 * «Когнитивный возраст» намеренно НЕ реализован.
 *
 * Из open-questions.md №6: любая такая цифра без возрастных норм — выдумка.
 * Пользователи цитируют число, а не сноску «с оговоркой». Реализуем только
 * после появления датасета возрастных норм. См. CognitiveAgeBlockedError.
 */
export class CognitiveAgeBlockedError extends Error {
  constructor() {
    super(
      'cognitiveAge не реализован: нужны возрастные нормы. ' +
      'См. docs/spec/open-questions.md №6. Показывать выдуманное число нельзя.'
    );
    this.name = 'CognitiveAgeBlockedError';
  }
}

export function cognitiveAge() {
  throw new CognitiveAgeBlockedError();
}

/** @param {number} v @param {number} digits */
function round(v, digits) {
  const f = 10 ** digits;
  return Math.round(v * f) / f;
}
