/**
 * difficulty.js — отображение скалярного индекса сложности в параметры упражнения.
 *
 * Контракт из content/exercises.json:
 *   d ∈ [0, 1], где at0 — значение на самой лёгкой сложности,
 *   at1 — на самой тяжёлой. Направление «что сложнее» закодировано
 *   в самих значениях, отдельное поле не нужно.
 *
 *   int:    round(at0 + (at1 - at0) * d)
 *   float:  at0 + (at1 - at0) * d
 *   enum:   values[round(d * (len(values) - 1))]
 *
 * Единственная причина, по которой это отдельный модуль: интерполяция должна
 * быть IDENTICAL в Kotlin-клиенте, в тестах и в генераторе отчётов. Расхождение
 * в один round() даст разную сложность на клиенте и на сервере.
 */

/**
 * @param {number} d индекс сложности
 * @returns {number} d, зажатый в [0, 1]
 */
export function clampIndex(d) {
  if (!Number.isFinite(d)) {
    throw new TypeError(`difficulty index must be a finite number, got ${d}`);
  }
  return Math.min(1, Math.max(0, d));
}

/**
 * Интерполяция одного параметра.
 * @param {{type: 'int'|'float'|'enum', at0?: number, at1?: number, values?: unknown[]}} param
 * @param {number} d
 */
export function interpParam(param, d) {
  const t = clampIndex(d);
  switch (param.type) {
    case 'int': {
      const v = param.at0 + (param.at1 - param.at0) * t;
      // Math.round, а не ~~ или |0: они ломаются на отрицательных и на >2^31
      return Math.round(v);
    }
    case 'float': {
      const v = param.at0 + (param.at1 - param.at0) * t;
      // 3 знака достаточно: параметры вроде targetRate=0.18 не требуют больше
      return Math.round(v * 1000) / 1000;
    }
    case 'enum': {
      const n = param.values.length;
      if (n === 0) throw new Error(`enum param '${param.key}' has no values`);
      const idx = Math.min(n - 1, Math.max(0, Math.round(t * (n - 1))));
      return param.values[idx];
    }
    default:
      throw new Error(`unknown param type '${param.type}' for '${param.key}'`);
  }
}

/**
 * Все параметры упражнения при данной сложности.
 * @param {{difficulty: {params: unknown[]}}} exercise
 * @param {number} d
 * @returns {Record<string, unknown>}
 */
export function resolveParams(exercise, d) {
  const out = {};
  for (const p of exercise.difficulty.params) {
    out[p.key] = interpParam(p, d);
  }
  return out;
}

/**
 * Таблица кривых сложности — для отладки и ревью.
 * @returns {Array<{key: string, at: unknown[]}>}
 */
export function difficultyTable(exercise, points = [0, 0.25, 0.5, 0.75, 1]) {
  return exercise.difficulty.params.map((p) => ({
    key: p.key,
    type: p.type,
    at: points.map((d) => interpParam(p, d)),
  }));
}
