#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тесты Святого Брейнфака.

Собирают hbf.cpp и сверяют обе реализации (C++ и Python) на одном наборе
программ: файлные примеры, все 16 команд, ошибки освящения, переполнение
и стоп Ω. Коды выхода и вывод обязаны совпасть.

Запуск:  python3 test.py
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
HBF = os.path.join(ROOT, "hbf")
HBF_CPP = os.path.join(ROOT, "hbf.cpp")
HBF_PY = os.path.join(ROOT, "hbf.py")
H = "♥"


def build() -> None:
    cmd = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-o", HBF, HBF_CPP]
    print("сборка:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def run_cpp(args: list[str], inp: bytes = b"") -> tuple[int, bytes, bytes]:
    p = subprocess.run([HBF, *args], input=inp, capture_output=True, cwd=ROOT)
    return p.returncode, p.stdout, p.stderr


def run_py(args: list[str], inp: bytes = b"") -> tuple[int, bytes, bytes]:
    p = subprocess.run(
        [sys.executable, HBF_PY, *args], input=inp, capture_output=True, cwd=ROOT
    )
    return p.returncode, p.stdout, p.stderr


# (имя, аргументы, ввод, ожидаемый вывод [None — не проверять], код выхода)
CASES: list[tuple[str, list[str], bytes, bytes | None, int]] = [
    ("Hello World (файл)", ["examples/hello.hbf"], b"", b"Hello World!\n", 0),
    ("следующая буква (файл)", ["examples/next_char.hbf"], b"A", b"B", 0),
    ("3 × 7 = 21 (файл)", ["examples/multiply.hbf"], b"", b"21", 0),
    ("очистление: 9×♥ ✝ ☥ → 0", ["-e", H * 9 + "✝☥"], b"", b"0", 0),
    ("приобщение вправо: ☛ → 5", ["-e", H * 5 + "☛♠☥"], b"", b"5", 0),
    ("приобщение влево: ☚ → 4", ["-e", "♠" + H * 4 + "☚♣☥"], b"", b"4", 0),
    ("умножение: 3 × 7 → 21", ["-e", H * 3 + "♠" + H * 7 + "♣✖☥"], b"", b"21", 0),
    ("удвоение: 21 × 2 → 42", ["-e", H * 21 + "☧☥"], b"", b"42", 0),
    ("обмен с соседом → 2", ["-e", "♥♠♥♥♣☨☥"], b"", b"2", 0),
    ("число 0", ["-e", "☥"], b"", b"0", 0),
    ("переполнение → 255", ["-e", "♦☥"], b"", b"255", 0),
    ("остановка Ω (вывода нет)", ["-e", "♥Ω☥"], b"", b"", 0),
    ("мирская суета (вывода нет)", ["-e", "просто молитва"], b"", b"", 0),
    ("ввод: A → B", ["-e", "✞♥☦"], b"A", b"B", 0),
    ("незакрытая молитва (ошибка)", ["-e", "✟♥"], b"", None, 1),
    ("лишний аминь (ошибка)", ["-e", "✠"], b"", None, 1),
]


def main() -> int:
    build()
    failed = 0
    for name, args, inp, want, want_rc in CASES:
        rc1, out1, err1 = run_cpp(args, inp)
        rc2, out2, err2 = run_py(args, inp)
        problems: list[str] = []
        if rc1 != want_rc or rc2 != want_rc:
            problems.append(f"код выхода cpp={rc1} py={rc2}, ждали {want_rc}")
        if want is not None and (out1 != want or out2 != want):
            problems.append(f"вывод cpp={out1!r} py={out2!r}, ждали {want!r}")
        if want_rc != 0:
            if "Ошибка освящения".encode() not in err1:
                problems.append("cpp: нет сообщения «Ошибка освящения»")
            if "Ошибка освящения".encode() not in err2:
                problems.append("py: нет сообщения «Ошибка освящения»")
        if problems:
            failed += 1
            print(f"  ПРОВАЛ  {name}: {'; '.join(problems)}")
        else:
            print(f"  ок      {name}")

    print()
    if failed:
        print(f"Провалов: {failed}")
        return 1
    print(f"Все {len(CASES)} тестов прошли: C++ и Python согласны.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
