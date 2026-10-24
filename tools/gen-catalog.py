#!/usr/bin/env python3
"""
gen-catalog.py — генератор content/exercises.json из компактной таблицы.

Этот скрипт — ИСТОЧНИК ПРАВДЫ для каталога упражнений. exercises.json является
порождаемым артефактом и коммитится, потому что его читают клиент, CI и
валидатор. Правки вносятся СЮДА, затем:

    python3 tools/gen-catalog.py && node tools/validate-content.mjs

Генератор держит все 59 упражнений в одном месте и попутно проверяет
целостность: существование доменов, архетипов и тегов, уникальность id,
допустимость оценок доказательности. Это ловит опечатки, которые валидатор
JSON-схемой не поймал бы.

Слияние трёх источников:
  1. Каталог из 50 тренировок продуктового брифа (номера 1–50) — приоритет.
  2. «Базовый слой» раздела 1.7 брифа, которого нет в списке 50: Шульте,
     классический Струп, task-switching (номера 51–53).
  3. Каталог v1.0.0: судоку, анаграммы, «слова из слова», «10 способов»,
     «Истории», RSVP (номера 54–59).

Дубликаты схлопнуты: v1 rapid_count → №26 speed_arithmetic,
v1 pattern_finding → №38 visual_patterns, v1 matchstick_puzzles → №35.
"""
import json, collections, sys

# ─── допустимые значения (сверяются с content/*.json) ────────────────────────
EVIDENCE = ("A", "B", "C", "D")

E = []

def add(no, id, name, tagline, desc, dom, arch, par, pv, te, notes, tags,
        params, perBlock, blocks, metrics, inp, audio, dur,
        mvp=False, src="generated", issues=None, removed=False, extra=None):
    E.append(dict(no=no, id=id, name=name, tagline=tagline, desc=desc, dom=dom,
                  arch=arch, par=par, pv=pv, te=te, notes=notes, tags=tags,
                  params=params, perBlock=perBlock, blocks=blocks, metrics=metrics,
                  inp=inp, audio=audio, dur=dur, mvp=mvp, src=src,
                  issues=issues or [], removed=removed, extra=extra or {}))

I = lambda k, t, a0, a1, d: dict(key=k, type=t, at0=a0, at1=a1, desc=d)
N = lambda k, vals, d: dict(key=k, type="enum", values=vals, desc=d)

# ══════════════════════════════════════════════════════════ БЛОК A: пространство
add(1, "mental_rotation_3d", "Мысленное вращение 3D-блоков", "Отличить поворот от зеркального двойника",
    "Эталонная конструкция из кубов и четыре варианта: один — повёрнутый эталон, остальные зеркальные или искажённые. Углы ротации 45°, 90°, 135°, 180°.",
    "spatial_reasoning", "single_choice", "mental rotation (Shepard & Metzler, 1971)", "A", "B",
    "Классическая парадигма. Линейная зависимость времени реакции от угла поворота — один из самых устойчивых эффектов в когнитивной психологии. Тренируемость показана (Uttal et al.).",
    ["paradigmFamily:mental-rotation", "delivery:offline-native", "risk:evidence-solid"],
    [I("cubeCount", "int", 4, 10, "Число кубов в конструкции"),
     I("rotationDeg", "int", 45, 180, "Угол ротации"),
     N("mirrorRatio", [0.0, 0.25, 0.5], "Доля зеркальных двойников среди дистракторов"),
     I("responseWindowMs", "int", 12000, 4000, "Окно на ответ")],
    10, 2, ["accuracy", "reactionTimeMs", "angleEffectSlope", "level"], ["touch"], False, 180,
    mvp=True, issues=["Генератор должен исключать неоднозначные конструкции: если поворот эталона совпадает с его зеркалом (фигуры с осевой симметрией), задача нерешаема. Нужна проверка на хиральность."])

add(2, "cube_nets", "Развёртки куба", "Какой куб сложится из этой развёртки",
    "Плоская развёртка из шести квадратов с узорами на гранях. Нужно выбрать куб, который из неё получится, или указать противоположные грани.",
    "spatial_reasoning", "single_choice", "cube net folding", "B", "B",
    "Входит в батареи пространственных тренировок (Foldmetry). Как измеритель валидна; перенос умеренный.",
    ["paradigmFamily:mental-folding", "delivery:offline-native", "risk:evidence-mixed"],
    [I("netKind", "int", 1, 3, "Класс развёртки: 1 — стандартные 11 развёрток куба, 3 — нестандартные с ловушками"),
     I("patternComplexity", "int", 1, 4, "Сложность узоров на гранях"),
     I("responseWindowMs", "int", 20000, 6000, "Окно на ответ")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 180,
    issues=["Всего существует 11 развёрток куба. Без узоров на гранях большинство задач тривиальны — разнообразие обеспечивается именно разметкой граней, а не формой развёртки."])

add(3, "paper_folding", "Складывание бумаги с проколами", "Где окажутся отверстия после разворота",
    "Лист складывается 2–4 раза и прокалывается. Нужно выбрать схему отверстий после полного разворота.",
    "spatial_reasoning", "single_choice", "paper folding test", "A", "B",
    "Стандартная задача батарей пространственных способностей (Paper Folding Test). Валидность высокая.",
    ["paradigmFamily:mental-folding", "delivery:offline-native", "risk:evidence-solid"],
    [I("foldCount", "int", 2, 4, "Число сложений"),
     I("holeCount", "int", 1, 4, "Число проколов"),
     N("foldSymmetry", ["single_axis", "two_axis", "diagonal"], "Тип симметрии сложений"),
     I("responseWindowMs", "int", 20000, 6000, "Окно на ответ")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 180)

add(4, "perspective_taking", "Смена перспективы", "Как конструкция выглядит с другой точки",
    "Трёхмерная конструкция и позиция наблюдателя. Нужно выбрать вид с противоположной стороны, сверху или из заданной точки.",
    "spatial_reasoning", "single_choice", "perspective taking", "B", "B",
    "Компонент пространственного мышления, тренируемый в интерактивных средах. Отдельных мета-анализов по переносу мало.",
    ["paradigmFamily:mental-rotation", "delivery:offline-native", "risk:evidence-mixed"],
    [I("constructionSize", "int", 4, 9, "Число элементов конструкции"),
     N("viewTransformation", ["opposite", "above", "arbitrary", "arbitrary_with_occlusion"], "Тип требуемого преобразования вида"),
     I("responseWindowMs", "int", 15000, 5000, "Окно на ответ")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 180)

add(5, "block_counting", "Подсчёт кубов, включая скрытые", "Сколько кубов в конструкции на самом деле",
    "Показана пирамида или конструкция из кубов. Нужно определить общее число кубов, включая невидимые, но необходимые для устойчивости.",
    "spatial_reasoning", "numeric_input", "block counting / hidden elements", "B", "C",
    "Классический тест пространственного мышления. Как тренажёр перенос не показан.",
    ["paradigmFamily:planning", "delivery:offline-native", "risk:evidence-weak"],
    [I("stackHeight", "int", 2, 5, "Высота конструкции в слоях"),
     I("baseWidth", "int", 3, 5, "Ширина основания"),
     N("hangingAllowed", [False, True], "Допускаются ли висящие элементы, меняющие правило подсчёта"),
     I("responseWindowMs", "int", 20000, 7000, "Окно на ответ")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch", "keyboard"], False, 150,
    issues=["Правило «включая скрытые» должно быть однозначным: считаются ли кубы, на которых ничего не стоит, но которые требуются для устойчивости? Формулировка определяет ответ, и её надо зафиксировать в контенте, а не отдавать на усмотрение генератора."])

add(6, "cross_sections", "Сечения объёмных тел", "Какая фигура получится при рассечении",
    "Объёмное тело (куб, цилиндр, конус, комбинация) и плоскость сечения. Нужно выбрать форму сечения.",
    "spatial_reasoning", "single_choice", "cross-section task", "B", "C",
    "Задача на пространственную визуализацию. Академически валидна, данных о тренировочном переносе мало.",
    ["paradigmFamily:mental-folding", "delivery:offline-native", "risk:evidence-weak"],
    [N("solidKind", ["cube", "cylinder", "cone", "prism", "composite"], "Тип тела"),
     N("planeAngle", ["axis_parallel", "axis_perpendicular", "oblique"], "Ориентация секущей плоскости"),
     I("responseWindowMs", "int", 15000, 5000, "Окно на ответ")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 150,
    issues=["Перенос не показан: упражнение измеряет и тренирует решение задач на сечения, но не пространственное мышление в целом. В описании для пользователя не обещать «развитие пространственного интеллекта»."])

add(7, "gear_trains", "Шестерёнки", "Куда повернётся последняя шестерня",
    "Система связанных шестерёнок. Нужно определить направление вращения последней или соотношение скоростей.",
    "spatial_reasoning", "single_choice", "gear train reasoning", "B", "C",
    "Компонент пространственно-механического рассуждения, входит в технические тесты способностей. Перенос как тренировки не изучался.",
    ["paradigmFamily:constraint-satisfaction", "delivery:offline-native", "risk:evidence-weak"],
    [I("gearCount", "int", 3, 9, "Число шестерёнок в цепи"),
     N("gearSizes", ["uniform", "mixed_two", "mixed_many"], "Одинаковые или разные размеры"),
     N("questionKind", ["direction", "direction_and_ratio"], "Что спрашивается"),
     I("responseWindowMs", "int", 15000, 5000, "Окно на ответ")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 150,
    issues=["Перенос не показан. Задача валидна как компонент технических тестов способностей, но тренировка не улучшает механическое рассуждение в целом — в описании не обещать этого."])

add(8, "mirror_completion", "Зеркальная достройка узора", "Достроить вторую половину симметрии",
    "Дана левая половина симметричного узора — геометрического или буквенного. Нужно выбрать или достроить правую половину в зеркальном отражении.",
    "spatial_reasoning", "single_choice", "symmetry detection / mental rotation", "A", "B",
    "ВАЖНО: бриф обосновывал это упражнение «зеркальным рисованием как методом активации межполушарных связей». Это неверная опора — см. science-audit.md, позиция №2. Реальная парадигма здесь — обнаружение симметрии и мысленное вращение, у них база крепкая. Обоснование исправлено, упражнение оставлено.",
    ["paradigmFamily:mental-rotation", "delivery:offline-native", "risk:evidence-solid"],
    [N("symmetryKind", ["axial_vertical", "axial_horizontal", "central"], "Тип симметрии"),
     I("elementCount", "int", 4, 12, "Число элементов узора"),
     N("stimulusKind", ["geometric", "letterform", "mixed"], "Природа узора"),
     I("responseWindowMs", "int", 12000, 4000, "Окно на ответ")],
    10, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 150)

add(9, "grid_dictation", "Графический диктант по клеткам", "Построить фигуру по командам",
    "Последовательность команд («2 клетки вправо, 1 вниз, 3 влево…») — нужно построить фигуру на сетке. Обратный режим: по готовой фигуре составить последовательность.",
    "spatial_reasoning", "sequence_recall", "graphical dictation", "B", "C",
    "Классический метод развития ориентировки на плоскости, широко используется в русскоязычной педагогике. Строгих РКИ по переносу нет.",
    ["paradigmFamily:planning", "delivery:offline-native", "risk:evidence-weak"],
    [I("instructionLength", "int", 4, 12, "Число команд"),
     I("maxStep", "int", 1, 4, "Максимальная длина одного шага"),
     N("directionSet", ["cardinal", "cardinal_diagonal"], "Допустимые направления"),
     N("mode", ["build_from_commands", "commands_from_figure"], "Прямой или обратный режим")],
    6, 2, ["accuracy", "completionSec", "level"], ["touch"], False, 180,
    issues=["Обратный режим неоднозначен: одну и ту же фигуру можно описать разными последовательностями. Принимать надо любую валидную, а не единственную эталонную, иначе пользователь получит незаслуженную ошибку."])

add(10, "assembly_3d", "3D-сборка по видам", "Собрать конструкцию из блоков",
    "Даны несколько видов конструкции с разных ракурсов. Нужно собрать её из предложенных блоков или выбрать недостающий блок.",
    "spatial_reasoning", "single_choice", "multi-view assembly", "B", "B",
    "Интегрирует mental rotation, perspective taking и block counting — поэтому как тренировка интереснее отдельных компонентов, но и дороже в реализации.",
    ["paradigmFamily:mental-rotation", "delivery:offline-native", "risk:evidence-mixed"],
    [I("blockCount", "int", 4, 9, "Число блоков"),
     I("viewCount", "int", 2, 3, "Сколько ракурсов показано"),
     N("distractorKind", ["none", "extra_blocks", "rotated_blocks"], "Тип лишнего материала"),
     I("responseWindowMs", "int", 25000, 8000, "Окно на ответ")],
    6, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 200,
    issues=["Требуется 3D-рендеринг или изометрическая проекция. Изометрию можно рисовать на canvas без 3D-движка — это сильно дешевле, и для MVP достаточно."])

# ═════════════════════════════════════════════════════════════ БЛОК B: память
add(11, "matrix_recall", "Матрица памяти", "Запомни узор и воспроизведи",
    "На сетке 4×4 или 5×5 на несколько секунд загораются клетки, затем сетка гаснет и нужно воспроизвести расположение.",
    "memory", "grid_recall", "visuospatial span", "A", "B",
    "Стандартная методика оценки и тренировки объёма зрительной памяти.",
    ["memoryKind:visuospatial", "memoryKind:working", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-solid"],
    [I("gridSize", "int", 3, 5, "Размер сетки"),
     I("highlightCount", "int", 3, 7, "Число подсвеченных клеток"),
     I("presentationMs", "int", 3000, 1000, "Время показа узора"),
     N("orderMatters", [False, True], "Учитывать ли порядок")],
    12, 2, ["accuracy", "span", "reactionTimeMs", "level"], ["touch"], False, 120, mvp=True)

add(12, "corsi_block", "Последовательность позиций (Corsi)", "Повтори порядок вспышек",
    "Блоки на экране загораются в определённом порядке; нужно повторить последовательность вперёд или назад.",
    "memory", "sequence_recall", "Corsi block-tapping", "A", "B",
    "Классическая парадигма visuospatial sketchpad, входит в нейропсихологические батареи. Corsi-объём — устоявшийся показатель.",
    ["memoryKind:visuospatial", "memoryKind:working", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-solid"],
    [I("sequenceLength", "int", 3, 8, "Длина последовательности"),
     I("presentationMs", "int", 1200, 500, "Длительность вспышки блока"),
     I("gapMs", "int", 500, 200, "Пауза между вспышками"),
     N("reverseOrder", [False, True], "Обратный порядок воспроизведения")],
    10, 2, ["accuracy", "span", "positionErrors", "level"], ["touch"], False, 150,
    extra=dict(relatedNote="Чёрно-красные таблицы Горбова–Шульте из раздела 1.7 — это переключение установок, а не Corsi; реализованы как вариант schulte_table."))

add(13, "object3d_memory", "Запоминание 3D-фигур", "Узнай фигуру среди повёрнутых копий",
    "Предъявляется трёхмерная фигура под определённым углом; затем нужно узнать её среди повёрнутых копий и дистракторов.",
    "memory", "single_choice", "3D object recognition memory", "B", "C",
    "Тренировка образной памяти на трёхмерные фигуры. Парадигма разумная, отдельных валидационных исследований мало.",
    ["memoryKind:visuospatial", "memoryKind:long-term", "paradigmFamily:mental-rotation",
     "delivery:offline-native", "risk:evidence-weak"],
    [I("figureComplexity", "int", 1, 4, "Сложность фигуры"),
     I("rotationSpread", "int", 30, 180, "Разброс углов поворота у вариантов"),
     I("retentionMs", "int", 2000, 8000, "Время удержания до теста"),
     I("optionCount", "int", 3, 6, "Число вариантов ответа")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 180,
    issues=["Перенос не показан, отдельных валидационных исследований парадигмы мало. Перекрывается с mental_rotation_3d: обе требуют мысленного вращения, разница только в наличии фазы удержания."])

add(14, "dual_nback", "Двойной N-back", "Зрительный и звуковой поток одновременно",
    "Квадрат подсвечивается в одной из восьми позиций и одновременно произносится буква. Нужно отметить, совпадает ли позиция с позицией N шагов назад и совпадает ли звук со звуком N шагов назад — независимо.",
    "memory", "continuous_nback", "dual n-back (Jaeggi et al., 2008)", "A", "B",
    "Самая цитируемая парадигма тренировки рабочей памяти. Влияние на fluid intelligence оспаривается: после первоначального ажиотажа мета-анализы показывают слабый широкий перенос. Внутризадачное улучшение стабильно.",
    ["memoryKind:working", "memoryKind:verbal", "paradigmFamily:nback",
     "delivery:offline-native", "risk:evidence-mixed"],
    [I("n", "int", 1, 4, "Глубина — сколько шагов назад сравнивать"),
     I("stimulusMs", "int", 3000, 1500, "Длительность показа стимула"),
     I("gapMs", "int", 500, 200, "Пауза между стимулами"),
     I("targetRate", "float", 0.3, 0.18, "Доля целевых совпадений. Меньше целей — труднее удерживать внимание")],
    20, 3, ["accuracy", "reactionTimeMs", "dPrime", "omissions", "falseAlarms", "level"],
    ["touch"], True, 180, mvp=True,
    issues=["Нужен набор русских слогов, сбалансированный по акустической различимости: пары вроде «б/п» или «д/т» на слух неразличимы в быстром потоке и дадут ложные ошибки.",
            "dPrime требует фиксации hits и false alarms по каждому каналу раздельно. Если хранить только суммарную точность, метрика теряет смысл."])

add(15, "cumulative_recall", "Снежный ком", "Каждый шаг — вся цепочка с начала",
    "Последовательно добавляются элементы (слова, цифры, фигуры); после каждого шага нужно воспроизвести всю цепочку с начала.",
    "memory", "sequence_recall", "cumulative recall / digit span", "B", "B",
    "Классическое упражнение на объём кратковременной памяти. Digit span — устоявшийся показатель, но тренировочный перенос ограничен самой задачей.",
    ["memoryKind:verbal", "memoryKind:working", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-mixed"],
    [I("maxChainLength", "int", 4, 9, "Максимальная длина цепочки"),
     I("presentationMs", "int", 2000, 800, "Время показа элемента"),
     N("stimulusKind", ["digits", "words", "figures"], "Категория стимулов"),
     N("reproductionMode", ["forward", "backward", "both"], "Порядок воспроизведения")],
    5, 2, ["span", "accuracy", "level"], ["touch", "keyboard"], False, 180)

add(16, "memory_match", "Парные карточки", "Найди все пары за минимум ходов",
    "Поле с перевёрнутыми карточками. Открываешь две — если совпали, остаются открытыми. Задача — открыть все пары за минимальное число ходов.",
    "memory", "stateful_board", "concentration / memory match", "C", "C",
    "Честно: доказательств переноса практически нет. Тренирует зрительно-пространственный буфер, а не эпизодическую память. Ценность — в вовлечении и низкопороговом входе, и в каталоге это сказано прямо, а не спрятано.",
    ["memoryKind:visuospatial", "paradigmFamily:visual-search", "delivery:offline-native",
     "risk:evidence-weak"],
    [I("pairs", "int", 6, 12, "Число пар карточек"),
     I("peekMs", "int", 3000, 800, "Время предварительного показа всех карточек"),
     I("flipBackMs", "int", 1500, 500, "Как долго несовпавшая пара остаётся открытой"),
     N("visualSimilarity", ["distinct", "similar_palette", "near_identical"], "Сходство изображений")],
    1, 1, ["moves", "accuracy", "completionSec", "level"], ["touch"], False, 150,
    issues=["Переноса нет — в каталоге это сказано прямо. Оставлять как «лёгкий вход» и упражнение для дней низкой мотивации, но не включать в онбординг-тест и не использовать как представитель домена в маркетинге."])

add(17, "coin_recall", "Монеты", "Воспроизведи расположение и номиналы",
    "На столе раскладываются монеты или фишки; после закрытия нужно воспроизвести их расположение и номиналы.",
    "memory", "grid_recall", "object location memory", "C", "C",
    "Упражнение из практик тренировки памяти, а не из валидированных батарей. Фактически вариант matrix_recall с дополнительной нагрузкой на номинал — это стоит признать в описании.",
    ["memoryKind:visuospatial", "paradigmFamily:visual-search", "delivery:offline-native",
     "risk:evidence-weak"],
    [I("objectCount", "int", 5, 12, "Число объектов"),
     I("presentationMs", "int", 8000, 3000, "Время показа"),
     N("denominations", ["uniform", "two_kinds", "four_kinds"], "Разнообразие номиналов"),
     I("positionTolerance", "int", 1, 0, "Допуск на точность позиции в клетках, 0 = точное совпадение")],
    4, 2, ["accuracy", "positionError", "level"], ["touch"], False, 180,
    issues=["Перекрывается с matrix_recall примерно на 80%. Стоит решить, нужны ли оба в продукте: два почти одинаковых упражнения размывают каталог и путают статистику домена."])

add(18, "mind_palace", "Метод Цицерона", "Привяжи запоминаемое к точкам маршрута",
    "Пользователь выбирает знакомое помещение и расставляет запоминаемые объекты по точкам маршрута, затем воспроизводит их в заданном порядке.",
    "memory", "card_review", "method of loci", "A", "B",
    "Классическая мнемотехника с крепкой базой (Legge et al. 2012 и др.). НО: это стратегия, а не тренажёр — её нельзя параметризовать скаляром сложности так же, как Струпа. Архетип card_review, лестница Левитта не применяется.",
    ["memoryKind:episodic", "memoryKind:long-term", "paradigmFamily:mnemonic",
     "delivery:needs-authors", "risk:evidence-solid"],
    [I("lociCount", "int", 5, 15, "Число точек маршрута"),
     I("itemAbstractness", "int", 1, 4, "Насколько абстрактны запоминаемые объекты"),
     I("reviewDelayHours", "int", 1, 72, "Интервал до проверки"),
     N("lociSource", ["preset_room", "user_defined"], "Готовый маршрут или свой")],
    1, 1, ["retention", "recallLatencyMs", "level"], ["touch", "keyboard"], False, 300,
    src="authored",
    issues=["Требует готовых маршрутов с точками (иллюстрации помещений) или инструмента разметки своих. Это контентная работа, не инженерная.",
            "Адаптация идёт через интервал повторения, а не через сложность стимула — лестница Левитта неприменима."])

add(19, "spaced_repetition", "Интервальное повторение", "Карточки по кривой Эббингауза",
    "Карточки (слова, факты, формулы) предъявляются с увеличивающимися интервалами; пользователь оценивает уверенность, алгоритм пересчитывает следующий интервал.",
    "memory", "card_review", "spaced repetition (Ebbinghaus; SM-2)", "A", "A",
    "Единственная позиция каталога с переносом уровня A: эффект интервального повторения на долговременное удержание — один из самых воспроизводимых результатов в психологии обучения (Ebbinghaus 1885; Cepeda et al. 2006, мета-анализ 254 исследований).",
    ["memoryKind:long-term", "paradigmFamily:mnemonic", "delivery:needs-content-pack",
     "risk:evidence-solid"],
    [I("cardsPerSession", "int", 10, 30, "Карточек за сессию"),
     I("intervalMultiplier", "float", 1.0, 1.6, "Множитель интервала: 1.0 = чистый SM-2, 1.6 = ускоренное продвижение"),
     N("recallMode", ["recognition", "cued_recall", "free_recall"], "Тип припоминания: узнавание, с подсказкой, свободное"),
     N("cardKind", ["user_deck", "vocabulary", "facts", "formulas"], "Тип колоды")],
    1, 1, ["retention", "recallLatencyMs", "easeFactor", "level"], ["touch", "keyboard"], False, 300,
    src="authored",
    issues=["Другая адаптивная модель: сложность определяется ease factor каждой карточки и интервалом, а не глобальным d. Не влезает в лестницу Левитта, и пытаться втиснуть значит сломать обе модели.",
            "SM-2 или FSRS — см. open-questions.md №7. Рекомендация: SM-2 для MVP (прост, 40 лет проверки), FSRS позже.",
            "UX-паттерн другой: это не «сессия», а «долг на сегодня». Требует отдельного экрана и отдельной логики уведомлений."])

add(20, "memory_tunnel", "Тоннель мнемониста", "Пройди тоннель и восстанови порядок образов",
    "Образы помещаются в тоннель в заданном порядке; затем нужно пройти по тоннелю и восстановить последовательность.",
    "memory", "sequence_recall", "serial position recall", "C", "C",
    "Техника тренировки объёмного восприятия. По сути cumulative_recall с пространственной метафорой вместо плоского списка — научной новизны относительно №15 не несёт.",
    ["memoryKind:visuospatial", "memoryKind:working", "paradigmFamily:mnemonic",
     "delivery:offline-native", "risk:evidence-weak"],
    [I("sequenceLength", "int", 4, 9, "Число образов в тоннеле"),
     I("travelMs", "int", 1500, 600, "Скорость прохождения тоннеля"),
     N("imageAbstractness", ["concrete_objects", "abstract_shapes"], "Тип образов"),
     I("delayMs", "int", 0, 5000, "Задержка перед воспроизведением")],
    5, 2, ["accuracy", "span", "level"], ["touch"], False, 180,
    issues=["Дублирует cumulative_recall (№15) и corsi_block (№12). Три упражнения на одну когнитивную операцию — избыточно. Рекомендация: оставить как визуальную обёртку №15, а не как отдельную позицию каталога."])

# ═════════════════════════════════════════════════════════ БЛОК C: число и математика
add(21, "subitizing", "Субтитизация", "Мгновенно назови количество, не считая",
    "На 200–500 мс показываются точки в случайном или структурированном порядке; нужно мгновенно назвать число — сначала 1–4, затем до 10.",
    "number_sense", "numeric_input", "subitizing (Kaufman et al., 1949)", "A", "C",
    "Парадигма безупречна: граница между субтитизацией (1–4, мгновенно) и пересчётом (5+, последовательно) — один из устойчивых эффектов. Перенос за пределы задачи не показан.",
    ["paradigmFamily:number-sense", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-weak"],
    [I("maxQuantity", "int", 4, 10, "Верхняя граница диапазона количества"),
     I("exposureMs", "int", 500, 150, "Время экспозиции"),
     N("arrangement", ["random", "structured_groups", "mixed"], "Случайное или сгруппированное расположение"),
     I("dotSizePx", "int", 24, 12, "Размер точки — мельче значит плотнее и труднее")],
    20, 2, ["accuracy", "reactionTimeMs", "subitizingLimit", "level"], ["touch", "keyboard"], False, 120,
    extra=dict(keyMetric="subitizingLimit — максимальное количество, которое пользователь определяет быстрее 1 секунды. Содержательная метрика, а не просто точность."),
    mvp=True,
    issues=["Перенос за пределы задачи не показан, хотя парадигма безупречна. Не обещать «улучшение математических способностей» — только «скорость схватывания количества»."])

add(22, "ans_comparison", "Сравнение множеств на глаз", "Где больше точек — без пересчёта",
    "Две группы точек; нужно быстро выбрать, где больше, не пересчитывая.",
    "number_sense", "single_choice", "approximate number system (ANS)", "A", "C",
    "ВАЖНО: бриф утверждал, что «невербальная манипуляция количеством causally улучшает точную символьную арифметику». Это не выдерживает проверки — Szkudlarek, DeWind & Brannon (2021), 4 эксперимента, N=318: тренировка приближённой арифметики оказалась не эффективнее контрольной. Ранние положительные результаты есть (Au 2018; Wang et al. 2016), мета-анализ 2021 оценивает эффект как малый. Корректная формулировка — «спорно», а не «causally». См. science-audit.md, позиция №3.",
    ["paradigmFamily:number-sense", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:claim-disputed"],
    [N("ratio", ["1:2", "2:3", "3:4", "5:6", "7:8"], "Соотношение количеств — главный параметр сложности в ANS"),
     I("totalDots", "int", 12, 40, "Суммарное число точек"),
     I("exposureMs", "int", 2000, 400, "Время экспозиции"),
     N("controlFor", ["area_only", "area_and_density"], "Контроль суммарной площади и плотности — иначе задача решается по нечисловому признаку")],
    20, 2, ["accuracy", "reactionTimeMs", "weberFraction", "level"], ["touch"], False, 120,
    issues=["КРИТИЧНО для валидности: если не контролировать суммарную площадь и плотность точек, пользователь решает задачу по нечисловому признаку и измеряется не ANS. Генератор обязан уравнивать площадь при разных количествах. Это самая частая методологическая ошибка в ANS-исследованиях.",
            "Заявку о переносе на арифметику из пользовательского описания убрать."])

add(23, "part_part_whole", "Разбивка чисел на части", "Найди вторую часть числа",
    "Дано число и одна часть — нужно найти вторую. Или показаны число и несколько вариантов разбивки — выбрать все корректные.",
    "number_sense", "numeric_input", "part-part-whole / number bonds", "A", "B",
    "Фундамент number sense и ранней арифметики; связь декомпозиции числа с арифметической беглостью показана в литературе по математическому образованию.",
    ["paradigmFamily:number-sense", "paradigmFamily:arithmetic-fluency",
     "delivery:offline-native", "risk:evidence-mixed"],
    [I("maxNumber", "int", 10, 100, "Максимальное значение числа"),
     I("responseWindowMs", "int", 6000, 2000, "Окно на ответ"),
     N("taskKind", ["find_missing_part", "select_all_decompositions"], "Тип задачи"),
     I("partCount", "int", 2, 3, "На сколько частей разбивается число")],
    15, 2, ["accuracy", "reactionTimeMs", "throughput", "level"], ["touch", "keyboard"], False, 120)

add(24, "number_chunking", "Chunking числовых последовательностей", "Разбей поток цифр на группы",
    "Длинная последовательность цифр предъявляется монолитно или уже разбитой на группы; нужно воспроизвести. Постепенно пользователь сам учится разбивать поток на осмысленные чанки.",
    "memory", "sequence_recall", "chunking (Miller, 1956)", "A", "B",
    "Chunking — ключевой механизм расширения ёмкости рабочей памяти; «магическое число 7±2» Миллера — одна из самых цитируемых работ в психологии.",
    ["memoryKind:working", "memoryKind:verbal", "paradigmFamily:number-sense",
     "delivery:offline-native", "risk:evidence-solid"],
    [I("sequenceLength", "int", 7, 16, "Длина последовательности цифр"),
     I("presentationMsPerDigit", "int", 1200, 400, "Время показа одной цифры"),
     N("groupingHint", ["none", "visual_groups", "semantic_groups"], "Подсказка группировки: нет, визуальная, осмысленная (даты, коды)"),
     I("chunkSize", "int", 2, 4, "Размер чанка при подсказке")],
    8, 2, ["span", "accuracy", "chunkingIndex", "level"], ["touch", "keyboard"], False, 180,
    extra=dict(keyMetric="chunkingIndex — отношение воспроизведённой длины к длине при монолитной подаче. Показывает, освоил ли пользователь стратегию, а не просто запомнил больше."))

add(25, "mental_abacus", "Ментальный абакус", "Сначала на счётах, потом в уме",
    "Операции на виртуальном абакусе, затем — только на мысленном образе: сложение и вычитание, позже умножение.",
    "number_sense", "stateful_board", "abacus-based mental calculation (AMC)", "B", "B",
    "Реальные исследования есть, включая fMRI-работы (Hu et al.), показывающие вовлечение зрительно-пространственных областей у trained abacists. Но выборки малые, дизайны гетерогенные, большая часть данных — на детях с многолетней практикой. Корректная формулировка: «связана с улучшением», а не «улучшает».",
    ["paradigmFamily:arithmetic-fluency", "paradigmFamily:mnemonic",
     "delivery:offline-native", "risk:evidence-mixed"],
    [I("digitCount", "int", 1, 4, "Разрядность чисел"),
     I("operationCount", "int", 2, 8, "Число операций в цепочке"),
     N("operations", ["add", "add_sub", "add_sub_mul"], "Набор операций"),
     N("visualizationMode", ["physical_abacus", "faded_abacus", "mental_only"], "Показывать ли абакус")],
    6, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 240,
    issues=["Требует интерактивный рендер абакуса (соробан: одна heaven-косточка и четыре earth-косточки на разряд). Это отдельная UI-работа в рамках stateful_board.",
            "Переход physical → mental — ключевая механика AMC. Без неё упражнение превращается в обычный устный счёт."])

add(26, "speed_arithmetic", "Быстрый устный счёт", "Реши примеры на скорость",
    "Примеры на сложение, вычитание, умножение и деление с адаптивной сложностью и таймером.",
    "number_sense", "numeric_input", "timed mental arithmetic", "B", "B",
    "Тренирует арифметическую беглость, перенос на общий интеллект не показан. Поглощает v1 rapid_count — это одна и та же задача.",
    ["paradigmFamily:arithmetic-fluency", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-mixed"],
    [I("maxOperand", "int", 10, 99, "Максимальное значение операнда"),
     N("operations", ["add", "add_sub", "add_sub_mul", "add_sub_mul_div"], "Набор операций"),
     I("responseWindowMs", "int", 5000, 1500, "Время на пример"),
     N("allowNegative", [False, True], "Допускать ли отрицательные результаты")],
    20, 2, ["accuracy", "reactionTimeMs", "throughput", "level"], ["touch", "keyboard"], False, 120,
    extra=dict(mergedFrom="v1 rapid_count"))

add(27, "number_series", "Числовые ряды и закономерности", "Найди правило и продолжи ряд",
    "Дан ряд чисел; нужно найти следующее число или пропущенное звено, выявив правило: арифметическая или геометрическая прогрессия, чередование, Фибоначчи.",
    "number_sense", "numeric_input", "number series / inductive reasoning", "A", "B",
    "Классическая задача на индуктивное рассуждение, входит в батареи измерения fluid intelligence. Как измеритель валидна; тренировочный перенос оспаривается.",
    ["paradigmFamily:number-sense", "delivery:offline-native", "risk:evidence-mixed"],
    [I("ruleCount", "int", 1, 3, "Сколько правил действует одновременно"),
     N("ruleKind", ["arithmetic", "geometric", "alternating", "fibonacci_like", "composite"], "Класс закономерности"),
     I("timeLimitSec", "int", 60, 20, "Время на задачу"),
     N("missingPosition", ["next", "middle"], "Пропущен последний элемент или средний")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch", "keyboard"], False, 180,
    issues=["Генератор обязан гарантировать ОДНОЗНАЧНОСТЬ правила. Короткий ряд можно продолжить многими способами, и если приложение считает свой вариант единственно верным, пользователь получит необоснованную ошибку. Нужно либо минимум шесть элементов, либо явная проверка единственности."])

add(28, "magic_squares", "Магические квадраты", "Заполни так, чтобы суммы совпадали",
    "Заполнить квадрат числами так, чтобы суммы по строкам, столбцам и диагоналям совпадали.",
    "number_sense", "stateful_board", "magic square construction", "B", "C",
    "Задача из олимпиадной и развивающей математики. Как тренажёр комбинаторного мышления разумна, данных о переносе нет.",
    ["paradigmFamily:constraint-satisfaction", "delivery:offline-native", "risk:evidence-weak"],
    [N("squareSize", [3, 4, 5], "Размер квадрата"),
     I("givens", "int", 5, 1, "Число уже заполненных клеток — меньше значит труднее"),
     N("constraintSet", ["rows_cols", "rows_cols_diagonals"], "Какие суммы должны совпадать"),
     I("timeLimitSec", "int", 300, 90, "Ограничение времени")],
    1, 1, ["solved", "completionSec", "errors", "level"], ["touch"], False, 300,
    issues=["Для 4×4 и 5×5 число решений огромно, и проверка правильности должна принимать ЛЮБОЙ валидный магический квадрат, а не один эталонный. Нужен валидатор, а не сравнение с заготовкой.",
            "Отрицательные и дробные значения расширяют пространство решений — для MVP ограничиться целыми положительными."])

add(29, "water_pouring", "Задачи на переливание", "Отмерь нужный объём за минимум шагов",
    "Даны сосуды разного объёма; нужно отмерить заданное количество за минимальное число шагов.",
    "number_sense", "stateful_board", "water pouring (Luchins, 1942)", "A", "B",
    "Классическая задача на решение проблем — именно на ней Лачинс продемонстрировал эффект установки (Einstellung effect). Ценна не только как тренировка, но и как измеритель ригидности мышления.",
    ["paradigmFamily:planning", "paradigmFamily:insight", "delivery:offline-native",
     "risk:evidence-solid"],
    [I("jugCount", "int", 2, 3, "Число сосудов"),
     I("targetVolume", "int", 4, 25, "Целевой объём"),
     I("moveLimit", "int", 12, 5, "Ограничение по числу шагов"),
     N("solutionUniqueness", ["multiple", "unique_shortest"], "Есть ли единственное кратчайшее решение")],
    3, 2, ["solved", "movesUsed", "optimalDelta", "level"], ["touch"], False, 240,
    issues=["Генератор обязан проверять разрешимость: не всякая тройка объёмов и целевого значения достижима. Нужен BFS по пространству состояний при генерации — это дёшево, но обязательно.",
            "optimalDelta (число ходов сверх оптимального) содержательнее бинарного «решил или не решил»."])

add(30, "magnitude_estimation", "Оценка величины и пропорций", "Определи долю или значение на шкале",
    "Дана визуальная шкала или отрезок с отмеченной точкой; нужно оценить числовое значение или долю, например какая часть закрашена.",
    "number_sense", "single_choice", "mental number line / magnitude estimation", "B", "B",
    "Связь пространственных и числовых представлений (mental number line) — активно изучаемая область; эффект SNARC и логарифмическая природа числовой оценки у детей подтверждены.",
    ["paradigmFamily:number-sense", "delivery:offline-native", "risk:evidence-mixed"],
    [N("scaleKind", ["linear_0_10", "linear_0_100", "linear_0_1000", "logarithmic"], "Тип шкалы"),
     I("tolerancePct", "int", 20, 4, "Допустимая ошибка в процентах"),
     N("taskKind", ["estimate_value", "estimate_proportion", "place_value"], "Что именно требуется"),
     I("responseWindowMs", "int", 8000, 3000, "Окно на ответ")],
    12, 2, ["accuracy", "absoluteErrorPct", "level"], ["touch"], False, 150,
    issues=["Логарифмическая шкала методологически самая интересная (отражает реальную природу числовой оценки), но для пользователя выглядит как несправедливая задача. Нужна явная подводка в обучении."])

# ════════════════════════════════════════════════════════════════ БЛОК D: логика
add(31, "syllogisms", "Дедуктивные силлогизмы", "Следует ли вывод из посылок",
    "Даны две посылки; нужно выбрать корректное заключение или оценить, является ли предложенный вывод логически необходимым.",
    "logic", "single_choice", "syllogistic reasoning", "A", "B",
    "Классическая логика и хорошо изученная область: эффект атмосферы (Woodworth–Sells) и belief bias — устойчивые находки. Как тренажёр дедукции валидна.",
    ["paradigmFamily:constraint-satisfaction", "delivery:offline-native", "risk:evidence-solid"],
    [N("figure", ["first", "second", "third", "fourth"], "Фигура силлогизма"),
     N("quantifiers", ["universal_only", "universal_and_particular", "with_negations"], "Набор кванторов"),
     N("contentBelievability", ["neutral", "belief_congruent", "belief_bias_trap"], "Нейтральные термины или провоцирующие belief bias"),
     I("responseWindowMs", "int", 45000, 15000, "Окно на ответ")],
    8, 2, ["accuracy", "reactionTimeMs", "beliefBiasIndex", "level"], ["touch"], False, 240,
    extra=dict(keyMetric="beliefBiasIndex — разница точности между логически валидными, но неправдоподобными выводами и невалидными, но правдоподобными. Содержательная метрика качества рассуждения."),
    issues=["Нужен генератор валидных и невалидных силлогизмов с проверкой через таблицы истинности или решатель. Ошибка в разметке правильного ответа в логической задаче фатальна для доверия."])

add(32, "logic_grid", "Логические сетки", "Заполни таблицу соответствий по подсказкам",
    "Даны объекты, категории и набор подсказок; нужно заполнить таблицу соответствий — кто где живёт, кто что пьёт.",
    "logic", "stateful_board", "logic grid / constraint satisfaction", "B", "B",
    "Табличный метод решения логических задач. Как тренировка дедукции валидна, перенос строго не измерялся.",
    ["paradigmFamily:constraint-satisfaction", "paradigmFamily:planning",
     "delivery:offline-native", "risk:evidence-mixed"],
    [I("categoryCount", "int", 2, 4, "Число категорий"),
     I("itemsPerCategory", "int", 3, 5, "Элементов в каждой категории"),
     I("clueCount", "int", 8, 4, "Число подсказок — меньше значит труднее"),
     N("clueKind", ["positive_only", "positive_negative", "with_relational"], "Типы подсказок: утвердительные, отрицательные, реляционные")],
    1, 1, ["solved", "completionSec", "wrongMarks", "level"], ["touch"], False, 420,
    issues=["Генератор обязан гарантировать ЕДИНСТВЕННОСТЬ решения: недодетерминированная сетка — брак, который пользователь обнаружит сам. Нужен решатель с проверкой единственности (backtracking с подсчётом числа решений).",
            "Формулировки подсказок на русском требуют аккуратных шаблонов: «А не живёт рядом с Б» и «А и Б — не соседи» должны парситься одинаково."])

add(33, "knights_knaves", "Рыцари и лжецы", "Кто всегда говорит правду, а кто лжёт",
    "Персонажи либо всегда говорят правду, либо всегда лгут; по их высказываниям нужно определить, кто есть кто.",
    "logic", "single_choice", "knights and knaves (Smullyan)", "A", "B",
    "Классический жанр от Реймонда Смаллиана. Как задача на рассуждение о противоречивых высказываниях — полноценный инструмент формальной логики.",
    ["paradigmFamily:constraint-satisfaction", "delivery:offline-native", "risk:evidence-solid"],
    [I("characterCount", "int", 2, 5, "Число персонажей"),
     N("statementKind", ["self_reference", "cross_reference", "both", "with_conditionals"], "Типы высказываний"),
     N("characterTypes", ["binary", "ternary_alternator"], "Два типа или три, включая чередующихся"),
     I("responseWindowMs", "int", 90000, 30000, "Окно на ответ")],
    5, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 300,
    issues=["Генератор должен проверять, что задача имеет ровно одно решение. Перебор по 2^n комбинациям тривиален для n не больше 5, так что гарантия дешёвая.",
            "Третий тип «чередующийся» резко усложняет формализацию — оставить для пост-MVP."])

add(34, "danetki", "Данетки", "Задавай вопросы да/нет и восстанови историю",
    "Дана загадочная ситуация; нужно задавать вопросы с ответами да/нет, чтобы восстановить скрытую историю.",
    "creativity", "dialog_yesno", "lateral thinking puzzles / abductive reasoning", "B", "C",
    "Валидная парадигма инсайтного мышления и абдукции. Но как измеряемый тренажёр проблематична: метрика «эффективность вопросов» зависит от авторской разметки сценария.",
    ["paradigmFamily:insight", "paradigmFamily:divergent", "delivery:needs-authors",
     "risk:evidence-weak"],
    [I("questionBudget", "int", 30, 10, "Сколько вопросов доступно"),
     N("scenarioComplexity", ["simple", "medium", "multi_twist"], "Сложность сценария"),
     N("hintLevel", ["full_hint", "direction", "none"], "Уровень подсказки"),
     N("answerAmbiguity", ["strict_yes_no", "yes_no_irrelevant"], "Допускаются ли ответы «не важно»")],
    1, 1, ["solved", "questionsUsed", "efficiency", "level"], ["touch", "keyboard"], False, 420,
    src="authored",
    issues=["ТЕХНИЧЕСКИЙ БЛОКЕР: нужны либо размеченные деревья ответов на каждый сценарий, либо LLM. Первое очень трудоёмко (каждый сценарий — мини-игра), второе ломает offline-first из брифа. См. open-questions.md №19.",
            "Автоматическое распознавание свободного вопроса пользователя и сопоставление с деревом ответов — отдельная NLP-задача даже без LLM."])

add(35, "matchstick_puzzles", "Задачи со спичками", "Переложи одну спичку",
    "Фигура или равенство из спичек; нужно переложить заданное число спичек, чтобы выполнить условие.",
    "creativity", "stateful_board", "matchstick arithmetic (Knoblich et al., 1999)", "A", "B",
    "Классическая задача на инсайт; на ней показаны механизмы расфиксации (decomposition) и связь с активностью передней поясной коры (Kounios, Jung-Beeman). Поглощает v1 matchstick_puzzles.",
    ["paradigmFamily:insight", "delivery:offline-native", "risk:evidence-solid"],
    [I("movesAllowed", "int", 3, 1, "Сколько спичек можно переложить — меньше значит труднее"),
     N("puzzleType", ["geometric_figure", "arithmetic_equality", "arithmetic_with_removal", "roman_numerals"], "Класс головоломки"),
     N("hintAvailability", ["full_solution", "direction", "none"], "Уровень подсказки")],
    3, 1, ["solved", "movesUsed", "completionSec", "level"], ["touch"], False, 200,
    extra=dict(mergedFrom="v1 matchstick_puzzles"),
    issues=["Нужен банк головоломок с гарантированно единственным решением. При малом числе спичек полный перебор тривиален — гарантия дешёвая, но обязательная."])

add(36, "pouring_weighing", "Переливания и взвешивания", "Минимум действий для точного результата",
    "Задачи на отмеривание объёма или веса с ограниченным набором действий; поиск минимального числа шагов.",
    "logic", "stateful_board", "weighing puzzles / state-space search", "B", "C",
    "Олимпиадная классика, тренировка алгоритмического мышления. Пересекается с №29 water_pouring: там акцент на установке мышления, здесь на поиске минимума.",
    ["paradigmFamily:planning", "paradigmFamily:constraint-satisfaction",
     "delivery:offline-native", "risk:evidence-weak"],
    [I("objectCount", "int", 3, 8, "Число объектов"),
     N("taskKind", ["weighing_balance", "volume_transfer", "crossing_river"], "Класс задачи"),
     I("moveLimit", "int", 7, 3, "Ограничение по числу действий"),
     N("constraintVisibility", ["explicit", "implicit"], "Явные или скрытые ограничения")],
    2, 1, ["solved", "movesUsed", "optimalDelta", "level"], ["touch"], False, 300,
    issues=["Перекрывается с water_pouring (№29). Рекомендация: объединить в один архетип задач на пространство состояний с параметром taskKind, а не держать две позиции каталога."])

add(37, "odd_one_out", "Исключение лишнего", "Найди лишний и определи критерий",
    "Дан набор объектов — слова, фигуры, числа; нужно найти лишний и указать критерий либо выбрать все возможные варианты.",
    "logic", "multi_choice", "odd one out / classification", "A", "B",
    "Базовые операции мышления: анализ, сравнение, обобщение, абстракция. Как измеритель классификации хорошо изучена.",
    ["paradigmFamily:divergent", "delivery:offline-native", "risk:evidence-mixed"],
    [I("itemCount", "int", 4, 8, "Число объектов в наборе"),
     N("stimulusKind", ["words", "figures", "numbers", "mixed"], "Природа объектов"),
     I("criterionCount", "int", 1, 3, "Сколько корректных критериев существует"),
     N("abstractionLevel", ["perceptual", "functional", "categorical", "abstract"], "Уровень абстракции критерия")],
    10, 2, ["accuracy", "reactionTimeMs", "criterionFound", "level"], ["touch"], False, 150,
    issues=["Если критериев несколько, нужно либо принимать все, либо явно просить «лучший». Иначе упражнение превращается в угадайку, а метрика criterionFound теряет смысл."])

add(38, "visual_patterns", "Закономерности в визуальных рядах", "Выбери следующую фигуру",
    "Последовательность фигур, меняющихся по правилу — поворот, добавление элемента, изменение цвета; нужно выбрать следующую.",
    "logic", "single_choice", "Raven-like matrix reasoning", "A", "B",
    "Прогрессивные матрицы Равена — золотой стандарт измерения fluid intelligence. Как измеритель валидна; тренировочный перенос оспаривается. Поглощает v1 pattern_finding.",
    ["paradigmFamily:mental-rotation", "delivery:offline-native", "risk:evidence-mixed"],
    [I("ruleCount", "int", 1, 3, "Сколько правил действует одновременно"),
     N("ruleTypes", ["rotation", "rotation_counting", "rotation_counting_color", "composite"], "Классы правил"),
     N("distractorSimilarity", ["far", "near", "near_plus_partial_rule"], "Похожесть неверных вариантов"),
     I("timeLimitSec", "int", 60, 20, "Время на задачу")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 180, mvp=True,
    extra=dict(mergedFrom="v1 pattern_finding"),
    issues=["Генерация задач с composite-правилами и валидными дистракторами нетривиальна. Проще авторский банк на 200–300 задач с ручной разметкой, чем генератор."])

add(39, "chess_tactics", "Шахматные задачи", "Найди форсированный мат",
    "Дана позиция; нужно найти форсированный мат за N ходов.",
    "logic", "stateful_board", "chess tactics / tactical pattern recognition", "B", "C",
    "Тренировка рабочей памяти и пространственного планирования в специфической области. Важно: исследования шахмат и интеллекта показывают, что шахматисты лучше решают шахматные задачи, а широкий перенос слаб (Burgoyne et al. 2016, мета-анализ).",
    ["paradigmFamily:planning", "paradigmFamily:constraint-satisfaction",
     "delivery:needs-external-data", "risk:evidence-weak"],
    [N("mateIn", [1, 2, 3], "За сколько ходов мат"),
     I("pieceCount", "int", 8, 20, "Число фигур на доске"),
     N("tacticTheme", ["any", "fork", "pin", "skewer", "discovered"], "Тема задачи"),
     N("hintLevel", ["first_move", "square_hint", "none"], "Уровень подсказки")],
    3, 1, ["solved", "movesToSolve", "completionSec", "level"], ["touch"], False, 300,
    src="external",
    issues=["Нужна внешняя база задач (Lichess puzzles — CC0) или встроенный движок для генерации и проверки. Свои задачи без движка делать нельзя: невозможно гарантировать форсированность.",
            "Ходы пользователя надо валидировать по правилам шахмат, включая рокировку, взятие на проходе и превращение пешки. Это полноценная шахматная логика — заметный объём.",
            "Заявку «тренировка рабочей памяти» в пользовательском описании смягчить: перенос слабый."])

add(40, "escape_room", "Мини-эскейп", "Найди код и выберись из комнаты",
    "Короткая комната с 3–5 объектами и цепочкой логических выводов; нужно найти код или выход.",
    "creativity", "stateful_board", "escape room logic / chained puzzles", "C", "C",
    "Комплексная тренировка решения проблем. Честная оценка: как измеритель слабо формализуема, перенос не изучен. Ценность — вовлечение и удержание, а не тренировка.",
    ["paradigmFamily:planning", "paradigmFamily:insight", "delivery:needs-authors",
     "risk:evidence-weak"],
    [I("chainLength", "int", 3, 6, "Длина цепочки выводов"),
     N("puzzleKinds", ["single_kind", "mixed_kinds"], "Однородные или разные типы подзадач"),
     I("objectCount", "int", 3, 7, "Число интерактивных объектов"),
     N("hintLevel", ["on_demand", "after_timeout", "none"], "Доступность подсказок")],
    1, 1, ["solved", "completionSec", "hintsUsed", "level"], ["touch"], False, 600,
    src="authored",
    issues=["Самое дорогое упражнение каталога по контенту: каждая комната — авторская работа на дни. При этом научная ценность наименьшая.",
            "Длительность 600 секунд ломает модель короткой сессии — это отдельный режим «долгая игра», а не часть ежедневной зарядки.",
            "Рекомендация: пост-MVP, не раньше появления контент-команды."])

# ═══════════════════════════════════════════════════ БЛОК E: графика и восприятие
add(41, "hidden_symbol", "Поиск скрытого символа", "Найди отличающийся символ в поле",
    "Поле из повторяющихся символов; среди них спрятан один отличающийся, например буква Q среди нулей.",
    "attention", "timed_field", "visual search (Treisman feature integration)", "A", "B",
    "Зрительный поиск — одна из лучше всего изученных парадигм; теория интеграции признаков Трейсман объясняет зависимость времени поиска от числа дистракторов.",
    ["paradigmFamily:visual-search", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-solid"],
    [I("fieldSize", "int", 64, 400, "Число символов в поле"),
     N("targetSimilarity", ["distinct", "visually_similar", "semantically_similar"], "Сходство цели и дистракторов"),
     I("responseWindowMs", "int", 10000, 3000, "Окно на ответ"),
     N("targetCount", [1, 2, 3], "Сколько целей спрятано")],
    12, 2, ["accuracy", "reactionTimeMs", "searchSlope", "level"], ["touch"], False, 120,
    extra=dict(keyMetric="searchSlope — прирост времени реакции на каждый дополнительный дистрактор. Содержательная характеристика эффективности поиска, а не просто скорость."))

add(42, "spot_difference", "Поиск отличий", "Найди N отличий между картинками",
    "Две почти одинаковые картинки; нужно найти заданное число отличий.",
    "attention", "timed_field", "visual comparison", "C", "C",
    "Тренировка зрительного восприятия и удержания деталей. Честно: это развлекательный формат, данных о когнитивном переносе нет.",
    ["paradigmFamily:visual-search", "delivery:needs-authors", "risk:evidence-weak"],
    [I("differenceCount", "int", 3, 10, "Число отличий"),
     N("differenceSubtlety", ["obvious", "moderate", "subtle_color", "subtle_detail"], "Тонкость различий"),
     I("timeLimitSec", "int", 120, 40, "Ограничение времени"),
     N("layoutVariation", ["identical_layout", "mirrored", "shifted"], "Совпадает ли компоновка картинок")],
    1, 1, ["found", "accuracy", "completionSec", "level"], ["touch"], False, 180,
    src="authored",
    issues=["Требует авторские пары картинок — не генерируется. Самая дорогая позиция каталога по контенту при наименьшей научной ценности.",
            "Рекомендация: пост-MVP, либо генеративный вариант (программная картинка с внесёнными изменениями) вместо иллюстраций."])

add(43, "maze", "Лабиринт", "Проведи линию от старта к финишу",
    "Провести палец или курсор от старта к финишу через лабиринт.",
    "spatial_reasoning", "trace_draw", "maze navigation / planning", "B", "C",
    "Классическая задача на пространственное планирование. Как измеритель планирования используется, перенос не показан.",
    ["paradigmFamily:planning", "paradigmFamily:visual-search", "delivery:offline-native",
     "risk:evidence-weak"],
    [I("gridSize", "int", 8, 24, "Размер лабиринта"),
     I("deadEndDensity", "float", 0.2, 0.6, "Плотность тупиков"),
     N("pathUniqueness", ["single_solution", "multiple_solutions"], "Единственность решения"),
     N("viewMode", ["full", "fog_of_war"], "Видна ли вся карта сразу")],
    2, 1, ["completionSec", "pathLengthRatio", "lifts", "level"], ["touch"], False, 180,
    issues=["Генератор на DFS или Prim даёт гарантированную связность — это дёшево. Но метрика pathLengthRatio требует знания оптимального пути, то есть BFS при генерации.",
            "fog_of_war превращает задачу в запоминание, а не планирование — фактически это другое упражнение."])

add(44, "color_connect", "Соедини точки по цветам", "Проложи непересекающиеся линии",
    "Нужно соединить точки одного цвета линиями, не пересекая их и заполнив всё поле.",
    "spatial_reasoning", "stateful_board", "flow free / non-crossing path planning", "C", "C",
    "Тренировка восприятия цвета, зрительной памяти и планирования. Формальных исследований именно этой задачи нет.",
    ["paradigmFamily:planning", "paradigmFamily:constraint-satisfaction",
     "delivery:offline-native", "risk:evidence-weak"],
    [I("gridSize", "int", 5, 9, "Размер поля"),
     I("colorCount", "int", 4, 10, "Число цветов и пар"),
     N("fillRequirement", ["connect_only", "fill_entire_grid"], "Требование заполнить всё поле"),
     I("timeLimitSec", "int", 180, 60, "Ограничение времени")],
    2, 1, ["solved", "completionSec", "movesUsed", "level"], ["touch"], False, 200,
    issues=["Вариант с требованием заполнить всё поле NP-труден в общем случае; генератор должен строить решение обратным ходом (разбивать поле на пути), а не искать решение перебором.",
            "Обязательна дальтоник-безопасная палитра — подобрать 10 различимых при дейтеранопии цветов нетривиально."])

add(45, "camouflaged_figures", "Камуфлированные фигуры", "Найди цифру в шуме из цветных точек",
    "Изображение из цветных точек, в котором зашифрована цифра или фигура; нужно её распознать.",
    "attention", "single_choice", "camouflaged figures / figure-ground segregation", "B", "C",
    "Таблицы Рабкина — клинический инструмент; как тренажёр выделения сигнала из шума задача валидна, но именно тренировочный эффект не валидирован.",
    ["paradigmFamily:visual-search", "paradigmFamily:interference", "delivery:offline-native",
     "risk:evidence-weak"],
    [I("contrastDelta", "int", 40, 8, "Различие цвета фигуры и фона — меньше значит труднее"),
     I("dotDensity", "int", 800, 3000, "Плотность точек"),
     N("figureKind", ["digit", "letter", "simple_shape"], "Тип зашифрованного объекта"),
     I("exposureMs", "int", 10000, 2000, "Время экспозиции")],
    8, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 150,
    issues=["ОБЯЗАТЕЛЬНА дальтоник-безопасность: при дейтеранопии часть цветовых комбинаций становится неразличимой, и задача оказывается непроходимой. Нужен режим с альтернативной палитрой и проверка контраста.",
            "Клинический инструмент в развлекательном приложении — формулировать осторожно, чтобы не создавать впечатления диагностики."])

add(46, "mirror_drawing", "Зеркальное рисование двумя руками", "Рисуй симметрично двумя пальцами",
    "Две области на экране; нужно одновременно рисовать двумя пальцами зеркально-симметричные линии или фигуры.",
    "cognitive_flexibility", "trace_draw", "bimanual coordination / mirror drawing", "B", "C",
    "ВАЖНО: бриф заявлял «активирует межполушарные связи». Зеркальная терапия имеет реальную базу в РЕАБИЛИТАЦИИ ПОСЛЕ ИНСУЛЬТА (перестроение моторной коры, снижение фантомной боли), но это данные о пациентах с односторонним дефицитом. Перенос вывода на здоровых пользователей и на «синхронизацию полушарий» не обоснован. См. science-audit.md, позиция №2: упражнение оставлено как зрительно-моторная задача, заявка о полушариях убрана.",
    ["paradigmFamily:motor", "delivery:offline-native", "risk:claim-disputed"],
    [I("pathComplexity", "int", 1, 4, "Сложность эталонной траектории"),
     I("tempoMs", "int", 6000, 2000, "Время на выполнение"),
     I("tolerancePx", "int", 30, 8, "Допуск отклонения от эталона"),
     N("symmetryKind", ["mirror_vertical", "mirror_horizontal", "rotational"], "Тип требуемой симметрии")],
    4, 1, ["symmetryError", "pathDeviation", "completionSec", "level"], ["touch"], False, 180,
    issues=["Требует мультитач с двумя одновременными точками контакта. На десктопе невыполнимо без специальной поддержки — нужен явный фолбэк.",
            "Метрика symmetryError осмысленна только при стабильной частоте опроса touch-событий; на слабых устройствах джиттер исказит результат."])

add(47, "symmetry_completion", "Симметричные узоры", "Дострой вторую половину орнамента",
    "Дана половина орнамента; нужно выбрать или достроить вторую половину так, чтобы получилась симметричная фигура.",
    "spatial_reasoning", "single_choice", "symmetry detection", "A", "B",
    "Пространственное восприятие симметрии — хорошо изученная область. Отличается от №8 тем, что здесь орнаменты и возможны оба типа симметрии в смешанном режиме.",
    ["paradigmFamily:mental-rotation", "delivery:offline-native", "risk:evidence-solid"],
    [N("symmetryKind", ["axial", "central", "both_mixed"], "Тип симметрии"),
     I("patternComplexity", "int", 2, 6, "Сложность орнамента"),
     I("optionCount", "int", 3, 6, "Число вариантов ответа"),
     I("responseWindowMs", "int", 12000, 4000, "Окно на ответ")],
    10, 2, ["accuracy", "reactionTimeMs", "level"], ["touch"], False, 150,
    issues=["Сильно перекрывается с №8 mirror_completion. Рекомендация: объединить в одно упражнение с параметром symmetryKind, а не держать две позиции каталога."])

add(48, "neurogym", "Кинезиологическая нейрогимнастика", "Повторяй жесты по инструкции",
    "Последовательность жестов по инструкции: «кулак–ребро–ладонь», «ухо–нос», «лезгинка», «колечко»; постепенное ускорение и смена рук.",
    "cognitive_flexibility", "motor_sequence", "educational kinesiology (Brain Gym)", "D", "D",
    "НАУЧНО НЕ ОБОСНОВАНО. Заявленный механизм — «синхронизация полушарий» через перекрёстные движения — не имеет нейрофизиологического подтверждения. Spaulding, Hutchins & Kaufmann (2010), 172 цитирования: «little empirical evidence validating the approach». Положительные результаты в мелких работах получены на дизайне pre/post без активной контрольной группы. Дополнительно: приложение не может проверить выполнение без камеры, а самоотчёт — не измерение. См. science-audit.md, позиция №1: РЕКОМЕНДУЕТСЯ ИСКЛЮЧИТЬ.",
    ["paradigmFamily:motor", "delivery:needs-authors", "risk:claim-disputed"],
    [I("elementCount", "int", 3, 8, "Число элементов последовательности"),
     I("tempoMs", "int", 3000, 800, "Время на элемент"),
     N("handSwap", [False, True], "Требуется ли смена рук"),
     N("dualTask", ["none", "verbal_counting", "verbal_naming"], "Вторая задача одновременно")],
    1, 1, ["selfReportedAccuracy", "tempoErrorMs"], ["touch"], False, 120,
    src="authored", removed=True,
    issues=["РЕКОМЕНДАЦИЯ: исключить из измеряемого каталога. Допустимо оставить как разминку вне системы метрик — без вклада в «Индекс ясности» и без утверждений о полушариях.",
            "Прямой конфликт с позиционированием продукта: Lumosity получила отозванное исследование и репутационный удар ровно за такие заявки.",
            "Выполнение непроверяемо без камеры или акселерометра — лестница Левитта неприменима.",
            "Связанное замечание: «кулак–ребро–ладонь» из раздела 3 брифа (разминка) — это проба Лурии на кинетическую праксию, она имеет клинический смысл, но её эффективность именно как разминки перед когнитивной тренировкой не показана."])

add(49, "visual_cancellation", "Корректурная проба", "Вычеркни все заданные символы",
    "Поле символов; нужно как можно быстрее вычеркнуть все заданные символы, например все буквы «К».",
    "attention", "timed_field", "cancellation test (Bourdon / Toulouse-Piéron)", "A", "B",
    "Классическая корректурная проба, входит в нейропсихологические батареи (Бурдон, Тулуз-Пьерон). Устойчивые метрики: темп, точность, индекс концентрации.",
    ["paradigmFamily:visual-search", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-solid"],
    [I("fieldSize", "int", 200, 900, "Число символов в поле"),
     I("targetTypes", "int", 1, 3, "Сколько типов символов нужно вычёркивать"),
     N("distractorSimilarity", ["distinct", "visually_similar", "phonetically_similar"], "Сходство дистракторов с целью"),
     I("timeLimitSec", "int", 180, 60, "Ограничение времени")],
    1, 1, ["processedCount", "errors", "omissions", "concentrationIndex", "level"], ["touch"], False, 200,
    extra=dict(keyMetric="concentrationIndex = (processed − errors) / time. Стандартная метрика корректурной пробы, сравнимая с бумажными нормами."))

add(50, "graphic_stroop", "Цвет-слово на графических объектах", "Назови цвет предмета, а не предмет",
    "Объект, например яблоко, окрашен в несоответствующий цвет; нужно быстро выбрать цвет, игнорируя содержание изображения.",
    "attention", "single_choice", "semantic Stroop / picture-word interference", "A", "B",
    "Модификация теста Струпа для зрительных объектов; picture-word interference — устоявшаяся парадигма (Rosinski; picture-word Stroop effect).",
    ["paradigmFamily:interference", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-solid"],
    [I("incongruentRate", "float", 0.25, 0.6, "Доля конфликтных проб"),
     I("responseWindowMs", "int", 2500, 900, "Окно на ответ"),
     I("objectCount", "int", 8, 24, "Число объектов в наборе"),
     N("interferenceKind", ["color_word", "color_word_shape", "color_word_emotion"], "Типы конкурирующих признаков")],
    24, 2, ["accuracy", "reactionTimeMs", "stroopEffectMs", "level"], ["touch"], False, 150,
    issues=["Нужен набор узнаваемых силуэтов предметов. Это ассеты, хотя и простые — можно рисовать программно.",
            "Обязательна дальтоник-безопасная палитра, см. №45."])

# ══════════════════════════════════════════════════ БАЗОВЫЙ СЛОЙ (раздел 1.7)
add(51, "schulte_table", "Таблицы Шульте", "Найди все числа по порядку на время",
    "Квадратная таблица со случайно расставленными числами. Нужно находить их по порядку. Модификация Горбова–Шульте — чёрно-красная таблица на переключение.",
    "attention", "timed_field", "Schulte table / visual search", "B", "C",
    "Широко используется в русскоязычной практике, но строгих современных РКИ по переносу мало. Как задача на визуальный поиск полностью валидна. Методика «фиксации взгляда в центре» без камеры неизмерима — не обещать.",
    ["paradigmFamily:visual-search", "paradigmFamily:task-switching",
     "delivery:offline-native", "risk:evidence-weak"],
    [I("gridSize", "int", 3, 6, "Размер таблицы"),
     N("numberSet", ["sequential_1_n", "shuffled_ranges", "gorbov_schulte_black_red"], "Тип содержимого; чёрно-красная — на переключение"),
     I("fontJitterPct", "int", 0, 60, "Разброс размера и наклона символов, %"),
     I("contrast", "float", 1.0, 0.55, "Контрастность символов — ниже значит труднее")],
    3, 2, ["completionSec", "regressions", "level"], ["touch"], False, 120, mvp=True,
    issues=["Чёрно-красный вариант Горбова–Шульте фактически задача на переключение установок и ближе к task_switching, чем к классическому Шульте. Стоит либо выделить отдельным упражнением, либо документировать, что внутри одного упражнения измеряются разные домены."])

add(52, "stroop_test", "Тест Струпа", "Назови цвет, а не слово",
    "Слово-название цвета написано чернилами другого цвета. Нужно выбрать ЦВЕТ, подавляя автоматическое чтение.",
    "attention", "single_choice", "Stroop interference (Stroop, 1935)", "A", "B",
    "Одна из самых реплицируемых парадигм в когнитивной психологии. Эффект Струпа — устойчивый маркер когнитивного контроля. Как тренировка — эффект на исполнительный контроль умеренный.",
    ["paradigmFamily:interference", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-solid"],
    [I("incongruentRate", "float", 0.25, 0.6, "Доля конфликтных проб, где цвет не совпадает со словом"),
     I("responseWindowMs", "int", 2500, 900, "Окно на ответ"),
     I("colorCount", "int", 3, 6, "Число цветов в наборе"),
     N("interference", ["color_word", "color_word_position", "color_word_position_emotion"], "Число конкурирующих признаков")],
    24, 2, ["accuracy", "reactionTimeMs", "stroopEffectMs", "level"], ["touch"], False, 150, mvp=True,
    issues=["Обязательна дальтоник-безопасная палитра: при дейтеранопии красный и зелёный неразличимы, и упражнение становится непроходимым. Проверка контраста по WCAG и альтернативная палитра — требование, а не опция.",
            "stroopEffectMs (разница RT между конфликтными и нейтральными пробами) — ключевая метрика, и она требует минимум 20 проб каждого типа, иначе оценка шумная."])

add(53, "task_switching", "Переключение правил", "Один стимул — два разных правила",
    "Показывается стимул — цифра и буква. По сигналу нужно отвечать то по одному правилу (чётная или нечётная), то по другому (гласная или согласная). Правила переключаются непредсказуемо.",
    "cognitive_flexibility", "single_choice", "task-switching / set-shifting", "A", "B",
    "Switch cost — устойчивый и хорошо измеряемый феномен (Jersild 1927; Monsell 2003). Тренируемость переключения показана, широкий перенос на исполнительные функции под вопросом.",
    ["paradigmFamily:task-switching", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-mixed"],
    [I("switchRate", "float", 0.2, 0.5, "Доля проб со сменой правила"),
     I("ruleCount", "int", 2, 3, "Число правил"),
     I("cueDurationMs", "int", 1500, 400, "Время показа подсказки о правиле"),
     N("cueExplicitness", ["explicit_text", "color_only", "position_only", "no_cue"], "Насколько явно указано правило")],
    30, 2, ["accuracy", "reactionTimeMs", "switchCostMs", "level"], ["touch"], False, 150,
    mvp=True, issues=["switchCostMs — ключевая метрика домена. Требует минимум 20 проб каждого типа на блок, иначе оценка шумная. Проверить, влезает ли это в 150 секунд на высокой сложности."])

# ══════════════════════════════════════════════════════════ ИЗ КАТАЛОГА v1.0.0
add(54, "sudoku", "Судоку", "От 4×4 для разминки до 9×9 для профи",
    "Классическая логическая головоломка. Адаптивная сложность меняет размер сетки и число открытых клеток.",
    "logic", "stateful_board", "constraint satisfaction puzzle", "B", "C",
    "Судоку коррелирует с исполнительными функциями, но причинного переноса от тренировок не показано. Ценность — в вовлечении и долгой игровой сессии.",
    ["paradigmFamily:constraint-satisfaction", "delivery:offline-native", "risk:evidence-weak"],
    [N("gridSize", [4, 6, 9], "Размер сетки"),
     I("givens", "int", 60, 22, "Число заполненных клеток на старте для 9×9"),
     N("techniquesRequired", ["naked_single", "hidden_single", "pointing_pairs", "advanced"], "Какие техники нужны для решения"),
     N("notesAllowed", ["auto", "manual", "off"], "Режим пометок-кандидатов")],
    1, 1, ["solved", "completionSec", "errors", "hintsUsed", "level"], ["touch"], False, 420,
    issues=["Генератор обязан гарантировать ЕДИНСТВЕННОСТЬ решения. Наивный генератор с выкалыванием клеток регулярно даёт головоломки с несколькими решениями — это брак, который пользователь находит сам. Нужна проверка решателем (DLX или подход Норвига).",
            "givens зависит от gridSize: для 4×4 диапазон 8→4, для 9×9 — 40→22. Одномерная интерполяция здесь некорректна, нужна нормализация по доле заполненных клеток."])

add(55, "anagrams", "Анаграммы", "Собери слово из перемешанных букв",
    "Перемешанные буквы русского слова. Нужно собрать исходное слово на время.",
    "language", "text_input", "anagram solving / lexical access", "A", "B",
    "Задачи на лексический доступ хорошо изучены. Практическая польза для беглости речи правдоподобна, строгих РКИ именно по тренировке мало.",
    ["memoryKind:verbal", "paradigmFamily:lexical-access", "delivery:needs-external-data",
     "risk:evidence-mixed"],
    [I("wordLength", "int", 4, 8, "Длина слова"),
     N("corpusFrequency", ["top_1k", "top_10k", "top_50k", "rare"], "Частотность слова в корпусе"),
     I("responseWindowMs", "int", 60000, 20000, "Время на слово"),
     N("hintLevel", ["definition_and_first_letter", "first_letter", "none"], "Доступность подсказки")],
    10, 2, ["accuracy", "reactionTimeMs", "solvedCount", "level"], ["keyboard", "touch"], False, 180,
    src="external",
    mvp=True, issues=["Нужен лицензионно чистый частотный словарь русского языка. OpenCorpora распространяется под CC BY-SA, что накладывает обязательства на производные данные. Проверить с юристом до релиза.",
            "Перестановка букв должна быть честной: если из тех же букв собирается другое существующее слово, задача неоднозначна. Нужна проверка по словарю при генерации."])

add(56, "words_from_word", "Слова из слова", "Составь максимум слов из длинного",
    "Дано длинное слово. Нужно составить из его букв как можно больше коротких слов за отведённое время.",
    "language", "text_input", "verbal fluency / word generation", "A", "B",
    "Задачи на беглость — стандартный нейропсихологический инструмент. Тренировка даёт устойчивый внутризадачный прирост.",
    ["memoryKind:verbal", "paradigmFamily:lexical-access", "paradigmFamily:divergent",
     "delivery:needs-external-data", "risk:evidence-mixed"],
    [I("sourceWordLength", "int", 6, 11, "Длина исходного слова"),
     I("minWordLength", "int", 3, 4, "Минимальная длина принимаемого слова"),
     I("timeLimitSec", "int", 180, 60, "Время на раунд"),
     N("corpusFrequency", ["top_1k", "top_10k", "top_50k"], "Частотность исходного слова")],
    3, 1, ["solvedCount", "throughput", "level"], ["keyboard", "touch"], False, 200,
    src="external",
    issues=["Нужен словарь с пометкой «существительное, именительный падеж, единственное число» — иначе пользователи будут спорить о принятых словах, а споры ломают доверие к продукту.",
            "Общий сервис лексики с №55 — не дублировать словарь в двух местах."])

add(57, "alternative_uses", "10 способов использования", "Придумай, зачем ещё нужен обычный предмет",
    "Даётся обычный предмет. Нужно придумать как можно больше нестандартных способов его использования.",
    "creativity", "text_input", "Alternative Uses Task (Guilford, 1967)", "A", "B",
    "AUT — стандартный инструмент измерения дивергентного мышления. Валиден как измеритель; тренируемость креативности через AUT показана умеренно.",
    ["paradigmFamily:divergent", "delivery:needs-authors", "risk:evidence-mixed"],
    [N("objectFamiliarity", ["household_common", "tool", "abstract_object"], "Насколько привычен предмет"),
     I("requiredCount", "int", 5, 12, "Сколько вариантов нужно дать"),
     I("responseWindowMs", "int", 180000, 90000, "Время на раунд")],
    2, 1, ["fluency", "flexibility", "level"], ["keyboard", "touch"], False, 240,
    src="authored", mvp=True,
    issues=["РЕШЕНО (open-questions №2): в MVP считаем только fluency (число уникальных ответов) и flexibility (число семантических категорий по размеченному банку ответов), БЕЗ ML. originality не оцениваем и не показываем — нельзя показывать оценку, которую не умеем считать честно.",
            "Для flexibility нужен размеченный банк категорий на каждый предмет — это авторская работа."])

add(58, "story_recall", "Истории", "Прочитай рассказ и ответь на вопросы",
    "Короткий текст на 60–90 секунд, затем текст закрывается и следуют 5–8 вопросов на детали, порядок событий и причинно-следственные связи.",
    "memory", "passage_qa", "story recall / logical memory (WMS)", "A", "B",
    "Субтест логической памяти из Wechsler Memory Scale — действительно валидный инструмент для эпизодической памяти. Единственное упражнение каталога, реально закрывающее эпизодическую память.",
    ["memoryKind:episodic", "memoryKind:long-term", "delivery:needs-authors",
     "risk:evidence-solid"],
    [I("textWordCount", "int", 60, 180, "Объём текста"),
     I("exposureSec", "int", 90, 40, "Время на чтение"),
     I("delaySec", "int", 0, 120, "Задержка перед вопросами — отсроченное воспроизведение"),
     I("questionCount", "int", 5, 8, "Число вопросов")],
    1, 2, ["accuracy", "immediateRecall", "delayedRecall", "level"], ["touch"], False, 300,
    mvp=True, src="authored",
    issues=["Нужен корпус из 30–40 текстов с вопросами, чтобы они не повторялись. Это работа контент-команды. Решение №4 перенесло упражнение в MVP — значит, корпус блокирует MVP.",
            "delaySec=0 валиден: это немедленное воспроизведение, стандартный первый шаг процедуры WMS.",
            "Вопросы должны быть трёх типов (детали, порядок, причинно-следственные) с раздельными метриками, иначе immediateRecall и delayedRecall не интерпретируемы."])

add(59, "rsvp_reading", "RSVP-чтение", "Слова мелькают в одной точке",
    "Текст подаётся по одному слову в фиксированной точке с заданной скоростью (слов в минуту), затем вопросы на понимание.",
    "language", "passage_qa", "rapid serial visual presentation", "A", "C",
    "RSVP — стандартный лабораторный метод. ВАЖНО: «скорочтение» в популярном смысле (600+ слов/мин с сохранением понимания) наукой НЕ подтверждено — понимание деградирует после ~300 wpm. Обещать «скорочтение 1000 слов/мин» нельзя: это прямое противоречие разделу 9 брифа о научной честности.",
    ["memoryKind:verbal", "paradigmFamily:staircase-timing", "delivery:needs-authors",
     "risk:claim-disputed"],
    [I("wpm", "int", 200, 450, "Скорость подачи, слов в минуту"),
     I("textLengthWords", "int", 80, 250, "Объём отрывка"),
     N("questionDepth", ["literal", "inferential", "inferential_and_critique"], "Уровень вопросов на понимание")],
    2, 1, ["wpm", "comprehension", "effectiveReadingRate", "level"], ["touch"], False, 240,
    src="authored",
    issues=["МАРКЕТИНГОВОЕ ОГРАНИЧЕНИЕ: позиционировать как «тренировку эффективного чтения», а не «скорочтение». Верхняя граница wpm сознательно 450, не 1000.",
            "effectiveReadingRate = wpm × comprehension — честная метрика: она падает при росте скорости сверх порога понимания, и пользователь это видит.",
            "Тот же корпус текстов, что и в №58 — переиспользовать."])


add(60, "reaction_field", "Поле реакции", "Успей нажать на цель раньше, чем она исчезнет",
    "В поле случайно появляются цели и дистракторы. Нужно реагировать только на цели, максимально быстро и точно.",
    "processing_speed", "timed_field", "useful field of view / speed of processing (UFOV)", "A", "A",
    "САМАЯ СИЛЬНАЯ доказательная база среди всех 60 позиций каталога. ACTIVE trial (Ball et al., 2002) показал перенос на повседневные задачи, а тренировка скорости обработки — единственный вид когнитивного тренинга с данными о снижении риска деменции (Edwards et al., 2017, 10-летнее наблюдение). Если продукт может честно заявить одну тренировку с переносом — это она.",
    ["paradigmFamily:visual-search", "paradigmFamily:staircase-timing",
     "delivery:offline-native", "risk:evidence-solid"],
    [I("stimulusMs", "int", 1200, 350, "Время жизни цели"),
     I("fieldCells", "int", 16, 36, "Размер поля от 4×4 до 6×6"),
     I("simultaneousTargets", "int", 1, 4, "Сколько целей активно одновременно"),
     I("distractorRate", "float", 0.0, 0.4, "Доля дистракторов, на которые реагировать нельзя")],
    30, 2, ["accuracy", "reactionTimeMs", "misses", "falseAlarms", "level"], ["touch"], False, 150,
    mvp=True,
    extra=dict(keyMetric="d-prime требует раздельного учёта misses и falseAlarms: при растущем distractorRate падает именно избирательность, а не скорость."),
    issues=["Единственное упражнение каталога с transferEvidence=A. Стоит вынести в онбординг и в маркетинг как флагманскую позицию — но без обещаний про деменцию: Edwards 2017 даёт снижение риска, а не профилактику, и формулировки здесь юридически чувствительны."])

# ─── сборка и перекрёстная проверка ─────────────────────────────────────────
def main():
    arch = json.load(open("content/archetypes.json", encoding="utf-8"))
    doms = json.load(open("content/domains.json", encoding="utf-8"))
    arch_ids = {a["id"] for a in arch["archetypes"]} | {f["id"] for f in arch.get("future", [])}
    retired_ids = {r["id"] for r in arch.get("retired", [])}
    dom_ids = {d["id"] for d in doms["domains"]}
    tag_ids = set()
    for g in doms["tagGroups"].values():
        tag_ids |= set(g["tags"].keys())

    problems, seen = [], set()
    for e in E:
        if e["id"] in seen: problems.append(f"дубль id: {e['id']}")
        seen.add(e["id"])
        if e["dom"] not in dom_ids: problems.append(f"{e['id']}: неизвестный домен {e['dom']}")
        # retired-архетип допустим ТОЛЬКО для упражнения со status=removed_pending_decision:
        # иначе в клиенте появится мёртвый рендерер, а контент будет на него ссылаться.
        if e["arch"] not in arch_ids:
            if e["arch"] in retired_ids and e["removed"]:
                pass  # исключённое упражнение на выведенном архетипе — согласованно
            elif e["arch"] in retired_ids:
                problems.append(f"{e['id']}: активное упражнение ссылается на retired-архетип {e['arch']}")
            else:
                problems.append(f"{e['id']}: неизвестный архетип {e['arch']}")
        for t in e["tags"]:
            if ":" not in t or t.split(":", 1)[1] not in tag_ids:
                problems.append(f"{e['id']}: неизвестный тег {t}")
        if e["pv"] not in EVIDENCE: problems.append(f"{e['id']}: paradigmValidity={e['pv']}")
        if e["te"] not in EVIDENCE: problems.append(f"{e['id']}: transferEvidence={e['te']}")
        if e["pv"] == "D" or e["te"] == "D":
            if "risk:claim-disputed" not in e["tags"]:
                problems.append(f"{e['id']}: оценка D без тега risk:claim-disputed")
        if not e["metrics"]: problems.append(f"{e['id']}: нет метрик")
        pk = {p["key"] for p in e["params"]}
        if len(pk) != len(e["params"]): problems.append(f"{e['id']}: дубли ключей параметров")
        for p in e["params"]:
            if p["type"] != "enum" and p["at0"] == p["at1"]:
                problems.append(f"{e['id']}.{p['key']}: at0 == at1, параметр мёртв")

    if problems:
        print("ОШИБКИ В ТАБЛИЦЕ ГЕНЕРАТОРА:")
        for p in problems: print("  ✗", p)
        return 1

    covers = collections.Counter(e["arch"] for e in E if not e["removed"])
    for a in arch["archetypes"]:
        a["coversCount"] = covers.get(a["id"], 0)

    out = []
    for e in E:
        d = {
            "no": e["no"], "id": e["id"], "domain": e["dom"], "archetype": e["arch"],
            "mvp": e["mvp"],
            "status": "removed_pending_decision" if e["removed"] else "planned",
            "name": {"ru": e["name"]}, "tagline": {"ru": e["tagline"]},
            "description": {"ru": e["desc"]}, "tags": e["tags"],
            "science": {"paradigm": e["par"], "paradigmValidity": e["pv"],
                        "transferEvidence": e["te"], "notes": e["notes"]},
            "difficulty": {"params": e["params"]},
            "trial": {"perBlock": e["perBlock"], "blocksPerSession": e["blocks"]},
            "metrics": e["metrics"], "input": e["inp"], "requiresAudio": e["audio"],
            "durationSec": e["dur"], "contentSource": e["src"], "openIssues": e["issues"],
        }
        d.update(e["extra"])
        out.append(d)

    doc = {
        "$schema": "../schema/exercises.schema.json",
        "version": "2.0.0",
        "generatedBy": "tools/gen-catalog.py — НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ",
        "meta": {
            "sources": {
                "brief50": "Каталог из 50 тренировок продуктового брифа — номера 1–50.",
                "baseLayer": "Базовый слой раздела 1.7 брифа, отсутствовавший в списке 50 — номера 51–53.",
                "catalogV1": "Упражнения каталога v1.0.0, не попавшие в 50 — номера 54–59.",
            },
            "merges": {
                "speed_arithmetic": "поглотило v1 rapid_count",
                "visual_patterns": "поглотило v1 pattern_finding",
                "matchstick_puzzles": "поглотило v1 matchstick_puzzles",
            },
            "duplicatesFlagged": [
                "coin_recall (№17) ≈ matrix_recall (№11) примерно на 80%",
                "memory_tunnel (№20) ≈ cumulative_recall (№15)",
                "pouring_weighing (№36) ≈ water_pouring (№29)",
                "symmetry_completion (№47) ≈ mirror_completion (№8)",
            ],
            "difficultyIndex": {
                "min": 0.0, "max": 1.0,
                "description": "Единый скаляр сложности d ∈ [0,1]. Каждый параметр интерполируется между at0 (легче всего) и at1 (сложнее всего). Один контроллер управляет любым упражнением.",
                "interpolation": {
                    "int": "round(at0 + (at1 - at0) * d)",
                    "float": "at0 + (at1 - at0) * d, округление до 3 знаков",
                    "enum": "values[round(d * (len(values) - 1))]",
                },
                "notApplicableTo": ["card_review", "motor_sequence"],
            },
            "evidenceScale": {
                "paradigmValidity": "Признана ли сама парадигма в науке. A — стандарт, B — признана с оговорками, C — классика без строгих современных репликаций, D — заявленный механизм опровергнут или не изучался.",
                "transferEvidence": "Доказан ли перенос тренировки на повседневные задачи. A — мета-аналитическая поддержка, B — смешанные или ограниченные данные, C — переноса практически нет, D — заявленный перенос опровергнут.",
                "note": "Разделение намеренное: продукт обещает научную честность, а эти две вещи регулярно смешивают. Парадигма может быть безупречна при недоказанном переносе.",
                "auditDoc": "docs/spec/science-audit.md",
            },
        },
        "exercises": out,
    }

    with open("content/exercises.json", "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2); f.write("\n")
    with open("content/archetypes.json", "w", encoding="utf-8") as f:
        json.dump(arch, f, ensure_ascii=False, indent=2); f.write("\n")

    active = [e for e in out if e["status"] != "removed_pending_decision"]
    mvp = [e for e in active if e["mvp"]]
    print(f"✅ content/exercises.json: {len(out)} упражнений ({len(active)} активных, "
          f"{len(out)-len(active)} помечено к исключению)")
    print(f"   MVP: {len(mvp)} → {', '.join(e['id'] for e in mvp)}")
    print("   по доменам:   " + " ".join(
        f"{d}={sum(1 for e in active if e['domain']==d)}" for d in sorted(dom_ids)))
    print("   по архетипам: " + " ".join(f"{k}={v}" for k, v in sorted(covers.items(), key=lambda x: -x[1])))
    print("   по контенту:  " + " ".join(
        f"{k}={sum(1 for e in active if e['contentSource']==k)}" for k in ("generated", "authored", "external")))
    print("   paradigmValidity: " + " ".join(f"{g}={sum(1 for e in active if e['science']['paradigmValidity']==g)}" for g in EVIDENCE))
    print("   transferEvidence: " + " ".join(f"{g}={sum(1 for e in active if e['science']['transferEvidence']==g)}" for g in EVIDENCE))
    print(f"   кривых сложности: {sum(len(e['difficulty']['params']) for e in out)}")
    print(f"   открытых вопросов: {sum(len(e['openIssues']) for e in out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
