/**
 * staircase.js — трансформированная лестница Левитта (1-up/3-down).
 *
 * Правило: сложность ПОВЫШАЕТСЯ после 3 подряд правильных ответов
 *          и ПОНИЖАЕТСЯ после 1 неправильного.
 *
 * Точка схождения — 79.4% правильных (Levitt, 1971). Это единственное правило
 * стандартного семейства, попадающее в целевой диапазон брифа 75–80%:
 *   1-up/2-down → 70.7%      1-up/3-down → 79.4%      1-up/4-down → 84.1%
 *
 * ─── ПРОТИВОРЕЧИЕ, О КОТОРОМ НАДО ЗНАТЬ ────────────────────────────────────
 * «Защита от фрустрации» (не понижать сложность чаще N раз подряд) подавляет
 * step-down'ы, а значит СДВИГАЕТ точку схождения вверх: пользователь реже
 * получает облегчение, фактическая точность падает ниже 79.4%.
 *
 * Поэтому antiFrustration по умолчанию ВЫКЛЮЧЕН, а измерение психометрики
 * и продуктовое сглаживание разведены:
 *   - measurement mode  (antiFrustration: null) — чистая лестница, 79.4%
 *   - production mode   (antiFrustration: {...}) — мягче для пользователя,
 *                                                  но фактическая точность ниже
 * Оба режима покрыты тестами: tests/staircase.test.js измеряет фактическую
 * точку схождения в каждом и фиксирует drift.
 *
 * Альтернатива, если drift окажется неприемлем: сглаживать только ПРЕЗЕНТАЦИЮ
 * (не показывать пользователю снижение уровня), оставив алгоритм чистым.
 */

const DEFAULTS = {
  /** сколько подряд правильных нужно для повышения сложности */
  correctsToStepUp: 3,
  /** сколько подряд ошибок нужно для понижения (у Левитта 1) */
  errorsToStepDown: 1,
  /** начальный размер шага — крупный, для быстрой сходимости */
  initialStep: 0.08,
  /** шаг уменьшается вдвое после каждого разворота, начиная с этого номера */
  halveAfterReversals: 2,
  /** пол шага */
  minStep: 0.02,
  /** границы индекса. Нижняя 0.05, а не 0: d=0 может дать вырожденно лёгкую задачу */
  floor: 0.05,
  ceiling: 1.0,
  /**
   * Защита от фрустрации. null = выключена (чистая психометрика).
   * maxConsecutiveDowns — сколько понижений подряд допустимо;
   * pauseTrials — сколько проб после этого сложность не меняется.
   */
  antiFrustration: null,
};

export class Staircase {
  /** @param {number} d0 стартовая сложность @param {Partial<typeof DEFAULTS>} options */
  constructor(d0 = 0.3, options = {}) {
    this.opt = { ...DEFAULTS, ...options };
    const { floor, ceiling } = this.opt;
    if (floor >= ceiling) throw new RangeError(`floor (${floor}) must be < ceiling (${ceiling})`);
    if (this.opt.correctsToStepUp < 1) throw new RangeError('correctsToStepUp must be >= 1');
    if (this.opt.errorsToStepDown < 1) throw new RangeError('errorsToStepDown must be >= 1');

    this.d = clamp(d0, floor, ceiling);
    this.step = this.opt.initialStep;
    this.correctRun = 0;
    this.errorRun = 0;
    this.reversals = [];
    this.lastDirection = 0;

    // диагностика
    this.trials = 0;
    this.correctCount = 0;
    this.history = []; // {trial, correct, d, direction, step}
    this.consecutiveDowns = 0;
    this.pauseRemaining = 0;
  }

  /** Текущая сложность. */
  get difficulty() {
    return this.d;
  }

  /** Фактическая доля правильных с начала работы контроллера. */
  get observedAccuracy() {
    return this.trials === 0 ? 0 : this.correctCount / this.trials;
  }

  /**
   * Обработать один ответ.
   * @param {boolean} isCorrect
   * @returns {{changed: boolean, direction: number, d: number}} что произошло
   */
  respond(isCorrect) {
    if (typeof isCorrect !== 'boolean') {
      throw new TypeError(`respond() expects a boolean, got ${typeof isCorrect}`);
    }
    this.trials += 1;
    if (isCorrect) this.correctCount += 1;

    if (isCorrect) {
      this.correctRun += 1;
      this.errorRun = 0;
    } else {
      this.errorRun += 1;
      this.correctRun = 0;
    }

    let direction = 0;
    if (this.correctRun >= this.opt.correctsToStepUp) {
      direction = +1;
      this.correctRun = 0;
    } else if (this.errorRun >= this.opt.errorsToStepDown) {
      direction = -1;
      this.errorRun = 0;
    }

    const before = this.d;
    if (direction !== 0) {
      direction = this.#applyMove(direction);
    } else if (this.pauseRemaining > 0) {
      this.pauseRemaining -= 1;
    }

    this.history.push({
      trial: this.trials,
      correct: isCorrect,
      d: this.d,
      direction,
      step: this.step,
    });

    return { changed: this.d !== before, direction, d: this.d };
  }

  /**
   * Применить шаг с учётом разворотов, halving и защиты от фрустрации.
   * @returns {number} фактическое направление (0 если шаг подавлен)
   */
  #applyMove(direction) {
    const af = this.opt.antiFrustration;

    // пауза после серии понижений
    if (this.pauseRemaining > 0) {
      this.pauseRemaining -= 1;
      return 0;
    }

    // защита от фрустрации: не понижаем больше N раз подряд
    if (af && direction === -1) {
      if (this.consecutiveDowns >= af.maxConsecutiveDowns) {
        this.pauseRemaining = af.pauseTrials;
        this.consecutiveDowns = 0;
        return 0; // понижение подавлено
      }
      this.consecutiveDowns += 1;
    } else if (direction === +1) {
      this.consecutiveDowns = 0;
    }

    // разворот → фиксируем точку и уменьшаем шаг (Levitt: halving).
    // Точка разворота — уровень ДО шага, поэтому push до изменения this.d.
    if (this.lastDirection !== 0 && direction !== this.lastDirection) {
      this.reversals.push(this.d);
      if (this.reversals.length >= this.opt.halveAfterReversals) {
        this.step = Math.max(this.opt.minStep, this.step / 2);
      }
    }
    this.lastDirection = direction;

    this.d = clamp(this.d + direction * this.step, this.opt.floor, this.opt.ceiling);
    return direction;
  }

  /**
   * Оценка порога: среднее по разворотам, первые два отбрасываются.
   *
   * Отбрасывание обязательно: до схождения лестница движется с систематическим
   * смещением в сторону стартовой точки, и включение ранних разворотов
   * занижает/завышает оценку в зависимости от d0.
   *
   * @param {number} [skip=2] сколько первых разворотов отбросить
   * @param {number} [max=4] сколько разворотов усреднять
   * @returns {number|null} null если разворотов недостаточно
   */
  threshold(skip = 2, max = 4) {
    const usable = this.reversals.slice(skip, skip + max);
    if (usable.length === 0) return null;
    return usable.reduce((s, v) => s + v, 0) / usable.length;
  }

  /** Снимок состояния — для сохранения между сессиями. */
  toJSON() {
    return {
      d: this.d,
      step: this.step,
      correctRun: this.correctRun,
      errorRun: this.errorRun,
      reversals: this.reversals,
      lastDirection: this.lastDirection,
      trials: this.trials,
      correctCount: this.correctCount,
      consecutiveDowns: this.consecutiveDowns,
      pauseRemaining: this.pauseRemaining,
      options: this.opt,
    };
  }

  /** @param {ReturnType<Staircase['toJSON']>} state */
  static fromJSON(state) {
    const s = new Staircase(state.d, state.options);
    Object.assign(s, {
      step: state.step,
      correctRun: state.correctRun,
      errorRun: state.errorRun,
      reversals: [...state.reversals],
      lastDirection: state.lastDirection,
      trials: state.trials,
      correctCount: state.correctCount,
      consecutiveDowns: state.consecutiveDowns,
      pauseRemaining: state.pauseRemaining,
    });
    return s;
  }
}

/** @param {number} v @param {number} lo @param {number} hi */
function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v));
}

/**
 * Теоретическая точка схождения для правила «N подряд правильных → вверх,
 * M ошибок → вниз». Значения из Levitt (1971) для M=1.
 * @param {number} n
 */
export function theoreticalConvergence(n) {
  const KNOWN = { 1: 0.5, 2: 0.7071, 3: 0.794, 4: 0.8409, 5: 0.8676 };
  return KNOWN[n] ?? null;
}
