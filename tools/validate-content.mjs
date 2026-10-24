#!/usr/bin/env node
/**
 * validate-content.mjs — валидация каталога доменов и упражнений.
 *
 *   node tools/validate-content.mjs            # обычная проверка
 *   node tools/validate-content.mjs --report   # + таблица кривых сложности
 *
 * Ноль зависимостей: только встроенные модули Node.
 * Exit code 1 при любой ошибке — подключается к CI.
 *
 * Проверяет не только схему, но и ПРОДУКТОВЫЕ инварианты:
 *   - квота MVP «10–12 упражнений» из дорожной карты брифа
 *   - покрытие всех 8 доменов упражнениями из MVP
 *   - онбординг оценивает ровно 4 домена (память, внимание, скорость, логика)
 *   - сессию «3 минуты» физически можно собрать
 *   - параметры сложности реально меняются (at0 !== at1)
 */

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  MIN_SESSION_SEC, WARMUP_SEC, REFLECTION_SEC, SESSION_PRESETS_SEC,
  blockSec, composeSession,
} from '../src/engine/session-composer.js';
import { interpParam } from '../src/engine/difficulty.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const WANT_REPORT = process.argv.includes('--report');

const errors = [];
const warnings = [];
const err = (m) => errors.push(m);
const warn = (m) => warnings.push(m);

const C = {
  red: (s) => `\x1b[31m${s}\x1b[0m`,
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s) => `\x1b[33m${s}\x1b[0m`,
  dim: (s) => `\x1b[2m${s}\x1b[0m`,
  bold: (s) => `\x1b[1m${s}\x1b[0m`,
};

// ─── загрузка ──────────────────────────────────────────────────────────────
function loadJson(rel) {
  try {
    return JSON.parse(readFileSync(resolve(ROOT, rel), 'utf8'));
  } catch (e) {
    err(`${rel}: не читается — ${e.message}`);
    return null;
  }
}

const domainsDoc = loadJson('content/domains.json');
const exDoc = loadJson('content/exercises.json');
if (!domainsDoc || !exDoc) {
  console.error(C.red('Критическая ошибка чтения файлов.'));
  process.exit(1);
}

const domains = domainsDoc.domains ?? [];
const exercises = exDoc.exercises ?? [];

// ─── 1. домены ─────────────────────────────────────────────────────────────
{
  const seen = new Set();
  const HEX = /^#[0-9A-Fa-f]{6}$/;
  for (const d of domains) {
    const tag = d.id ?? '(без id)';
    if (!d.id) err('domain: отсутствует id');
    else if (seen.has(d.id)) err(`domain ${tag}: дублирующийся id`);
    seen.add(d.id);

    if (typeof d.order !== 'number') err(`domain ${tag}: order должен быть числом`);
    if (!d.name?.ru) err(`domain ${tag}: нет name.ru`);
    if (!d.lifeTask?.ru) err(`domain ${tag}: нет lifeTask.ru`);
    if (!HEX.test(d.color ?? '')) err(`domain ${tag}: color '${d.color}' не валидный #RRGGBB`);
    if (typeof d.weight !== 'number' || d.weight <= 0 || d.weight > 2) {
      err(`domain ${tag}: weight=${d.weight} вне допустимого диапазона (0, 2]`);
    }
    if (typeof d.onboardingAssessed !== 'boolean') {
      err(`domain ${tag}: onboardingAssessed должен быть boolean`);
    }
  }

  const EXPECTED_DOMAINS = 8;
  if (domains.length !== EXPECTED_DOMAINS) {
    err(`доменов ${domains.length}, по брифу должно быть ${EXPECTED_DOMAINS}`);
  }
  const orders = domains.map((d) => d.order).sort((a, b) => a - b);
  const contiguous = orders.every((o, i) => o === i + 1);
  if (!contiguous) err(`order доменов не сплошной 1..N: [${orders.join(', ')}]`);

  // онбординг по брифу: память, внимание, скорость, логика → 4 домена
  const onb = domains.filter((d) => d.onboardingAssessed).map((d) => d.id);
  if (onb.length !== 4) {
    err(`онбординг оценивает ${onb.length} доменов, по брифу (раздел 5) должно быть 4: [${onb.join(', ')}]`);
  }
}

// ─── 2. упражнения ─────────────────────────────────────────────────────────
const domainIds = new Set(domains.map((d) => d.id));
const EVIDENCE = new Set(['A', 'B', 'c'.toUpperCase()]);
const PTYPES = new Set(['int', 'float', 'enum']);
const seenEx = new Set();

for (const ex of exercises) {
  const tag = ex.id ?? '(без id)';

  if (!ex.id) err('exercise: отсутствует id');
  else if (seenEx.has(ex.id)) err(`exercise ${tag}: дублирующийся id`);
  seenEx.add(ex.id);

  if (!ex.id || !/^[a-z][a-z0-9_]*$/.test(ex.id)) {
    err(`exercise ${tag}: id должен быть snake_case`);
  }
  if (!domainIds.has(ex.domain)) {
    err(`exercise ${tag}: domain '${ex.domain}' не существует в domains.json`);
  }
  if (typeof ex.mvp !== 'boolean') err(`exercise ${tag}: mvp должен быть boolean`);
  if (!ex.name?.ru) err(`exercise ${tag}: нет name.ru`);
  if (!ex.tagline?.ru) warn(`exercise ${tag}: нет tagline.ru`);
  if (!ex.description?.ru || ex.description.ru.length < 40) {
    err(`exercise ${tag}: description.ru отсутствует или слишком короткий`);
  }

  // научная база — ключевое требование «научной честности» из брифа
  const sc = ex.science ?? {};
  if (!sc.paradigm) err(`exercise ${tag}: нет science.paradigm`);
  if (!EVIDENCE.has(sc.paradigmValidity)) {
    err(`exercise ${tag}: paradigmValidity='${sc.paradigmValidity}' не в {A,B,C}`);
  }
  if (!EVIDENCE.has(sc.transferEvidence)) {
    err(`exercise ${tag}: transferEvidence='${sc.transferEvidence}' не в {A,B,C}`);
  }
  if (!sc.notes || sc.notes.length < 30) {
    warn(`exercise ${tag}: science.notes пустые — для «научно-честного» продукта это обязательное поле`);
  }

  // метрики и IO
  if (!Array.isArray(ex.metrics) || ex.metrics.length === 0) err(`exercise ${tag}: metrics пуст`);
  if (!ex.metrics?.includes('level')) warn(`exercise ${tag}: metrics не содержит 'level' — адаптивный движок его ожидает`);
  if (!Array.isArray(ex.input) || ex.input.length === 0) err(`exercise ${tag}: input пуст`);
  if (typeof ex.requiresAudio !== 'boolean') err(`exercise ${tag}: requiresAudio должен быть boolean`);
  if (typeof ex.durationSec !== 'number' || ex.durationSec < 30 || ex.durationSec > 900) {
    err(`exercise ${tag}: durationSec=${ex.durationSec} вне диапазона [30, 900]`);
  }
  if (!Array.isArray(ex.openIssues)) err(`exercise ${tag}: openIssues должен быть массивом (можно пустым)`);

  // trial
  const t = ex.trial ?? {};
  if (!(t.perBlock > 0)) err(`exercise ${tag}: trial.perBlock должен быть > 0`);
  if (!(t.blocksPerSession > 0)) err(`exercise ${tag}: trial.blocksPerSession должен быть > 0`);

  // параметры сложности
  const dp = ex.difficulty?.params;
  if (!Array.isArray(dp) || dp.length === 0) {
    err(`exercise ${tag}: difficulty.params пуст — упражнение неуправляемо адаптивным движком`);
    continue;
  }
  const keys = new Set();
  for (const p of dp) {
    const pk = `${tag}.${p.key ?? '?'}`;
    if (!p.key) err(`${tag}: параметр без key`);
    else if (keys.has(p.key)) err(`${pk}: дублирующийся key`);
    keys.add(p.key);

    if (!PTYPES.has(p.type)) err(`${pk}: type='${p.type}' не в {int,float,enum}`);
    if (!p.desc) warn(`${pk}: нет desc`);

    if (p.type === 'enum') {
      if (!Array.isArray(p.values) || p.values.length < 2) {
        err(`${pk}: enum должен иметь >= 2 значений`);
      }
    } else {
      if (typeof p.at0 !== 'number' || typeof p.at1 !== 'number') {
        err(`${pk}: для ${p.type} нужны числовые at0 и at1`);
        continue;
      }
      if (p.at0 === p.at1) err(`${pk}: at0 === at1 — параметр не влияет на сложность`);
      if (p.type === 'int' && (!Number.isInteger(p.at0) || !Number.isInteger(p.at1))) {
        err(`${pk}: type=int, но at0/at1 не целые`);
      }
      // семантические границы. Отрицательное время — баг; ноль легален
      // (напр. story_recall.delaySec=0 означает немедленное воспроизведение).
      if (/Ms$/.test(p.key) && (p.at0 < 0 || p.at1 < 0)) err(`${pk}: длительность в мс не может быть отрицательной`);
      if (/Sec$/.test(p.key) && (p.at0 < 0 || p.at1 < 0)) err(`${pk}: длительность в сек не может быть отрицательной`);
      if (/(Ms|Sec)$/.test(p.key) && p.at0 === 0 && p.at1 === 0) err(`${pk}: оба значения нулевые — шаг не имеет длительности`);
      if (/Rate$/.test(p.key) && (p.at0 < 0 || p.at0 > 1 || p.at1 < 0 || p.at1 > 1)) {
        err(`${pk}: Rate должен быть в [0,1], получено at0=${p.at0} at1=${p.at1}`);
      }
      if (/Count$/.test(p.key) && (p.at0 < 1 || p.at1 < 1)) err(`${pk}: Count должен быть >= 1`);
    }
  }
}

// ─── 3. продуктовые инварианты ─────────────────────────────────────────────
const mvp = exercises.filter((e) => e.mvp);

// дорожная карта: «MVP: 10–12 упражнений (по 1–2 на домен)»
if (mvp.length < 10 || mvp.length > 12) {
  err(`MVP содержит ${mvp.length} упражнений, дорожная карта требует 10–12`);
}

// каждый домен должен быть представлен в MVP
const uncovered = domains.filter((d) => !mvp.some((e) => e.domain === d.id));
if (uncovered.length) {
  err(`домены без MVP-упражнений: ${uncovered.map((d) => d.id).join(', ')}`);
}

// «по 1–2 на домен» из дорожной карты
for (const d of domains) {
  const n = mvp.filter((e) => e.domain === d.id).length;
  if (n > 2) warn(`домен ${d.id}: ${n} упражнений в MVP (дорожная карта: 1–2)`);
}

// Бюджет сессии.
//
// Единственный источник правды — src/engine/session-composer.js. Раньше здесь
// был свой хардкод «3 минуты», и он разошёлся с движком после продуктового
// решения A+C (минимум 5 минут). Дублирование констант между валидатором
// и рантаймом — это ровно тот класс багов, который CI не поймает.
const MAIN_BUDGET_SEC = MIN_SESSION_SEC - WARMUP_SEC - REFLECTION_SEC;

const cheapest = [...mvp]
  .map((e) => ({ id: e.id, block: blockSec(e) }))
  .sort((a, b) => a.block - b.block);
const minOne = cheapest[0]?.block ?? 0;

if (minOne > MAIN_BUDGET_SEC) {
  err(`Самый короткий блок MVP-упражнения (${minOne}с) не влезает в основную часть минимальной сессии (${MAIN_BUDGET_SEC}с). MIN_SESSION_SEC нужно поднять.`);
}

// Реальная собираемость: композитор должен уметь собрать сессию на каждом пресете.
for (const preset of SESSION_PRESETS_SEC) {
  try {
    const s = composeSession({ budgetSec: preset, catalog: mvp });
    if (s.blocks.length === 0) err(`composeSession(${preset}) вернул 0 блоков`);
    if (s.totalSec > preset) err(`composeSession(${preset}) превысил бюджет: ${s.totalSec}с`);
  } catch (e) {
    err(`composeSession(${preset})с упал: ${e.message}`);
  }
}

// упражнения без openIssues при спорной научной базе
for (const ex of exercises) {
  if (ex.science?.transferEvidence === 'C' && (ex.openIssues?.length ?? 0) === 0) {
    warn(`${ex.id}: transferEvidence=C, но openIssues пуст — для «научно-честного» продукта стоит зафиксировать оговорку`);
  }
}

// ─── 4. отчёт о кривых сложности ───────────────────────────────────────────
// Используется interpParam из движка, а не локальная копия: расхождение в
// один round() дало бы разную сложность в отчёте и в рантайме.
const interp = interpParam;

if (WANT_REPORT) {
  console.log(`\n${C.bold('Кривые сложности (d = 0 → 0.5 → 1)')}\n`);
  for (const ex of exercises) {
    const flag = ex.mvp ? C.green('MVP ') : C.dim('later');
    console.log(`${flag} ${C.bold(ex.id)} ${C.dim(`[${ex.domain}] ${ex.science?.paradigm ?? ''}`)}`);
    for (const p of ex.difficulty.params) {
      const cells = [0, 0.5, 1].map((d) => String(interp(p, d)));
      const arrow = cells[0] === cells[2] ? '  ' : cells[0] < cells[2] ? '↗' : '↘';
      console.log(`    ${p.key.padEnd(22)} ${cells.map((c) => c.padStart(9)).join(' → ')} ${arrow}`);
    }
    console.log();
  }
}

// ─── 5. итог ───────────────────────────────────────────────────────────────
console.log(C.bold('\n═══ Валидация контента ═══'));
console.log(`  доменов:      ${domains.length}`);
console.log(`  упражнений:   ${exercises.length} (${C.green(`MVP: ${mvp.length}`)}, later: ${exercises.length - mvp.length})`);
const byDomain = domains.map((d) => `${d.id}=${exercises.filter((e) => e.domain === d.id).length}`);
console.log(`  покрытие:     ${C.dim(byDomain.join(' '))}`);
console.log(`  параметры:    ${exercises.reduce((s, e) => s + (e.difficulty?.params?.length ?? 0), 0)} кривых сложности`);
console.log(`  открытые вопросы: ${exercises.reduce((s, e) => s + (e.openIssues?.length ?? 0), 0)} в упражнениях`);
console.log(`  сессии:         ${MIN_SESSION_SEC}с мин., основная часть ${MAIN_BUDGET_SEC}с`);
console.log(`  cheapest block: ${cheapest[0]?.id} = ${cheapest[0]?.block}с`);

if (warnings.length) {
  console.log(`\n${C.yellow(`Предупреждений: ${warnings.length}`)}`);
  for (const w of warnings) console.log(`  ${C.yellow('!')} ${w}`);
}
if (errors.length) {
  console.log(`\n${C.red(`ОШИБОК: ${errors.length}`)}`);
  for (const e of errors) console.log(`  ${C.red('✗')} ${e}`);
  console.log();
  process.exit(1);
}
console.log(`\n${C.green('✔ Контент валиден')}\n`);
